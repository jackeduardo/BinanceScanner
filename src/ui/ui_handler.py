"""
UI处理器模块，用于处理UI事件和交互
"""

import os
import json
import time
import logging
import traceback
from datetime import datetime, timedelta
from PyQt5.QtCore import QUrl, QTimer, QObject
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QPushButton
from PyQt5.QtGui import QDesktopServices

from src.utils.config import load_config_from_file, save_config_to_file
from src.utils.exchange_utils import get_exchange_instance, setup_exchange
from src.utils.url_generator import generate_trade_url
from src.utils.market_utils import get_market_symbols
from src.scanner.scanner_pool import ScannerPool

def setup_event_handlers(window):
    """设置UI组件的事件处理"""
    # 连接开始扫描按钮
    window.scan_long_button.clicked.connect(lambda: scan_long_signals(window))
    window.scan_short_button.clicked.connect(lambda: scan_short_signals(window))
    window.start_scan_button.clicked.connect(lambda: start_scanning(window))
    
    # 连接API设置
    window.apply_api_button.clicked.connect(lambda: apply_api_settings(window))
    window.save_api_button.clicked.connect(lambda: save_api_settings(window))
    
    # 连接币种过滤器
    window.add_filter_button.clicked.connect(lambda: add_coin_filter(window))
    window.remove_filter_button.clicked.connect(lambda: remove_coin_filter(window))
    window.clear_filter_button.clicked.connect(lambda: clear_coin_filter(window))
    
    # 连接交易所变更事件
    window.exchange_combo.currentTextChanged.connect(lambda: exchange_changed(window))
    window.market_type_combo.currentTextChanged.connect(lambda: market_type_changed(window))
    
    # 只连接"连接到交易所"按钮
    window.connect_button.clicked.connect(lambda: connect_to_exchange(window))

def auto_connect(window):
    """自动连接到交易所"""
    try:
        # 修改为只显示提示信息，不再自动连接
        window.log_text.append("请点击'连接到交易所'按钮进行连接")
        return False
    except Exception as e:
        window.log_text.append(f"自动连接失败: {str(e)}")
        return False

def exchange_changed(window):
    """处理交易所变更事件"""
    # 更新市场类型下拉选项
    current_exchange = window.exchange_combo.currentText()
    window.market_type_combo.clear()
    
    if "币安" in current_exchange or "Binance" in current_exchange:
        window.market_type_combo.addItem("现货(Spot)")
        window.market_type_combo.addItem("期货(U本位)")
        window.market_type_combo.addItem("期货(币本位)")
    else:
        window.market_type_combo.addItem("现货(Spot)")
    
    # 触发市场类型变更事件
    market_type_changed(window)

def market_type_changed(window):
    """处理市场类型变更事件"""
    # 更新永续合约选择框的可见性
    current_market = window.market_type_combo.currentText()
    if "期货" in current_market:
        window.perpetual_only_checkbox.setVisible(True)
        window.perpetual_only_label.setVisible(True)
    else:
        window.perpetual_only_checkbox.setVisible(False)
        window.perpetual_only_label.setVisible(False)
    
    # 尝试更新市场数据
    update_market_data(window)

def update_market_data(window):
    """更新市场数据"""
    try:
        if not hasattr(window, 'exchange') or window.exchange is None:
            # 提示用户需要先连接
            window.log_text.append("请先连接到交易所后再更新市场数据")
            return False
        
        # 获取当前交易所和市场类型
        exchange_name = window.exchange_combo.currentText()
        market_type = window.market_type_combo.currentText()
        perpetual_only = window.perpetual_only_checkbox.isChecked()
        
        window.log_text.append(f"选择的交易所: {exchange_name}, 市场类型: {market_type}")
        
        # 获取市场符号
        symbols = get_market_symbols(window.exchange, market_type, perpetual_only)
        
        # 仅保留USDT交易对
        usdt_symbols = [s for s in symbols if "/USDT" in s]
        
        window.log_text.append(f"USDT交易对数量: {len(usdt_symbols)}")
        if usdt_symbols:
            sample = usdt_symbols[:5]
            window.log_text.append(f"USDT交易对示例: {sample}")
        
        # 保存到窗口实例
        window.symbols = usdt_symbols
        
        # 更新交易对过滤列表
        update_coin_filter_list(window)
        
        return True
    except Exception as e:
        window.log_text.append(f"更新市场数据时出错: {str(e)}")
        traceback.print_exc()
        return False

