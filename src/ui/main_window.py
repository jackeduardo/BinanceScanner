"""
主窗口模块，实现应用的主界面。
"""

import os
import sys
import traceback
from datetime import datetime, timedelta
import pandas as pd

from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QGroupBox, QCheckBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon

from src.scanner.scanner_thread import ScannerThread
from src.scanner.signal_detector import check_long_conditions, check_short_conditions, check_additional_condition
from src.exchange.exchange_handler import connect_exchange, get_exchange_id, get_market_symbols
from src.utils.url_generator import get_exchange_url
from src.utils.config import load_config


class BinanceScanner(QMainWindow):
    """币安扫描器主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 加载配置文件
        self.config = load_config()
        
        # 初始化状态变量
        self.exchange = None
        self.timer = None
        self.symbol_urls = {}  # 存储交易对URL
        self.basic_condition_results = {}  # 存储基本条件扫描结果，用于附加条件判断
        self.last_scan_time = None
        self.is_scanning_long = False  # 是否正在扫描做多信号
        self.is_scanning_short = False  # 是否正在扫描做空信号
        self.is_scanning = False  # 扫描状态统一标志
        self.long_scanner_thread = None  # 做多扫描线程
        self.short_scanner_thread = None  # 做空扫描线程
        
        # BTC提醒相关
        self.btc_last_alert_time = None  # 上次BTC提醒时间，用于避免频繁提醒
        self.btc_alert_cooldown = 300  # 提醒冷却时间（秒），避免短时间内多次提醒
        
        # 设置主窗口属性
        self.setWindowTitle("币安扫描器 - 移动平均线信号扫描")
        self.setGeometry(100, 100, 1024, 768)
        
        # 创建UI组件
        self.setup_ui()
        
        # 初始化定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.scan_markets)  # 默认扫描做多信号
        self.timer.setInterval(self.config.get('scan_interval', 15) * 60000)  # 转换为毫秒
        
        # 已注释掉自动连接代码，需要用户手动点击连接
        # QTimer.singleShot(500, self.auto_connect)
        
    def setup_ui(self):
        """创建并初始化UI组件"""
        try:
            from src.ui.ui_components import create_main_layout
            from src.ui.ui_handler import auto_connect, update_coin_filter_list, setup_event_handlers
            
            # 创建主布局
            create_main_layout(self)
            
            # 设置事件处理器
            setup_event_handlers(self)
            
            # 设置窗口图标
            self.set_window_icon()
            
            # 初始化状态变量
            self.is_scanning = False
            self.is_scanning_long = False
            self.is_scanning_short = False
            
            # 初始化信号URL字典
            self.symbol_urls = {}
            
            # 应用默认配置
            self.apply_default_config()
            
            # 在应用程序启动时记录
            if hasattr(self, 'log_text'):
                self.log_text.append("应用程序已启动，请点击'连接到交易所'按钮进行连接")
            
        except Exception as e:
            QMessageBox.critical(self, "初始化UI错误", f"初始化UI时出错: {str(e)}")
            traceback.print_exc()
        
    def apply_default_config(self):
        """将配置文件中的默认值填充到UI组件"""
        # 记录配置加载信息
        if hasattr(self, 'log_text'):
            self.log_text.append("正在加载默认配置...")
        
        # 填充API密钥信息
        if hasattr(self, 'api_key_input') and self.config.get('api_key'):
            self.api_key_input.setText(self.config.get('api_key', ''))
            if hasattr(self, 'log_text'):
                self.log_text.append("已加载API密钥配置")
            
        if hasattr(self, 'api_secret_input') and self.config.get('api_secret'):
            self.api_secret_input.setText(self.config.get('api_secret', ''))
            
        # 设置交易所
        if hasattr(self, 'exchange_combo') and self.config.get('exchange'):
            exchange_text = self.config.get('exchange', 'binance')
            if exchange_text == "binance":
                exchange_text = "币安(Binance)"
            elif exchange_text == "binanceusdm":
                exchange_text = "币安(Binance)"
                # 确保选择U本位期货
                if hasattr(self, 'market_type_combo'):
                    self.market_type_combo.setCurrentText("期货(U本位)")
            
            index = self.exchange_combo.findText(exchange_text)
            if index >= 0:
                self.exchange_combo.setCurrentIndex(index)
                if hasattr(self, 'log_text'):
                    self.log_text.append(f"已设置默认交易所: {exchange_text}")
        
        # 设置代理
        if hasattr(self, 'use_proxy_checkbox') and self.config.get('use_proxy'):
            self.use_proxy_checkbox.setChecked(self.config.get('use_proxy', False))
            
        if hasattr(self, 'proxy_input') and self.config.get('proxy_url'):
            self.proxy_input.setText(self.config.get('proxy_url', ''))
                
        # 显示代理设置信息
        if hasattr(self, 'log_text'):
            use_proxy = self.config.get('use_proxy', False)
            proxy_url = self.config.get('proxy_url', '')
            if use_proxy and proxy_url:
                self.log_text.append(f"已启用代理: {proxy_url}")
            else:
                self.log_text.append("未启用代理")
                
        if hasattr(self, 'log_text'):
            self.log_text.append("配置加载完成")
        
    def create_settings_widget(self):
        """创建设置区域"""
        from src.ui.ui_components import create_settings_widget
        return create_settings_widget(self)
    
    def create_results_widget(self):
        """创建结果区域"""
        from src.ui.ui_components import create_results_widget
        return create_results_widget(self)
    
    def bind_events(self):
        """绑定事件处理函数"""
        # 绑定按钮点击事件
        self.connect_button.clicked.connect(self.connect_to_exchange)
        self.scan_long_button.clicked.connect(self.scan_long_signals)
        self.scan_short_button.clicked.connect(self.scan_short_signals)
        self.test_case_button.clicked.connect(self.run_test_case)
        
        # 确保自动扫描按钮正确连接
        if hasattr(self, 'start_scan_button'):
            self.start_scan_button.clicked.disconnect() if self.start_scan_button.receivers(self.start_scan_button.clicked) > 0 else None
            self.start_scan_button.clicked.connect(self.start_scanning)
        
        # 绑定表格点击事件
        self.long_signals_table.cellClicked.connect(lambda row, col: self.handle_table_click(row, col, True))
        self.short_signals_table.cellClicked.connect(lambda row, col: self.handle_table_click(row, col, False))
        
        # 绑定窗口关闭事件
        self.closeEvent = self.handle_close_event
    
    def toggle_proxy(self, state):
        """切换代理状态"""
        if hasattr(self, 'proxy_input'):
            self.proxy_input.setEnabled(state == Qt.Checked)
    
    def update_market_type(self, index):
        """更新市场类型"""
        if hasattr(self, 'market_type_combo'):
            market_type = self.market_type_combo.currentText()
            self.log_text.append(f"已选择市场类型: {market_type}")
        
    def auto_connect(self):
        """自动连接到交易所"""
        # 不自动连接，而是显示提示信息
        if hasattr(self, 'log_text'):
            self.log_text.append("请点击'连接到交易所'按钮手动连接")
        return
        
    def connect_to_exchange(self):
        """连接到交易所"""
        from src.ui.ui_handler import connect_to_exchange
        connect_to_exchange(self)
        
    def handle_table_click(self, row, column, is_long):
        """处理表格点击事件"""
        from src.ui.ui_handler import handle_table_click
        handle_table_click(self, row, column, is_long)
        
    def scan_long_signals(self):
        """扫描做多信号"""
        from src.ui.ui_handler import scan_long_signals
        scan_long_signals(self)
        
    def scan_short_signals(self):
        """扫描做空信号"""
        from src.ui.ui_handler import scan_short_signals
        scan_short_signals(self)
        
    def update_progress(self, processed, total, is_long):
        """更新进度条"""
        from src.ui.ui_handler import update_progress
        update_progress(self, processed, total, is_long)
        
    def handle_signal_found(self, symbol, signal_data, is_long):
        """处理发现的信号"""
        from src.ui.ui_handler import handle_signal_found
        handle_signal_found(self, symbol, signal_data, is_long)
        
    def handle_scan_completed(self, is_long):
        """处理扫描完成"""
        from src.ui.ui_handler import handle_scan_completed
        handle_scan_completed(self, is_long)
        
    def handle_scan_error(self, error_msg):
        """处理扫描错误"""
        from src.ui.ui_handler import handle_scan_error
        handle_scan_error(self, error_msg)
        
    def log_message(self, message, is_long):
        """记录日志消息"""
        from src.ui.ui_handler import log_message
        log_message(self, message, is_long)
        
    def run_test_case(self):
        """运行测试用例"""
        from src.ui.ui_handler import run_test_case
        run_test_case(self)
        
    def start_scanning(self):
        """开始或停止自动扫描"""
        from src.ui.ui_handler import start_scanning
        start_scanning(self)
        
    def scan_markets(self):
        """自动扫描所有市场"""
        from src.ui.ui_handler import scan_markets
        scan_markets(self)
        
    def handle_close_event(self, event):
        """处理窗口关闭事件"""
        from src.ui.ui_handler import handle_close_event
        handle_close_event(self, event)
        
    def update_window_title(self):
        """更新窗口标题，显示连接状态"""
        title = "币安扫描器 - 移动平均线信号扫描"
        
        if hasattr(self, 'exchange') and self.exchange:
            # 如果已连接交易所，在标题中显示连接信息
            exchange_id = self.exchange.id if hasattr(self.exchange, 'id') else "未知交易所"
            title += f" [已连接: {exchange_id}]"
        else:
            title += " [未连接]"
        
        self.setWindowTitle(title) 
        
    def set_window_icon(self):
        """设置窗口图标"""
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'icon.png')
            
            # 检查图标文件是否存在
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                # 如果图标文件不存在，不设置图标，但不抛出错误
                if hasattr(self, 'log_text'):
                    self.log_text.append(f"警告: 图标文件不存在 {icon_path}")
                
        except Exception as e:
            # 设置图标失败不应该影响程序运行
            if hasattr(self, 'log_text'):
                self.log_text.append(f"设置窗口图标失败: {str(e)}")
                traceback.print_exc()
        
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        from src.ui.ui_handler import handle_close_event
        handle_close_event(self, event)
        