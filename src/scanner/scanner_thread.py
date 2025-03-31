"""
扫描线程模块，实现与UI线程分离的交易对扫描功能。
"""

import os
import traceback
import pandas as pd
from datetime import datetime, timedelta
from PyQt5.QtCore import QThread, pyqtSignal
from src.scanner.signal_detector import check_long_signal, check_short_signal
import time

# 定义全局缓存和过期时间(秒)
OHLCV_CACHE = {}
CACHE_EXPIRY = 300  # 缓存过期时间(秒)
INVALID_SYMBOLS = set()  # 存储无效的交易对

def clear_ohlcv_cache():
    """
    清理K线数据缓存
    
    Returns:
        int: 清理前缓存的大小
    """
    global OHLCV_CACHE
    cache_size = len(OHLCV_CACHE)
    OHLCV_CACHE = {}
    print(f"已清理K线缓存，共清理 {cache_size} 条数据")
    return cache_size

def clear_invalid_symbols():
    """
    清理无效的交易对列表
    
    Returns:
        int: 清理前无效交易对的数量
    """
    global INVALID_SYMBOLS
    invalid_size = len(INVALID_SYMBOLS)
    INVALID_SYMBOLS = set()
    print(f"已清理无效交易对列表，共清理 {invalid_size} 个交易对")
    return invalid_size

def is_symbol_invalid(symbol):
    """
    检查交易对是否在无效列表中
    
    Args:
        symbol (str): 交易对名称
        
    Returns:
        bool: 如果交易对无效返回True，否则返回False
    """
    return symbol in INVALID_SYMBOLS

def mark_symbol_as_invalid(symbol):
    """
    将交易对标记为无效
    
    Args:
        symbol (str): 要标记为无效的交易对名称
    """
    INVALID_SYMBOLS.add(symbol)
    print(f"已将交易对 {symbol} 添加到无效列表，当前无效交易对数量: {len(INVALID_SYMBOLS)}")

def get_ohlcv_with_cache(exchange, symbol, timeframe, limit=100, cache=None):
    """
    获取OHLCV数据，支持缓存
    
    Args:
        exchange: CCXT交易所实例
        symbol (str): 交易对名称
        timeframe (str): 时间周期
        limit (int): 获取的K线数量
        cache (dict, optional): 可选的外部缓存字典，如果不提供则使用全局缓存
        
    Returns:
        list: OHLCV数据列表，如果获取失败则返回空列表
    """
    global OHLCV_CACHE
    
    # 如果交易对被标记为无效，直接跳过
    if is_symbol_invalid(symbol):
        print(f"交易对 {symbol} 在无效列表中，跳过处理")
        return []
    
    # 使用传入的缓存或全局缓存
    cache_to_use = cache if cache is not None else OHLCV_CACHE
    cache_key = f"{symbol}_{timeframe}_{limit}"
    
    # 检查缓存中是否有数据且未过期
    current_time = time.time()
    if cache_key in cache_to_use:
        cache_time, data = cache_to_use[cache_key]
        if current_time - cache_time < CACHE_EXPIRY:
            return data
    
    # 缓存中没有数据或已过期，从交易所获取
    try:
        print(f"从交易所获取 {symbol} 的K线数据")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # 验证数据是否有效
        if not ohlcv or len(ohlcv) < 10:  # 确保至少有10条数据
            print(f"交易对 {symbol} 获取的数据不足，可能是无效交易对")
            return []
        
        # 更新缓存
        cache_to_use[cache_key] = (current_time, ohlcv)
        return ohlcv
        
    except Exception as e:
        error_msg = str(e)
        print(f"获取 {symbol} 的K线数据时出错: {error_msg}")
        
        # 检查错误类型，将特定错误的交易对标记为无效
        if any(x in error_msg for x in [
            "does not have a testnet/sandbox URL", 
            "symbol not found", 
            "not supported",
            "Unknown symbol",
            "Invalid symbol"
        ]):
            mark_symbol_as_invalid(symbol)
        
        return []

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
                    # 检查交易对是否无效
                    if is_symbol_invalid(symbol):
                        print(f"跳过无效交易对 {symbol}")
                        processed += 1
                        self.progress_updated.emit(processed, total)
                        continue
                    
                    # 使用带缓存的方法获取OHLCV数据
                    ohlcv = get_ohlcv_with_cache(self.exchange, symbol, self.timeframe, limit=500)
                    
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
                    error_msg = str(e)
                    print(f"处理交易对 {symbol} 时出错: {error_msg}")
                    
                    # 检查是否需要标记为无效交易对
                    if any(x in error_msg for x in [
                        "does not have a testnet/sandbox URL", 
                        "symbol not found", 
                        "not supported",
                        "Unknown symbol",
                        "Invalid symbol"
                    ]):
                        print(f"将交易对标记为无效: {symbol}")
                        mark_symbol_as_invalid(symbol)
                    
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

    def get_ohlcv_with_cache(self, exchange, symbol, timeframe, limit=100, cache=None):
        """
        获取OHLCV数据，支持缓存
        
        Args:
            exchange: CCXT交易所实例
            symbol (str): 交易对名称
            timeframe (str): 时间周期
            limit (int): 获取的K线数量
            cache (dict, optional): 可选的外部缓存字典，如果不提供则使用全局缓存
            
        Returns:
            list: OHLCV数据列表，如果获取失败则返回空列表
        """
        global OHLCV_CACHE
        
        # 如果交易对被标记为无效，直接跳过
        if is_symbol_invalid(symbol):
            print(f"交易对 {symbol} 在无效列表中，跳过处理")
            return []
        
        # 使用传入的缓存或全局缓存
        cache_to_use = cache if cache is not None else OHLCV_CACHE
        cache_key = f"{symbol}_{timeframe}_{limit}"
        
        # 检查缓存中是否有数据且未过期
        current_time = time.time()
        if cache_key in cache_to_use:
            cache_time, data = cache_to_use[cache_key]
            if current_time - cache_time < CACHE_EXPIRY:
                return data
        
        # 缓存中没有数据或已过期，从交易所获取
        try:
            print(f"从交易所获取 {symbol} 的K线数据")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # 验证数据是否有效
            if not ohlcv or len(ohlcv) < 10:  # 确保至少有10条数据
                print(f"交易对 {symbol} 获取的数据不足，可能是无效交易对")
                return []
            
            # 更新缓存
            cache_to_use[cache_key] = (current_time, ohlcv)
            return ohlcv
            
        except Exception as e:
            error_msg = str(e)
            print(f"获取 {symbol} 的K线数据时出错: {error_msg}")
            
            # 检查错误类型，将特定错误的交易对标记为无效
            if any(x in error_msg for x in [
                "does not have a testnet/sandbox URL", 
                "symbol not found", 
                "not supported",
                "Unknown symbol",
                "Invalid symbol"
            ]):
                mark_symbol_as_invalid(symbol)
            
            return [] 