def apply_api_settings(window):
    """应用API设置"""
    try:
        api_key = window.api_key_input.text().strip()
        api_secret = window.api_secret_input.text().strip()
        
        if not api_key or not api_secret:
            window.log_text.append("API密钥或密钥不能为空")
            return
        
        # 保存API设置到配置
        config = {
            "api_key": api_key,
            "api_secret": api_secret,
            "exchange": window.exchange_combo.currentText(),
            "market_type": window.market_type_combo.currentText()
        }
        
        save_config_to_file(config)
        window.log_text.append("API设置已保存")
        
        # 尝试连接到交易所
        connect_to_exchange(window)
    except Exception as e:
        window.log_text.append(f"应用API设置时出错: {str(e)}")

def connect_to_exchange(window):
    """连接到交易所"""
    try:
        window.log_text.append("正在连接到交易所...")
        
        # 获取当前选择的交易所和市场类型
        exchange_name = window.exchange_combo.currentText()
        market_type = window.market_type_combo.currentText()
        
        # 获取API密钥和密钥
        api_key = window.api_key_input.text().strip()
        api_secret = window.api_secret_input.text().strip()
        
        # 获取代理设置
        use_proxy = window.use_proxy_checkbox.isChecked()
        proxy_url = window.proxy_input.text().strip() if use_proxy else None
        
        # 创建交易所实例参数
        kwargs = {}
        
        # 设置代理
        if use_proxy and proxy_url:
            window.log_text.append(f"使用代理: {proxy_url}")
            kwargs['proxies'] = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # 设置超时
        if hasattr(window, 'timeout_input'):
            timeout = window.timeout_input.value()
            kwargs['timeout'] = timeout
            window.log_text.append(f"设置请求超时: {timeout}ms")
        
        # 设置和获取交易所实例
        window.log_text.append(f"使用{exchange_name}{market_type}")
        
        # 对币安期货进行特殊处理
        if exchange_name == "币安(Binance)" and market_type == "期货(U本位)":
            from src.utils.ccxt_helper import BinanceFuturesClient
            # 设置期货API直接创建客户端
            window.log_text.append("创建币安U本位期货客户端...")
            proxies = kwargs.get('proxies')
            timeout = kwargs.get('timeout', 30000)
            
            # 直接创建期货客户端实例
            exchange = BinanceFuturesClient(api_key, api_secret, proxies, timeout)
            window.log_text.append("币安U本位期货客户端创建成功")
        else:
            # 使用常规方式创建交易所实例
            exchange = get_exchange_instance(exchange_name, market_type, api_key, api_secret, **kwargs)
        
        if not exchange:
            window.log_text.append("创建交易所实例失败")
            return False
        
        # 测试连接
        try:
            # 根据交易所类型选择不同的测试方法
            if hasattr(exchange, 'ping') and callable(exchange.ping):
                # 对于我们自定义的币安期货客户端
                window.log_text.append("检测到币安U本位期货客户端，使用专用测试方法")
                
                # 1. 使用最基本的ping接口测试
                window.log_text.append("1. 测试期货API ping...")
                response = exchange.ping()
                window.log_text.append("✓ 期货API ping成功")
                
                # 2. 获取交易所时间
                window.log_text.append("2. 获取交易所服务器时间...")
                time_response = exchange.get_time()
                server_time = datetime.fromtimestamp(time_response['serverTime'] / 1000)
                window.log_text.append(f"✓ 交易所服务器时间: {server_time}")
                
                # 3. 获取交易所信息（不需要签名）
                window.log_text.append("3. 获取交易所信息...")
                exchange_info = exchange.get_exchange_info()
                symbols_count = len(exchange_info['symbols'])
                window.log_text.append(f"✓ 交易所信息获取成功，共有 {symbols_count} 个交易对")
                
                # 4. 加载市场数据
                window.log_text.append("4. 加载市场数据...")
                markets = exchange.load_markets()
                window.log_text.append(f"✓ 市场数据加载成功，找到 {len(exchange.symbols)} 个交易对")
                
                window.log_text.append("币安期货API连接测试全部通过!")
            elif 'binanceusdm' in str(exchange):
                # 向后兼容，以防使用原始CCXT库
                window.log_text.append("检测到币安U本位期货，使用CCXT方法")
                
                # 1. 使用最基本的ping接口测试
                window.log_text.append("1. 测试期货API ping...")
                response = exchange.fapiPublic_get_ping()
                window.log_text.append("✓ 期货API ping成功")
                
                # 2. 获取交易所时间
                window.log_text.append("2. 获取交易所服务器时间...")
                time_response = exchange.fapiPublic_get_time()
                server_time = datetime.fromtimestamp(time_response['serverTime'] / 1000)
                window.log_text.append(f"✓ 交易所服务器时间: {server_time}")
                
                # 3. 获取交易所信息（不需要签名）
                window.log_text.append("3. 获取交易所信息...")
                exchange_info = exchange.fapiPublic_get_exchangeinfo()
                symbols_count = len(exchange_info['symbols'])
                window.log_text.append(f"✓ 交易所信息获取成功，共有 {symbols_count} 个交易对")
                
                # 4. 加载市场数据
                window.log_text.append("4. 加载市场数据...")
                markets = exchange.load_markets()
                window.log_text.append(f"✓ 市场数据加载成功，找到 {len(exchange.symbols)} 个交易对")
                
                window.log_text.append("币安期货API连接测试全部通过!")
            else:
                # 对于其他交易所，加载市场以测试连接
                exchange.load_markets()
                window.log_text.append("市场数据加载成功")
            
            # 显示交易对数量
            symbols = exchange.symbols
            window.log_text.append(f"总交易对数量: {len(symbols)}")
            if symbols:
                sample = symbols[:5]
                window.log_text.append(f"交易对示例: {sample}")
            
            # 保存交易所实例到窗口
            window.exchange = exchange
            
            # 标记连接成功
            window.is_connected = True
            window.connection_status_label.setText("已连接")
            window.connection_status_label.setStyleSheet("color: green;")
            
            # 更新窗口标题
            if hasattr(window, 'update_window_title'):
                window.update_window_title()
            
            # 更新市场数据
            perpetual_only = window.perpetual_only_checkbox.isChecked()
            window.symbols = get_market_symbols(exchange, market_type, perpetual_only)
            
            # 更新币种过滤列表
            update_coin_filter_list(window)
            
            return True
        except Exception as e:
            window.log_text.append(f"连接测试失败: {str(e)}")
            window.is_connected = False
            window.connection_status_label.setText("未连接")
            window.connection_status_label.setStyleSheet("color: red;")
            return False
    except Exception as e:
        window.log_text.append(f"连接过程中出错: {str(e)}")
        traceback.print_exc()
        return False

