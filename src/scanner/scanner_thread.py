"""
扫描线程模块，实现与UI线程分离的交易对扫描功能。
"""

import os
import traceback
import pandas as pd
from datetime import datetime, timedelta
from PyQt5.QtCore import QThread, pyqtSignal
from src.scanner.signal_detector import check_long_signal, check_short_signal

# 移除全局缓存相关的变量和函数
# OHLCV_CACHE = {}
# CACHE_EXPIRY = 300  # 5分钟
# INVALID_SYMBOLS = set()

class ScannerThread(QThread):
    """扫描线程类，用于在后台执行交易对扫描操作"""
    
    # 定义信号
    progress_updated = pyqtSignal(int, int)  # 进度更新信号 (已处理数量, 总数量)
    signal_found = pyqtSignal(str, dict)  # 发现信号 (交易对, 信号数据)
    short_signal_found = pyqtSignal(str, dict)  # 发现做空信号 (交易对, 信号数据)
    scan_completed = pyqtSignal()  # 扫描完成信号
    error_occurred = pyqtSignal(str)  # 错误信号 (错误信息)
    
    def __init__(self, exchange, symbols, is_long=True, timeframe='15m', check_both=False, candle_count=10):
        """
        初始化扫描线程
        
        Args:
            exchange: 交易所实例
            symbols: 要扫描的交易对列表
            is_long: 是否扫描做多信号，False为扫描做空信号
            timeframe: K线时间周期，默认为15分钟
            check_both: 是否同时检查做多和做空信号
            candle_count: 检查的K线数量，默认为10
        """
        super().__init__()
        self.exchange = exchange
        self.symbols = symbols
        self.is_long = is_long
        self.timeframe = timeframe
        self.check_both = check_both
        self.candle_count = candle_count
        self.should_terminate = False
    
    def run(self):
        """线程的run方法，执行扫描操作"""
        try:
            total = len(self.symbols)
            processed = 0
            
            # 发送初始进度更新
            self.progress_updated.emit(processed, total)
            
            for symbol in self.symbols:
                if self.should_terminate:
                    print(f"线程已被要求终止，跳过剩余交易对")
                    break
                
                try:
                    # 直接从交易所获取K线数据，不使用缓存
                    ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=500)
                    
                    # 如果获取数据失败，跳过此交易对
                    if not ohlcv:
                        print(f"交易对 {symbol} 获取数据失败，跳过")
                        processed += 1
                        self.progress_updated.emit(processed, total)
                        continue
                    
                    # 转换OHLCV数据为DataFrame
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    # 计算移动平均线
                    df['ma7'] = df['close'].rolling(window=7).mean()
                    df['ma25'] = df['close'].rolling(window=25).mean()
                    df['ma99'] = df['close'].rolling(window=99).mean()
                    
                    # 丢弃包含NaN的行
                    df = df.dropna()
                    
                    # 根据设置检查信号
                    if self.is_long or self.check_both:
                        # 检查做多信号
                        signal_data = check_long_signal(df, self.candle_count)
                        if signal_data:
                            self.signal_found.emit(symbol, signal_data)
                    
                    if not self.is_long or self.check_both:
                        # 检查做空信号
                        signal_data = check_short_signal(df, self.candle_count)
                        if signal_data:
                            self.short_signal_found.emit(symbol, signal_data)
                    
                except Exception as e:
                    print(f"处理交易对 {symbol} 时出错: {str(e)}")
                    traceback.print_exc()
                
                # 更新进度
                processed += 1
                self.progress_updated.emit(processed, total)
            
            # 扫描完成，发送信号
            self.scan_completed.emit()
            
        except Exception as e:
            error_msg = f"扫描过程中出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.error_occurred.emit(error_msg)

    def stop(self):
        """停止扫描线程"""
        self.should_terminate = True
        print("已请求扫描线程停止")

def get_ohlcv_with_cache(exchange, symbol, timeframe='1h', limit=100, cache=None):
    """
    获取带缓存的OHLCV数据
    """
    # 检查缓存
    cache_key = f"{symbol}_{timeframe}_{limit}"
    if cache is not None and cache_key in cache:
        return cache[cache_key]
    
    try:
        # 根据exchange类型选择不同的方法获取OHLCV数据
        if hasattr(exchange, 'fetch_ohlcv') and callable(exchange.fetch_ohlcv):
            # 对于自定义的币安期货客户端
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        else:
            # 对于CCXT的交易所实例
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # 保存到缓存
        if cache is not None:
            cache[cache_key] = ohlcv
        
        return ohlcv
    except Exception as e:
        print(f"获取OHLCV数据时出错: {symbol} {timeframe}: {str(e)}")
        if "does not have a testnet/sandbox URL" in str(e):
            print(f"警告: {symbol} 请求出错，可能是测试网络URL问题，请确认使用了正确的API配置")
        return None 