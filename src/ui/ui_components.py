"""
UI组件模块，负责创建应用界面的各个组件。
"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QGroupBox, QCheckBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QProgressBar, QListWidget
)
from PyQt5.QtCore import Qt
import os

def create_settings_widget(main_window):
    """创建设置区域组件"""
    settings_widget = QWidget()
    settings_layout = QVBoxLayout(settings_widget)
    
    # 添加扫描进度UI
    scan_progress_group = QGroupBox("扫描进度")
    scan_progress_layout = QVBoxLayout()
    scan_progress_group.setLayout(scan_progress_layout)
    
    # 添加做多信号进度布局
    long_scan_layout = QHBoxLayout()
    long_scan_layout.addWidget(QLabel("做多信号:"))
    main_window.long_progress_bar = QProgressBar()
    main_window.long_progress_bar.setVisible(False)
    main_window.long_progress_bar.setFormat("%v/%m (%p%)")  # 显示格式：当前值/最大值 (百分比)
    long_scan_layout.addWidget(main_window.long_progress_bar)
    
    # 添加进度文本标签
    main_window.long_progress_label = QLabel("0/0 (0%)")
    long_scan_layout.addWidget(main_window.long_progress_label)
    
    # 添加扫描状态标签
    main_window.scanning_long_label = QLabel("正在扫描...")
    main_window.scanning_long_label.setVisible(False)
    main_window.scanning_long_label.setStyleSheet("color: blue;")
    long_scan_layout.addWidget(main_window.scanning_long_label)
    
    scan_progress_layout.addLayout(long_scan_layout)
    
    # 添加做空信号进度布局
    short_scan_layout = QHBoxLayout()
    short_scan_layout.addWidget(QLabel("做空信号:"))
    main_window.short_progress_bar = QProgressBar()
    main_window.short_progress_bar.setVisible(False)
    main_window.short_progress_bar.setFormat("%v/%m (%p%)")  # 显示格式：当前值/最大值 (百分比)
    short_scan_layout.addWidget(main_window.short_progress_bar)
    
    # 添加进度文本标签
    main_window.short_progress_label = QLabel("0/0 (0%)")
    short_scan_layout.addWidget(main_window.short_progress_label)
    
    # 添加扫描状态标签
    main_window.scanning_short_label = QLabel("正在扫描...")
    main_window.scanning_short_label.setVisible(False)
    main_window.scanning_short_label.setStyleSheet("color: blue;")
    short_scan_layout.addWidget(main_window.scanning_short_label)
    
    scan_progress_layout.addLayout(short_scan_layout)
    
    # 添加自动扫描倒计时进度布局
    auto_scan_layout = QHBoxLayout()
    auto_scan_layout.addWidget(QLabel("自动扫描倒计时:"))
    main_window.auto_scan_progress_bar = QProgressBar()
    main_window.auto_scan_progress_bar.setVisible(False)
    main_window.auto_scan_progress_bar.setRange(0, 100)
    main_window.auto_scan_progress_bar.setTextVisible(True)  # 显示文本
    main_window.auto_scan_progress_bar.setFormat("%v% (剩余%vs)")  # 显示百分比和剩余秒数
    auto_scan_layout.addWidget(main_window.auto_scan_progress_bar)
    
    # 自动扫描进度条的另一个引用，保持向后兼容
    main_window.update_countdown_progress_bar = main_window.auto_scan_progress_bar
    
    # 添加倒计时文本标签
    main_window.countdown_label = QLabel("等待扫描...")
    main_window.countdown_label.setVisible(False)
    auto_scan_layout.addWidget(main_window.countdown_label)
    
    # 添加自动扫描间隔布局到进度布局
    scan_progress_layout.addLayout(auto_scan_layout)
    
    # 添加进度组到布局
    settings_layout.addWidget(scan_progress_group)
    
    # 交易所选择部分
    exchange_group = QGroupBox("交易所选择")
    exchange_layout = QGridLayout()
    exchange_group.setLayout(exchange_layout)
    
    # 交易所行
    exchange_layout.addWidget(QLabel("交易所:"), 0, 0)
    main_window.exchange_combo = QComboBox()
    main_window.exchange_combo.addItem("币安(Binance)")
    exchange_layout.addWidget(main_window.exchange_combo, 0, 1)
    
    # 市场类型行
    exchange_layout.addWidget(QLabel("市场类型:"), 0, 2)
    main_window.market_type_combo = QComboBox()
    main_window.market_type_combo.addItem("期货(U本位)")
    exchange_layout.addWidget(main_window.market_type_combo, 0, 3)
    
    # 连接状态标签
    exchange_layout.addWidget(QLabel("连接状态:"), 0, 4)
    main_window.connection_status_label = QLabel("未连接")
    main_window.connection_status_label.setStyleSheet("color: red;")
    exchange_layout.addWidget(main_window.connection_status_label, 0, 5)
    
    settings_layout.addWidget(exchange_group)
    
    # API设置部分
    api_group = QGroupBox("API设置")
    api_layout = QGridLayout()
    api_group.setLayout(api_layout)
    
    # API Key行
    api_layout.addWidget(QLabel("API Key:"), 0, 0)
    main_window.api_key_input = QLineEdit()
    main_window.api_key_input.setEchoMode(QLineEdit.Password)
    api_layout.addWidget(main_window.api_key_input, 0, 1)
    
    # API Secret行
    api_layout.addWidget(QLabel("API Secret:"), 1, 0)
    main_window.api_secret_input = QLineEdit()
    main_window.api_secret_input.setEchoMode(QLineEdit.Password)
    api_layout.addWidget(main_window.api_secret_input, 1, 1)
    
    # API 按钮行
    main_window.apply_api_button = QPushButton("应用API设置")
    api_layout.addWidget(main_window.apply_api_button, 2, 0)
    
    main_window.save_api_button = QPushButton("保存API设置")
    api_layout.addWidget(main_window.save_api_button, 2, 1)
    
    settings_layout.addWidget(api_group)
    
    # 网络设置部分
    network_group = QGroupBox("网络设置")
    network_layout = QGridLayout()
    network_group.setLayout(network_layout)
    
    # 请求超时行
    network_layout.addWidget(QLabel("请求超时:"), 0, 0)
    main_window.timeout_input = QSpinBox()
    main_window.timeout_input.setRange(1000, 60000)
    main_window.timeout_input.setValue(10000)
    main_window.timeout_input.setSuffix(" ms")
    network_layout.addWidget(main_window.timeout_input, 0, 1)
    
    # 使用代理行
    main_window.use_proxy_checkbox = QCheckBox("使用代理")
    network_layout.addWidget(main_window.use_proxy_checkbox, 1, 0)
    main_window.proxy_input = QLineEdit()
    main_window.proxy_input.setPlaceholderText("例如: http://127.0.0.1:7890")
    network_layout.addWidget(main_window.proxy_input, 1, 1)
    
    settings_layout.addWidget(network_group)
    
    # 扫描参数设置部分
    scan_params_group = QGroupBox("扫描参数设置")
    scan_params_layout = QGridLayout()
    scan_params_group.setLayout(scan_params_layout)
    
    # 时间周期行
    scan_params_layout.addWidget(QLabel("时间周期:"), 0, 0)
    main_window.timeframe_combo = QComboBox()
    main_window.timeframe_combo.addItems(['1m', '5m', '15m', '1h', '4h', '1d'])
    main_window.timeframe_combo.setCurrentText('15m')
    main_window.timeframe_combo.setToolTip("选择K线时间周期")
    scan_params_layout.addWidget(main_window.timeframe_combo, 0, 1)
    
    # 添加币种筛选
    scan_params_layout.addWidget(QLabel("币种筛选:"), 0, 2)
    main_window.coin_filter_combo = QComboBox()
    main_window.coin_filter_combo.addItem('全部')  # 初始只添加"全部"选项
    main_window.coin_filter_combo.setCurrentText('全部')
    main_window.coin_filter_combo.setToolTip("选择要扫描的特定币种，选择'全部'将扫描所有币种\n支持多选：输入多个币种用逗号分隔（如'BTC,ETH'）\n列表将在连接交易所后自动更新")
    main_window.coin_filter_combo.setEditable(True)  # 允许用户输入自定义币种
    main_window.coin_filter_combo.setInsertPolicy(QComboBox.NoInsert)  # 不自动插入用户输入的内容到下拉菜单
    scan_params_layout.addWidget(main_window.coin_filter_combo, 0, 3)
    
    # 添加永续合约过滤复选框
    main_window.perpetual_only_checkbox = QCheckBox("只显示永续合约")
    main_window.perpetual_only_checkbox.setChecked(True)  # 默认勾选
    main_window.perpetual_only_checkbox.setToolTip("勾选后只显示永续合约，不显示带有日期的交割合约")
    scan_params_layout.addWidget(main_window.perpetual_only_checkbox, 3, 0)
    
    # 添加永续合约标签（用于切换可见性）
    main_window.perpetual_only_label = QLabel("永续合约过滤已启用")
    main_window.perpetual_only_label.setStyleSheet("color: green;")
    scan_params_layout.addWidget(main_window.perpetual_only_label, 3, 1)
    
    # K线数量行
    scan_params_layout.addWidget(QLabel("检查K线数量:"), 3, 2)
    main_window.candle_count_input = QSpinBox()
    main_window.candle_count_input.setRange(5, 50)
    main_window.candle_count_input.setValue(10)
    main_window.candle_count_input.setToolTip("设置要检查的K线数量")
    scan_params_layout.addWidget(main_window.candle_count_input, 3, 3)
    
    # 添加自动扫描间隔设置
    scan_params_layout.addWidget(QLabel("自动扫描间隔(分钟):"), 3, 4)
    main_window.scan_interval_input = QSpinBox()
    main_window.scan_interval_input.setRange(1, 120)
    main_window.scan_interval_input.setValue(15)
    main_window.scan_interval_input.setToolTip("设置自动扫描的时间间隔，单位为分钟")
    scan_params_layout.addWidget(main_window.scan_interval_input, 3, 5)
    
    # 添加扫描参数组到布局
    settings_layout.addWidget(scan_params_group)
    
    # 操作部分
    operation_group = QGroupBox("操作")
    operation_layout = QGridLayout()
    operation_group.setLayout(operation_layout)
    
    # 操作按钮 - 移除测试连接按钮
    main_window.connect_button = QPushButton("连接到交易所")
    main_window.connect_button.setToolTip("连接到交易所并获取交易对列表")
    operation_layout.addWidget(main_window.connect_button, 0, 0)
    
    # 清理缓存按钮
    main_window.clear_cache_button = QPushButton("清理K线缓存")
    main_window.clear_cache_button.setToolTip("清理K线数据缓存和无效交易对列表，解决连接问题")
    operation_layout.addWidget(main_window.clear_cache_button, 0, 1)
    
    # 第二行按钮
    main_window.scan_long_button = QPushButton("扫描做多信号")
    operation_layout.addWidget(main_window.scan_long_button, 1, 0)
    
    main_window.scan_short_button = QPushButton("扫描做空信号")
    operation_layout.addWidget(main_window.scan_short_button, 1, 1)
    
    # 第三行按钮
    main_window.test_case_button = QPushButton("运行测试用例")
    operation_layout.addWidget(main_window.test_case_button, 2, 0)
    
    main_window.start_scan_button = QPushButton("开始自动扫描")
    main_window.start_scan_button.setCheckable(True)
    operation_layout.addWidget(main_window.start_scan_button, 2, 1)
    
    settings_layout.addWidget(operation_group)
    
    # 添加日志区域
    log_group = QGroupBox("日志")
    log_layout = QVBoxLayout()
    log_group.setLayout(log_layout)
    
    main_window.log_text = QTextEdit()
    main_window.log_text.setReadOnly(True)
    log_layout.addWidget(main_window.log_text)
    
    # 添加日志组到布局
    settings_layout.addWidget(log_group)
    
    return settings_widget

def create_results_widget(main_window):
    """创建结果区域组件"""
    results_widget = QWidget()
    results_layout = QVBoxLayout(results_widget)
    
    # 创建水平分隔器，用于放置两个表格和日志区域
    table_splitter = QSplitter(Qt.Horizontal)
    
    # 创建做多信号区域
    long_signals_widget = QWidget()
    long_signals_layout = QVBoxLayout(long_signals_widget)
    
    # 添加做多信号标签和清除按钮
    long_header_layout = QHBoxLayout()
    long_header_layout.addWidget(QLabel("做多信号:"))
    
    # 添加清除做多信号按钮
    main_window.clear_long_signals_button = QPushButton("清除全部")
    main_window.clear_long_signals_button.setToolTip("清除所有做多信号记录")
    long_header_layout.addWidget(main_window.clear_long_signals_button)
    long_signals_layout.addLayout(long_header_layout)
    
    # 初始化做多信号表格
    main_window.long_signals_table = QTableWidget(0, 7)  # 增加一列用于删除按钮
    main_window.long_signals_table.setHorizontalHeaderLabels(["交易对", "价格", "MA7", "MA25", "MA99", "链接", "操作"])
    main_window.long_signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    main_window.long_signals_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    main_window.long_signals_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
    main_window.long_signals_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
    main_window.long_signals_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    main_window.long_signals_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    long_signals_layout.addWidget(main_window.long_signals_table)
    
    # 添加做多信号日志标签和清除按钮
    long_log_header_layout = QHBoxLayout()
    long_log_header_layout.addWidget(QLabel("做多信号日志:"))
    
    # 添加清除做多信号日志按钮
    main_window.clear_long_log_button = QPushButton("清除日志")
    main_window.clear_long_log_button.setToolTip("清除做多信号日志")
    long_log_header_layout.addWidget(main_window.clear_long_log_button)
    long_signals_layout.addLayout(long_log_header_layout)
    
    # 添加做多信号日志区域
    main_window.long_signals_log = QTextEdit()
    main_window.long_signals_log.setReadOnly(True)
    long_signals_layout.addWidget(main_window.long_signals_log)
    
    # 添加做多信号区域到分隔器
    table_splitter.addWidget(long_signals_widget)
    
    # 创建做空信号区域
    short_signals_widget = QWidget()
    short_signals_layout = QVBoxLayout(short_signals_widget)
    
    # 添加做空信号标签和清除按钮
    short_header_layout = QHBoxLayout()
    short_header_layout.addWidget(QLabel("做空信号:"))
    
    # 添加清除做空信号按钮
    main_window.clear_short_signals_button = QPushButton("清除全部")
    main_window.clear_short_signals_button.setToolTip("清除所有做空信号记录")
    short_header_layout.addWidget(main_window.clear_short_signals_button)
    short_signals_layout.addLayout(short_header_layout)
    
    # 初始化做空信号表格
    main_window.short_signals_table = QTableWidget(0, 7)  # 增加一列用于删除按钮
    main_window.short_signals_table.setHorizontalHeaderLabels(["交易对", "价格", "MA7", "MA25", "MA99", "链接", "操作"])
    main_window.short_signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    main_window.short_signals_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    main_window.short_signals_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
    main_window.short_signals_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
    main_window.short_signals_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    main_window.short_signals_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    short_signals_layout.addWidget(main_window.short_signals_table)
    
    # 添加做空信号日志标签和清除按钮
    short_log_header_layout = QHBoxLayout()
    short_log_header_layout.addWidget(QLabel("做空信号日志:"))
    
    # 添加清除做空信号日志按钮
    main_window.clear_short_log_button = QPushButton("清除日志")
    main_window.clear_short_log_button.setToolTip("清除做空信号日志")
    short_log_header_layout.addWidget(main_window.clear_short_log_button)
    short_signals_layout.addLayout(short_log_header_layout)
    
    # 添加做空信号日志区域
    main_window.short_signals_log = QTextEdit()
    main_window.short_signals_log.setReadOnly(True)
    short_signals_layout.addWidget(main_window.short_signals_log)
    
    # 添加做空信号区域到分隔器
    table_splitter.addWidget(short_signals_widget)
    
    # 设置分隔器初始大小比例 (1:1)
    table_splitter.setSizes([500, 500])
    
    # 添加表格分隔器到结果布局
    results_layout.addWidget(table_splitter)
    
    return results_widget

def create_main_layout(main_window):
    """创建主窗口布局"""
    
    # 创建中央部件
    main_window.central_widget = QWidget()
    main_window.setCentralWidget(main_window.central_widget)
    
    # 创建水平分隔器，用于放置设置区域和结果区域
    main_window.splitter = QSplitter(Qt.Horizontal)
    
    # 创建设置区域和结果区域
    main_window.settings_widget = create_settings_widget(main_window)
    main_window.results_widget = create_results_widget(main_window)
    
    # 添加设置区域和结果区域到分隔器
    main_window.splitter.addWidget(main_window.settings_widget)
    main_window.splitter.addWidget(main_window.results_widget)
    
    # 设置分隔器初始大小比例 (1:4)
    main_window.splitter.setSizes([200, 800])
    
    # 创建主布局并添加分隔器
    main_layout = QVBoxLayout()
    main_layout.addWidget(main_window.splitter)
    main_window.central_widget.setLayout(main_layout)
    
    # 设置窗口大小
    main_window.resize(1280, 720)
    
    # 返回中央部件
    return main_window.central_widget 