def save_api_settings(window):
    """保存API设置到配置文件"""
    try:
        # 获取API设置
        config = {
            "api_key": window.api_key_input.text().strip(),
            "api_secret": window.api_secret_input.text().strip(),
            "exchange": window.exchange_combo.currentText(),
            "market_type": window.market_type_combo.currentText(),
            "perpetual_only": window.perpetual_only_checkbox.isChecked()
        }
        
        # 保存配置
        save_config_to_file(config)
        window.log_text.append("API设置已保存到配置文件")
    except Exception as e:
        window.log_text.append(f"保存API设置时出错: {str(e)}")

def add_coin_filter(window):
    """添加币种到过滤列表"""
    try:
        # 获取输入的币种
        coin = window.coin_filter_input.text().strip().upper()
        if not coin:
            return
        
        # 检查币种是否已在列表中
        if coin not in window.coin_filter_list.findItems(coin, Qt.MatchExactly):
            window.coin_filter_list.addItem(coin)
            window.coin_filter_input.clear()
    except Exception as e:
        window.log_text.append(f"添加币种过滤器时出错: {str(e)}")

def remove_coin_filter(window):
    """从过滤列表中删除选中的币种"""
    try:
        # 获取选中的项
        selected_items = window.coin_filter_list.selectedItems()
        if not selected_items:
            return
        
        # 删除选中的项
        for item in selected_items:
            window.coin_filter_list.takeItem(window.coin_filter_list.row(item))
    except Exception as e:
        window.log_text.append(f"删除币种过滤器时出错: {str(e)}")

