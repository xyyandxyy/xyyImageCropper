import cv2
from pathlib import Path

def process_images(src_folder, dest_folder):
    # 将文件夹路径转换为 Path 对象
    src_folder = Path(src_folder)
    dest_folder = Path(dest_folder)
    
    # 如果目标文件夹不存在，则创建它
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    # 定义支持的图片后缀
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    # 遍历源文件夹下所有符合条件的文件
    images = [p for p in src_folder.iterdir() if p.suffix.lower() in image_extensions]
    
    if not images:
        print("文件夹中没有找到图片文件!")
        return
    
    for image_path in images:
        # 读取图片
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"无法加载图片 {image_path} ，跳过...")
            continue
        print(f"正在处理图片: {image_path.name}")
        
        # 复制一份原图数据
        clone = img.copy()
        
        # 使用 cv2.selectROI 展示交互式窗口，让用户用鼠标拖拽选择想要保留的区域
        r = cv2.selectROI("标注窗口 - 请拖拽选取保留区域, 回车确认, ESC取消", img, showCrosshair=True, fromCenter=False)
        # 关闭所有窗口，确保后续窗口能正常弹出
        cv2.destroyAllWindows()
        
        # r 返回值为 (x, y, w, h)
        x, y, w, h = r
        if w > 0 and h > 0:
            pass
        else:
            print("未选择ROI区域，图片保持不变。")
        # 截取用户选择的 ROI 区域
        cropped = clone[y:y+h, x:x+w]
        # 构造目标文件的路径，文件名保持原来名称
        dest_path = dest_folder / image_path.name
        # 保存截取后的图片到目标文件夹
        cv2.imwrite(str(dest_path), cropped)
        print(f"图片已保存到：{dest_path}")

        
        # 暂停一下，确保系统状态更新
        cv2.waitKey(100)

if __name__ == '__main__':
    # 源图片所在的文件夹路径
    src_folder = "/Users/xyy/git_syn/xyy_image_fucker/test_pics"
    # 处理后的图片保存的文件夹路径，可根据需要修改
    dest_folder = "/Users/xyy/git_syn/xyy_image_fucker/processed_pics"
    process_images(src_folder, dest_folder)