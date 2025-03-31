"""
主程序入口文件，启动币安扫描器应用。
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

# 添加src目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 显示当前的Python路径
print("Python路径:")
for p in sys.path:
    print(f"- {p}")

# 尝试导入必要的模块
print("\n尝试导入模块...")
try:
    # 首先检查src目录是否存在
    src_dir = os.path.join(current_dir, 'src')
    ui_dir = os.path.join(src_dir, 'ui')
    main_window_file = os.path.join(ui_dir, 'main_window.py')
    
    if not os.path.exists(src_dir):
        print(f"错误: src目录不存在: {src_dir}")
        sys.exit(1)
        
    if not os.path.exists(ui_dir):
        print(f"错误: ui目录不存在: {ui_dir}")
        sys.exit(1)
        
    if not os.path.exists(main_window_file):
        print(f"错误: main_window.py文件不存在: {main_window_file}")
        sys.exit(1)
    
    print(f"src目录存在: {src_dir}")
    print(f"ui目录存在: {ui_dir}")
    print(f"main_window.py文件存在: {main_window_file}")
    
    # 尝试导入模块
    print("\n尝试导入以下模块:")
    
    print("导入src模块...", end="")
    import src
    print("成功!")
    
    print("导入src.ui模块...", end="")
    import src.ui
    print("成功!")
    
    print("导入src.ui.main_window模块...", end="")
    import src.ui.main_window
    print("成功!")
    
    print("从src.ui.main_window导入BinanceScanner类...", end="")
    from src.ui.main_window import BinanceScanner
    print("成功!")
    
except ImportError as e:
    print(f"导入错误: {str(e)}")
    QApplication(sys.argv)
    QMessageBox.critical(None, "导入错误", f"无法导入必要的模块: {str(e)}\n\n请检查日志以获取更多信息。")
    sys.exit(1)
except Exception as e:
    print(f"错误: {str(e)}")
    QApplication(sys.argv)
    QMessageBox.critical(None, "错误", f"发生错误: {str(e)}\n\n请检查日志以获取更多信息。")
    sys.exit(1)


def main():
    """主程序入口函数"""
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = BinanceScanner()
    
    # 显示主窗口
    window.show()
    
    # 运行应用的事件循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