def clear_coin_filter(window):
    """清空币种过滤列表"""
    try:
        window.coin_filter_list.clear()
    except Exception as e:
        window.log_text.append(f"清空币种过滤器时出错: {str(e)}")

def update_coin_filter_list(window):
    """更新币种过滤列表控件"""
    try:
        # 清空现有列表
        window.coin_filter_list.clear()
        
        # 如果没有可用的交易对，直接返回
        if not hasattr(window, 'symbols') or not window.symbols:
            return
        
        # 提取所有币种
        coins = set()
        for symbol in window.symbols:
            # 从交易对中提取基础币种
            if '/' in symbol:
                base_coin = symbol.split('/')[0]
                coins.add(base_coin)
        
        # 添加到列表控件
        for coin in sorted(coins):
            window.coin_filter_list.addItem(coin)
    except Exception as e:
        window.log_text.append(f"更新币种过滤列表时出错: {str(e)}")

def get_filtered_symbols(window):
    """根据过滤器获取符合条件的交易对"""
    try:
        # 如果没有可用的交易对，直接返回空列表
        if not hasattr(window, 'symbols') or not window.symbols:
            window.log_text.append("没有可用的交易对")
            return []
        
        # 获取选择的币种过滤器
        selected_items = window.coin_filter_list.selectedItems()
        selected_coins = [item.text() for item in selected_items]
        
        # 如果没有选择币种，使用所有交易对
        if not selected_coins:
            window.log_text.append(f"使用所有 {len(window.symbols)} 个交易对进行扫描")
            return window.symbols
        
        # 根据选择的币种过滤交易对
        filtered_symbols = []
        for symbol in window.symbols:
            for coin in selected_coins:
                if '/' in symbol and symbol.split('/')[0] == coin:
                    filtered_symbols.append(symbol)
                    break
        
        window.log_text.append(f"已选择 {len(filtered_symbols)}/{len(window.symbols)} 个交易对进行扫描")
        return filtered_symbols
    except Exception as e:
        window.log_text.append(f"过滤交易对时出错: {str(e)}")
        return []

def scan_long_signals(window):
    """扫描做多信号"""
    try:
        # 检查连接状态
        if not hasattr(window, 'exchange') or not window.exchange:
            window.log_text.append("请先连接到交易所")
            return
        
        # 获取过滤后的交易对
        symbols = get_filtered_symbols(window)
        if not symbols:
            window.log_text.append("没有符合条件的交易对")
            return
        
        # 获取选择的时间周期
        timeframe = window.timeframe_combo.currentText()
        
        # 创建扫描线程池
        window.log_text.append(f"开始扫描做多信号，时间周期: {timeframe}，交易对数量: {len(symbols)}")
        
        # 停止之前的扫描（如果有）
        stop_current_scans(window)
        
        # 创建并启动新的扫描池
        window.long_scanner_pool = ScannerPool(
            window.exchange,
            symbols,
            is_long=True,
            timeframe=timeframe,
            window=window
        )
        
        # 连接信号
        window.long_scanner_pool.progress_updated.connect(lambda current, total: update_progress(window, current, total, True))
        window.long_scanner_pool.signal_found.connect(lambda symbol, data: handle_signal_found(window, symbol, data, True))
        window.long_scanner_pool.scan_completed.connect(lambda: handle_scan_completed(window, is_long=True))
        window.long_scanner_pool.scan_error.connect(lambda msg: window.log_text.append(f"扫描错误: {msg}"))
        
        # 启动扫描
        window.long_scanner_pool.run()
        
        # 更新UI状态
        window.scan_long_button.setEnabled(False)
        window.scan_short_button.setEnabled(False)
        window.start_scan_button.setEnabled(False)
        window.scanning_long_label.setVisible(True)
        
    except Exception as e:
        window.log_text.append(f"启动做多信号扫描时出错: {str(e)}")
        traceback.print_exc()

