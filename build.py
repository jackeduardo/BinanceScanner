"""
打包脚本，用于将应用程序打包成可执行文件
"""

import os
import PyInstaller.__main__

def main():
    """
    主函数，用于打包应用程序
    """
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义PyInstaller参数
    params = [
        'main.py',                       # 主程序文件
        '--name=BinanceScanner',         # 输出的可执行文件名
        '--noconsole',                   # 不显示控制台窗口
        '--onefile',                     # 生成单个可执行文件
        '--clean',                       # 清理临时文件
        '--add-data=config.env;.',       # 包含配置文件
        '--hidden-import=ccxt',          # 隐式导入ccxt库
        '--hidden-import=pandas',        # 隐式导入pandas库
        '--hidden-import=numpy',         # 隐式导入numpy库
        '--hidden-import=python-dotenv', # 隐式导入dotenv库
    ]
    
    # 执行打包命令
    PyInstaller.__main__.run(params)

if __name__ == '__main__':
    main() 