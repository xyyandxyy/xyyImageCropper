import sys
import os
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QIcon
from PyQt5.QtCore import Qt, QRect

FORMAT_MODE = "windows"  # 或者 "unix"

def resource_path(relative_path):
    """获取资源在打包后或开发时的正确路径"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

icon_filepath = resource_path("favicon.ico")

# 自定义的 QLabel，用于显示图片并支持 ROI 选取
class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.startPoint = None
        self.endPoint = None
        self.drawing = False
        self.roi_rect = None
        self.pix = None
        self.scale_factor = 1.0

    def setImage(self, pixmap, scale_factor=1.0):
        self.pix = pixmap
        self.setPixmap(self.pix)
        self.scale_factor = scale_factor
        self.roi_rect = None
        self.startPoint = None
        self.endPoint = None
        self.update()

    def mousePressEvent(self, event):
        if self.pix is None:
            return
        if event.button() == Qt.LeftButton:
            self.startPoint = event.pos()
            self.endPoint = event.pos()
            self.drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.endPoint = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drawing and event.button() == Qt.LeftButton:
            self.endPoint = event.pos()
            self.drawing = False
            self.roi_rect = QRect(self.startPoint, self.endPoint).normalized()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pix is None:
            return
        if self.drawing or self.roi_rect:
            painter = QPainter(self)
            pen = QPen(Qt.red, 2, Qt.SolidLine)
            painter.setPen(pen)
            if self.drawing:
                rect = QRect(self.startPoint, self.endPoint).normalized()
                painter.drawRect(rect)
            elif self.roi_rect:
                painter.drawRect(self.roi_rect)

    def getOriginalROI(self):
        if self.roi_rect is None:
            return None
        x = int(self.roi_rect.x() / self.scale_factor)
        y = int(self.roi_rect.y() / self.scale_factor)
        w = int(self.roi_rect.width() / self.scale_factor)
        h = int(self.roi_rect.height() / self.scale_factor)
        return (x, y, w, h)

    def resetROI(self):
        self.roi_rect = None
        self.startPoint = None
        self.endPoint = None
        self.update()

class MainWindow(QMainWindow):
    def __init__(self, src_folder, dest_folder, max_width=800):
        super().__init__()
        self.setWindowTitle("xyy的图片批量手动切割工具")
        self.setWindowIcon(QIcon(icon_filepath))
        self.src_folder = Path(src_folder)
        self.dest_folder = Path(dest_folder)
        self.dest_folder.mkdir(parents=True, exist_ok=True)
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_paths = sorted([p for p in self.src_folder.iterdir() if p.suffix.lower() in image_extensions])
        if not self.image_paths:
            self.statusBar().showMessage("指定的文件夹中没有找到图片文件!", 2000)
            sys.exit(1)
        self.current_index = 0
        self.max_width = max_width  
        self.original_cv_image = None  
        self.initUI()
        self.loadCurrentImage()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.imageLabel = ImageLabel()
        self.imageLabel.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        instructions = (
            "按键说明：\n"
            "1. 鼠标左键拖动选择需要保留的区域（ROI）。\n"
            "2. 按 回车 键 (你可以一只把手放到这)：\n"
            "     保存当前 ROI 并切换到下一张图片（当前图片必须完成 ROI 选择，否则无法切换）。\n"
            "3. 按 ESC 键：重置当前 ROI 选择。\n"
            "4. 点击 “上一个” 按钮：返回上一张图片，可重新选择 ROI（保存后将覆盖原先版本）。\n"
            "5. 当所有图片处理完毕后，会弹出完成提示，按回车或点击“确定”关闭程序。"
        )
        self.instructionText = QTextEdit()
        self.instructionText.setReadOnly(True)
        self.instructionText.setText(instructions)
        self.statusLabel = QLabel("状态：")
        self.saveBtn = QPushButton("保存 ROI (快捷键:回车)")
        self.resetBtn = QPushButton("重置 ROI")
        self.prevBtn = QPushButton("上一个")
        self.nextBtn = QPushButton("下一个")
        self.saveBtn.clicked.connect(self.saveCurrentROI)
        self.resetBtn.clicked.connect(self.resetROI)
        self.prevBtn.clicked.connect(self.prevImage)
        self.nextBtn.clicked.connect(self.nextImage)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<b>操作说明</b>"))
        right_layout.addWidget(self.instructionText)
        right_layout.addWidget(self.statusLabel)
        right_layout.addWidget(self.saveBtn)
        right_layout.addWidget(self.resetBtn)
        right_layout.addWidget(self.prevBtn)
        right_layout.addWidget(self.nextBtn)
        right_layout.addStretch()
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.imageLabel, 1)
        main_layout.addLayout(right_layout, 0)
        central_widget.setLayout(main_layout)

    def loadCurrentImage(self):
        image_path = self.image_paths[self.current_index]
        if FORMAT_MODE == "windows":
            image_file = str(image_path)
        else:
            image_file = image_path.as_posix()
        self.original_cv_image = cv2.imread(image_file)
        if self.original_cv_image is None:
            self.statusBar().showMessage(f"无法加载图片 {image_path.name}", 2000)
            return
        img_rgb = cv2.cvtColor(self.original_cv_image, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qImg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scale_factor = 1.0
        if w > self.max_width:
            scale_factor = self.max_width / w
            qImg = qImg.scaled(self.max_width, int(h * scale_factor), Qt.KeepAspectRatio)
        pixmap = QPixmap.fromImage(qImg)
        self.imageLabel.setImage(pixmap, scale_factor)
        self.statusLabel.setText(f"当前图片: {image_path.name}  ({self.current_index + 1}/{len(self.image_paths)})")

    def saveCurrentROI(self):
        roi = self.imageLabel.getOriginalROI()
        if roi is None:
            self.statusBar().showMessage("请先选择 ROI 区域，再保存！", 2000)
            return
        x, y, w, h = roi
        if w <= 0 or h <= 0:
            self.statusBar().showMessage("无效的 ROI 区域!", 2000)
            return
        cropped = self.original_cv_image[y:y+h, x:x+w]
        image_path = self.image_paths[self.current_index]
        dest_path = self.dest_folder / image_path.name
        if FORMAT_MODE == "windows":
            dest_file = str(dest_path)
        else:
            dest_file = dest_path.as_posix()
        cv2.imwrite(dest_file, cropped)
        self.statusBar().showMessage(f"图片已保存到：{dest_file}", 2000)
        if self.current_index == len(self.image_paths) - 1:
            ret = QMessageBox.information(self, "处理完毕", "所有图片处理完毕，xyy感谢你。", QMessageBox.Ok)
            if ret == QMessageBox.Ok:
                QApplication.instance().quit()
        else:
            self.current_index += 1
            self.loadCurrentImage()

    def resetROI(self):
        self.imageLabel.resetROI()

    def prevImage(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.loadCurrentImage()
        else:
            self.statusBar().showMessage("已经是第一张图片, 没办法上一张了！", 2000)

    def nextImage(self):
        if self.imageLabel.getOriginalROI() is None:
            self.statusBar().showMessage("请先选择 ROI 区域再切换到下一张图片！", 2000)
            return
        self.saveCurrentROI()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return:
            if self.imageLabel.getOriginalROI() is None:
                self.statusBar().showMessage("请先选择 ROI 区域再确认！", 2000)
            else:
                self.saveCurrentROI()
        elif key == Qt.Key_Escape:
            self.resetROI()
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_filepath))
    
    QMessageBox.information(None, "选择要处理的图片的文件夹",
                            "请选择包含要处理的图片文件夹，我们将处理其中的jpg和png文件。")
    src_folder = QFileDialog.getExistingDirectory(None, "选择图片文件夹", os.getcwd())
    if not src_folder:
        sys.exit("你没有选择存放图片的文件夹，程序退出。")
    
    QMessageBox.information(None, "选择导出图片的文件夹",
                            "请选择导出到哪个文件夹，处理后的图片将保存在该文件夹中。")
    dest_folder = QFileDialog.getExistingDirectory(None, "选择导出文件夹", os.getcwd())
    if not dest_folder:
        sys.exit("你没有选择导出图片的文件夹，程序退出。")
    
    window = MainWindow(src_folder, dest_folder)
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())