def scan_short_signals(window):
    """扫描做空信号"""
    try:
        # 检查连接状态
        if not hasattr(window, 'exchange') or not window.exchange:
            window.log_text.append("请先连接到交易所")
            return
        
        # 获取过滤后的交易对
        symbols = get_filtered_symbols(window)
        if not symbols:
            window.log_text.append("没有符合条件的交易对")
            return
        
        # 获取选择的时间周期
        timeframe = window.timeframe_combo.currentText()
        
        # 创建扫描线程池
        window.log_text.append(f"开始扫描做空信号，时间周期: {timeframe}，交易对数量: {len(symbols)}")
        
        # 停止之前的扫描（如果有）
        stop_current_scans(window)
        
        # 创建并启动新的扫描池
        window.short_scanner_pool = ScannerPool(
            window.exchange,
            symbols,
            is_long=False,
            timeframe=timeframe,
            window=window
        )
        
        # 连接信号
        window.short_scanner_pool.progress_updated.connect(lambda current, total: update_progress(window, current, total, False))
        window.short_scanner_pool.signal_found.connect(lambda symbol, data: handle_signal_found(window, symbol, data, False))
        window.short_scanner_pool.scan_completed.connect(lambda: handle_scan_completed(window, is_long=False))
        window.short_scanner_pool.scan_error.connect(lambda msg: window.log_text.append(f"扫描错误: {msg}"))
        
        # 启动扫描
        window.short_scanner_pool.run()
        
        # 更新UI状态
        window.scan_long_button.setEnabled(False)
        window.scan_short_button.setEnabled(False)
        window.start_scan_button.setEnabled(False)
        window.scanning_short_label.setVisible(True)
        
    except Exception as e:
        window.log_text.append(f"启动做空信号扫描时出错: {str(e)}")
        traceback.print_exc()

def handle_scan_completed(window, is_long=True):
    """处理扫描完成事件"""
    try:
        if is_long:
            window.log_text.append("做多信号扫描完成")
            window.scanning_long_label.setVisible(False)
            
            # 如果短线扫描也不在运行，则重新启用按钮
            if not hasattr(window, 'short_scanner_pool') or not window.short_scanner_pool or not window.short_scanner_pool.running:
                window.scan_long_button.setEnabled(True)
                window.scan_short_button.setEnabled(True)
                window.start_scan_button.setEnabled(True)
        else:
            window.log_text.append("做空信号扫描完成")
            window.scanning_short_label.setVisible(False)
            
            # 如果长线扫描也不在运行，则重新启用按钮
            if not hasattr(window, 'long_scanner_pool') or not window.long_scanner_pool or not window.long_scanner_pool.running:
                window.scan_long_button.setEnabled(True)
                window.scan_short_button.setEnabled(True)
                window.start_scan_button.setEnabled(True)
                
        # 处理自动扫描的完成
        if hasattr(window, 'auto_scanning') and window.auto_scanning:
            # 如果是最后一次扫描，重置自动扫描状态
            if hasattr(window, 'auto_scan_count'):
                window.auto_scan_count += 1
                remaining = window.auto_scan_total - window.auto_scan_count
                
                if remaining <= 0:
                    stop_automatic_scanning(window)
                    window.log_text.append("自动扫描完成")
                else:
                    # 启动下一次自动扫描的倒计时
                    window.auto_scan_timer.start(window.auto_scan_interval * 1000)
                    window.log_text.append(f"将在 {window.auto_scan_interval} 秒后进行下一次扫描，剩余 {remaining} 次")
                    
                    # 更新倒计时进度条初始值
                    window.countdown_remaining = window.auto_scan_interval
                    window.update_countdown_progress_bar.setValue(100)  # 初始值100%
                    
                    # 启动倒计时更新计时器
                    window.countdown_timer.start(1000)  # 每秒更新一次
                
    except Exception as e:
        window.log_text.append(f"处理扫描完成事件时出错: {str(e)}")
        traceback.print_exc()

def update_progress(window, current, total, is_long=True):
    """更新进度条和日志"""
    try:
        # 计算百分比
        percentage = int((current / total) * 100) if total > 0 else 0
        
        # 更新相应的进度条
        if is_long:
            window.long_progress_bar.setValue(percentage)
            window.long_progress_label.setText(f"{current}/{total} ({percentage}%)")
        else:
            window.short_progress_bar.setValue(percentage)
            window.short_progress_label.setText(f"{current}/{total} ({percentage}%)")
        
        # 定期更新日志
        if current % 50 == 0 or current == total:
            signal_type = "做多" if is_long else "做空"
            window.log_text.append(f"{signal_type}信号扫描进度: {current}/{total} ({percentage}%)")
    except Exception as e:
        print(f"更新进度时出错: {str(e)}")

