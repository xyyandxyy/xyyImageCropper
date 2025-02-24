# xyy的图片数据选取标注软件

<img src=".\asset\demo.png" alt="demo" style="zoom:50%;" />

#### 0. Introduction

这是一款基于 PyQt5 和 OpenCV 的图片批量手动切割工具, 主要用于从大量图片中按需裁剪出指定区域 (ROI). 

主要用于计算机视觉和多模态相关工作制作数据时的批量图片裁剪. 

标注者启动程序后, 会依次被提示选择存放原始图片的文件夹以及保存裁剪后图片的目标文件夹. 软件支持常见图片格式 (如 jpg, png, bmp 等), 并会逐张显示图片供用户处理. 

使用时, 用户只需用鼠标左键在图片上按下并拖动, 即可选中需要保留的区域, 选区完成后通过按回车键 (**左手可以一直放在回车键上**)(如果是右撇子) 或点击 "保存 ROI" 按钮将当前图片裁剪并保存到目标文件夹. 若需要重新调整选区, 可按 ESC 键或点击 "重置 ROI" 按钮进行重置. 

软件还提供 "上一个" 按钮, 允许用户返回上一张图片, 修改之前的选取. 所有操作都会在界面状态栏中实时显示当前进度和提示信息. 

目前 Release 只有 Win x64 版本. 因为在 Win 下好标注嘿嘿, 经常只用 Win 来标注. 有需要只需要修改代码中的平台变量, 并到对应的平台进行打包即可.



#### 1. Environment

```
pip install opencv-python numpy PyQt5 pyinstaller
```



#### 2. Running

```
python main.py
```



#### 3. Packaging

in Windows:
```
pyinstaller --onefile --windowed --icon=favicon.ico --add-data "favicon.ico;." main.py
```

