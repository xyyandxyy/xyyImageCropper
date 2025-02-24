import sys
import os
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QFileDialog
)
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen
from PyQt5.QtCore import Qt, QRect, QPoint

# 选择使用的路径格式：
# 设置 FORMAT_MODE 为 "windows" 则采用 Windows 格式，
# 设置为 "unix" 则采用 mac/linux/UNIX 系统的格式。
FORMAT_MODE = "windows"  # 或者 "unix"

# 自定义的 QLabel，用于显示图片并支持 ROI 选取
class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.startPoint = None   # 鼠标按下起始点
        self.endPoint = None     # 鼠标释放点
        self.drawing = False     # 是否正在拖拽
        self.roi_rect = None     # 存储最后选取的 ROI 区域
        self.pix = None          # 当前显示的 QPixmap
        self.scale_factor = 1.0  # 原图与显示图的缩放比例

    # 更新显示图片，同时重置 ROI 相关数据
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

    # 返回 ROI 在原图上的坐标，若未选择则返回 None
    def getOriginalROI(self):
        if self.roi_rect is None:
            return None
        # 将显示图中的 ROI 坐标转为原图坐标
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
        self.setWindowTitle("图片标注软件 - ROI 选择")
        self.src_folder = Path(src_folder)
        self.dest_folder = Path(dest_folder)
        self.dest_folder.mkdir(parents=True, exist_ok=True)
        # 加载所有支持的图片文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_paths = sorted([p for p in self.src_folder.iterdir() if p.suffix.lower() in image_extensions])
        if not self.image_paths:
            self.statusBar().showMessage("指定的文件夹中没有找到图片文件!", 2000)
            sys.exit(1)
        self.current_index = 0
        self.max_width = max_width  # 限制图片显示的最大宽度
        self.original_cv_image = None  # 当前图片的原始 numpy 数据
        self.initUI()
        self.loadCurrentImage()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # 左侧：图片显示区域
        self.imageLabel = ImageLabel()
        # 设定左上对齐，防止图片出现偏移
        self.imageLabel.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # 右侧：操作说明和按钮区域
        instructions = (
            "按键说明：\n"
            "1. 鼠标左键拖动选择需要保留的区域（ROI）。\n"
            "2. 按 空格 或 回车 键：\n"
            "     保存当前 ROI 并切换到下一张图片（当前图片必须完成 ROI 选择，否则无法切换）。\n"
            "3. 按 ESC 键：重置当前 ROI 选择。\n"
            "4. 点击 “上一个” 按钮：返回上一张图片，可重新选择 ROI（保存后将覆盖原先版本）。\n"
            "5. 当所有图片处理完毕后，按 空格 或 回车 键将关闭程序。"
        )
        self.instructionText = QTextEdit()
        self.instructionText.setReadOnly(True)
        self.instructionText.setText(instructions)
        self.statusLabel = QLabel("状态：")
        self.saveBtn = QPushButton("保存 ROI")
        self.resetBtn = QPushButton("重置 ROI")
        self.prevBtn = QPushButton("上一个")
        # “下一个”按钮仅做显示，但其功能与确认保存 ROI 保持一致
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
        # 根据 FORMAT_MODE 选择合适的路径字符串
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
        # 根据 FORMAT_MODE 选择合适的路径格式
        if FORMAT_MODE == "windows":
            dest_file = str(dest_path)
        else:
            dest_file = dest_path.as_posix()
        cv2.imwrite(dest_file, cropped)
        self.statusBar().showMessage(f"图片已保存到：{dest_file}", 2000)
        # 如果当前已经是最后一张图片，则全部处理完毕，退出程序
        if self.current_index == len(self.image_paths) - 1:
            self.statusBar().showMessage("所有图片处理完毕，程序将关闭，感谢你使用。", 2000)
            QApplication.instance().processEvents()  # 刷新事件，显示状态消息
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
            self.statusBar().showMessage("已经是第一张图片！", 2000)

    def nextImage(self):
        # 如果当前图片尚未选择 ROI，则提示用户
        if self.imageLabel.getOriginalROI() is None:
            self.statusBar().showMessage("请先选择 ROI 区域再切换到下一张图片！", 2000)
            return
        # 模拟保存操作，覆盖当前图片
        self.saveCurrentROI()

    # 重载键盘事件，支持快捷键操作
    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Space, Qt.Key_Return):
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
    # 提示选择图片所在的文件夹
    src_folder = QFileDialog.getExistingDirectory(None, "选择图片文件夹", os.getcwd())
    if not src_folder:
        sys.exit("未选择图片文件夹，程序退出。")
    # 提示选择保存处理后图片的目标文件夹
    dest_folder = QFileDialog.getExistingDirectory(None, "选择目标文件夹", os.getcwd())
    if not dest_folder:
        sys.exit("未选择目标文件夹，程序退出。")
    window = MainWindow(src_folder, dest_folder)
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())