def handle_signal_found(window, symbol, data, is_long=None):
    """处理发现信号事件"""
    try:
        # 获取信号数据
        price = data['close']
        ma7 = data['ma7']
        ma25 = data['ma25']
        ma99 = data.get('ma99', 0)  # 可能不存在ma99
        timestamp = data['timestamp'].strftime('%H:%M:%S') if hasattr(data['timestamp'], 'strftime') else str(data['timestamp'])
        
        # 确定信号类型
        # 如果传入is_long参数，直接使用；否则根据MA7和MA25的关系判断
        if is_long is None:
            signal_type = "做多" if ma7 > ma25 else "做空"
        else:
            signal_type = "做多" if is_long else "做空"
        
        # 构建信号描述
        if signal_type == "做多":
            desc = f"做多信号：MA7({ma7:.2f})上穿MA25({ma25:.2f})，上一根K线收盘价({price:.2f})在MA7({ma7:.2f})上方"
        else:
            desc = f"做空信号：MA7({ma7:.2f})下穿MA25({ma25:.2f})，上一根K线收盘价({price:.2f})在MA7({ma7:.2f})下方"
        
        # 记录到日志
        window.log_text.append(desc)
        window.log_text.append(f"发现{signal_type}信号: {symbol}, 价格: {price:.4f}, MA7: {ma7:.4f}")
        
        # 生成交易URL - 强制使用期货URL格式
        if '/' in symbol:
            base, quote = symbol.split('/')
        else:
            # 假设是BTCUSDT格式
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                quote = 'USDT'
            else:
                base = symbol
                quote = 'USDT'
        
        # 直接构造币安U本位期货URL，不使用exchange_id判断
        symbol_formatted = f"{base}{quote}".upper()
        url = f"https://www.binance.com/zh-CN/futures/{symbol_formatted}"
        
        # 直接添加到相应的信号表格中
        if signal_type == "做多":
            table = window.long_signals_table
        else:
            table = window.short_signals_table
            
        # 添加新行
        row_position = table.rowCount()
        table.insertRow(row_position)
        
        # 添加数据到表格 - 注意列的顺序应该与表头定义一致
        # ["交易对", "价格", "MA7", "MA25", "MA99", "链接"]
        table.setItem(row_position, 0, QTableWidgetItem(symbol))
        table.setItem(row_position, 1, QTableWidgetItem(f"{price:.4f}"))
        table.setItem(row_position, 2, QTableWidgetItem(f"{ma7:.4f}"))
        table.setItem(row_position, 3, QTableWidgetItem(f"{ma25:.4f}"))
        table.setItem(row_position, 4, QTableWidgetItem(f"{ma99:.4f}"))
        
        # 添加查看按钮
        view_button = QPushButton("查看")
        view_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        table.setCellWidget(row_position, 5, view_button)
        
        # 添加到相应的日志框中
        log_text = f"{symbol} - 价格: {price:.4f}, MA7: {ma7:.4f}, MA25: {ma25:.4f}, 时间: {timestamp}"
        if signal_type == "做多":
            window.long_signals_log.append(log_text)
        else:
            window.short_signals_log.append(log_text)
        
    except Exception as e:
        window.log_text.append(f"处理信号时出错: {str(e)}")
        traceback.print_exc()

def start_scanning(window):
    """开始或停止自动扫描"""
    try:
        # 如果已经在自动扫描，则停止
        if hasattr(window, 'auto_scanning') and window.auto_scanning:
            stop_automatic_scanning(window)
            return
        
        # 检查连接状态
        if not hasattr(window, 'exchange') or not window.exchange:
            window.log_text.append("请先连接到交易所")
            return
        
        # 获取过滤后的交易对
        symbols = get_filtered_symbols(window)
        if not symbols:
            window.log_text.append("没有符合条件的交易对")
            return
        
        # 获取扫描参数
        timeframe = window.timeframe_combo.currentText()
        scan_interval = int(window.auto_scan_interval_input.text())
        scan_count = int(window.auto_scan_count_input.text())
        
        # 验证参数
        if scan_interval < 10:
            window.log_text.append("自动扫描间隔不能小于10秒")
            return
        
        if scan_count < 1:
            window.log_text.append("自动扫描次数不能小于1次")
            return
        
        # 停止当前正在进行的任何扫描
        stop_current_scans(window)
        
        # 设置自动扫描状态
        window.auto_scanning = True
        window.auto_scan_interval = scan_interval
        window.auto_scan_count = 0
        window.auto_scan_total = scan_count
        
        # 更新按钮文本
        window.start_scan_button.setText("停止自动扫描")
        
        # 禁用其他扫描按钮
        window.scan_long_button.setEnabled(False)
        window.scan_short_button.setEnabled(False)
        
        # 创建自动扫描计时器
        window.auto_scan_timer = QTimer()
        window.auto_scan_timer.timeout.connect(lambda: perform_auto_scan(window))
        
        # 创建倒计时计时器
        window.countdown_timer = QTimer()
        window.countdown_timer.timeout.connect(lambda: update_countdown(window))
        window.countdown_remaining = 0
        
        # 立即执行第一次扫描
        window.log_text.append(f"开始自动扫描，每 {scan_interval} 秒扫描一次，共 {scan_count} 次")
        perform_auto_scan(window)
        
    except Exception as e:
        window.log_text.append(f"启动自动扫描时出错: {str(e)}")
        traceback.print_exc()

def stop_automatic_scanning(window):
    """停止自动扫描"""
    try:
        window.log_text.append("正在停止自动扫描...")
        
        # 停止计时器
        if hasattr(window, 'auto_scan_timer') and window.auto_scan_timer:
            window.auto_scan_timer.stop()
        
        if hasattr(window, 'countdown_timer') and window.countdown_timer:
            window.countdown_timer.stop()
        
        # 停止当前正在进行的扫描
        stop_current_scans(window)
        
        # 重置自动扫描状态
        window.auto_scanning = False
        window.start_scan_button.setText("开始自动扫描")
        
        # 恢复按钮状态
        window.scan_long_button.setEnabled(True)
        window.scan_short_button.setEnabled(True)
        
        # 隐藏扫描标签
        window.scanning_long_label.setVisible(False)
        window.scanning_short_label.setVisible(False)
        
        # 重置进度条
        window.long_progress_bar.setValue(0)
        window.short_progress_bar.setValue(0)
        window.update_countdown_progress_bar.setValue(0)
        
        window.log_text.append("自动扫描已停止")
        
    except Exception as e:
        window.log_text.append(f"停止自动扫描时出错: {str(e)}")
        traceback.print_exc()

def stop_current_scans(window):
    """停止当前正在进行的所有扫描"""
    try:
        # 停止长线扫描
        if hasattr(window, 'long_scanner_pool') and window.long_scanner_pool:
            window.log_text.append("正在停止做多信号扫描...")
            window.long_scanner_pool.stop()
            window.long_scanner_pool = None
            window.scanning_long_label.setVisible(False)
        
        # 停止短线扫描
        if hasattr(window, 'short_scanner_pool') and window.short_scanner_pool:
            window.log_text.append("正在停止做空信号扫描...")
            window.short_scanner_pool.stop()
            window.short_scanner_pool = None
            window.scanning_short_label.setVisible(False)
        
        window.log_text.append("所有扫描已停止")
        
    except Exception as e:
        window.log_text.append(f"停止当前扫描时出错: {str(e)}")
        traceback.print_exc()

def perform_auto_scan(window):
    """执行自动扫描"""
    try:
        # 如果不在自动扫描模式，则退出
        if not hasattr(window, 'auto_scanning') or not window.auto_scanning:
            return
        
        # 获取过滤后的交易对
        symbols = get_filtered_symbols(window)
        if not symbols:
            window.log_text.append("没有符合条件的交易对，跳过此次自动扫描")
            return
        
        # 获取选择的时间周期
        timeframe = window.timeframe_combo.currentText()
        
        # 记录扫描开始
        scan_no = window.auto_scan_count + 1
        scan_total = window.auto_scan_total
        window.log_text.append(f"开始第 {scan_no}/{scan_total} 次自动扫描，时间周期: {timeframe}")
        
        # 创建并启动长线扫描
        window.long_scanner_pool = ScannerPool(
            window.exchange,
            symbols,
            is_long=True,
            timeframe=timeframe,
            window=window
        )
        
        # 连接长线扫描信号
        window.long_scanner_pool.progress_updated.connect(lambda current, total: update_progress(window, current, total, True))
        window.long_scanner_pool.signal_found.connect(lambda symbol, data: handle_signal_found(window, symbol, data, True))
        window.long_scanner_pool.scan_completed.connect(lambda: long_scan_completed_in_auto_mode(window))
        window.long_scanner_pool.scan_error.connect(lambda msg: window.log_text.append(f"长线扫描错误: {msg}"))
        
        # 启动长线扫描
        window.long_scanner_pool.run()
        window.scanning_long_label.setVisible(True)
        
    except Exception as e:
        window.log_text.append(f"执行自动扫描时出错: {str(e)}")
        traceback.print_exc()

def long_scan_completed_in_auto_mode(window):
    """自动模式下长线扫描完成后的处理"""
    try:
        window.log_text.append("自动模式下做多信号扫描完成")
        window.scanning_long_label.setVisible(False)
        
        # 启动短线扫描
        # 获取过滤后的交易对
        symbols = get_filtered_symbols(window)
        if not symbols:
            window.log_text.append("没有符合条件的交易对，跳过做空信号扫描")
            # 直接标记为完成
            handle_scan_completed(window, is_long=False)
            return
        
        # 获取选择的时间周期
        timeframe = window.timeframe_combo.currentText()
        
        # 创建并启动短线扫描
        window.short_scanner_pool = ScannerPool(
            window.exchange,
            symbols,
            is_long=False,
            timeframe=timeframe,
            window=window
        )
        
        # 连接短线扫描信号
        window.short_scanner_pool.progress_updated.connect(lambda current, total: update_progress(window, current, total, False))
        window.short_scanner_pool.signal_found.connect(lambda symbol, data: handle_signal_found(window, symbol, data, False))
        window.short_scanner_pool.scan_completed.connect(lambda: handle_scan_completed(window, is_long=False))
        window.short_scanner_pool.scan_error.connect(lambda msg: window.log_text.append(f"短线扫描错误: {msg}"))
        
        # 启动短线扫描
        window.short_scanner_pool.run()
        window.scanning_short_label.setVisible(True)
        
    except Exception as e:
        window.log_text.append(f"自动模式下处理长线扫描完成事件时出错: {str(e)}")
        traceback.print_exc()
        # 确保标记为完成
        handle_scan_completed(window, is_long=True)

def update_countdown(window):
    """更新倒计时"""
    try:
        if not hasattr(window, 'countdown_remaining'):
            return
        
        # 减少剩余时间
        window.countdown_remaining -= 1
        
        # 计算百分比
        percentage = int((window.countdown_remaining / window.auto_scan_interval) * 100)
        
        # 更新进度条
        window.update_countdown_progress_bar.setValue(percentage)
        
        # 更新倒计时文本
        minutes = window.countdown_remaining // 60
        seconds = window.countdown_remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        window.countdown_label.setText(f"下次扫描倒计时: {time_str}")
        
        # 如果倒计时结束，停止计时器
        if window.countdown_remaining <= 0:
            window.countdown_timer.stop()
            
    except Exception as e:
        print(f"更新倒计时时出错: {str(e)}")
        traceback.print_exc()

def handle_close_event(window, event):
    """处理窗口关闭事件"""
    try:
        # 停止所有定时器
        if hasattr(window, 'auto_scan_timer') and window.auto_scan_timer:
            window.auto_scan_timer.stop()
        
        if hasattr(window, 'countdown_timer') and window.countdown_timer:
            window.countdown_timer.stop()
        
        # 停止所有扫描线程
        if hasattr(window, 'long_scanner_pool') and window.long_scanner_pool:
            window.long_scanner_pool.stop()
        
        if hasattr(window, 'short_scanner_pool') and window.short_scanner_pool:
            window.short_scanner_pool.stop()
        
        # 接受关闭事件
        event.accept()
        
    except Exception as e:
        print(f"关闭窗口时出错: {str(e)}")
        traceback.print_exc()
        event.accept()  # 确保窗口能够关闭

        