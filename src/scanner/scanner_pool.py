"""
扫描线程池模块，用于管理多个扫描线程。
"""

import os
import time
import queue
import threading
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QCoreApplication
from src.scanner.scanner_thread import ScannerThread, OHLCV_CACHE, is_symbol_invalid

# 全局锁，用于线程安全操作
progress_lock = threading.Lock()

class ScannerPool(QObject):
    """扫描线程池类，管理多个扫描线程"""
    
    # 定义信号
    progress_updated = pyqtSignal(int, int)  # 进度更新信号 (已处理数量, 总数量)
    signal_found = pyqtSignal(str, dict)  # 发现信号 (交易对, 信号数据)
    scan_completed = pyqtSignal()  # 扫描完成信号
    scan_error = pyqtSignal(str)  # 错误信号 (错误信息)
    
    def __init__(self, exchange, symbols, is_long=True, timeframe='15m', window=None, threads=None):
        """
        初始化扫描线程池
        
        Args:
            exchange: 交易所实例
            symbols: 要扫描的交易对列表
            is_long: 是否扫描做多信号，False为扫描做空信号
            timeframe: K线时间周期，默认为15分钟
            window: 主窗口实例，用于在UI上显示进度
            threads: 线程池中的线程数量，如果为None，则自动设置为CPU核心数x2
        """
        super().__init__()
        self.exchange = exchange
        self.symbols = symbols
        self.is_long = is_long
        self.timeframe = timeframe
        self.window = window
        
        # 自动设置线程数为CPU核心数的2倍或用户指定的数量
        import multiprocessing
        self.threads = threads if threads is not None else min(multiprocessing.cpu_count() * 2, 16)
        print(f"使用 {self.threads} 个线程进行扫描")
        
        self.running = False
        self.should_stop = False
        self.total_symbols = len(symbols)
        self.processed_symbols = 0
        self.worker_threads = []
        self.batch_size = 5  # 每批处理的交易对数量
    
    def run(self):
        """运行扫描线程池"""
        if self.running:
            print("扫描线程池已在运行")
            return
        
        self.running = True
        self.should_stop = False
        self.processed_symbols = 0
        
        # 预处理：过滤掉无效的交易对
        valid_symbols = [s for s in self.symbols if not is_symbol_invalid(s)]
        self.total_symbols = len(valid_symbols)
        print(f"过滤后有效交易对数量: {self.total_symbols}")
        
        # 如果没有有效交易对，直接结束
        if self.total_symbols == 0:
            print("没有有效的交易对可扫描")
            self.scan_completed.emit()
            self.running = False
            return
        
        # 创建任务队列
        self.queue = queue.Queue()
        
        # 批量处理：将交易对分成小批次
        # 每批处理多个交易对可以减少线程创建/销毁的开销
        batches = []
        for i in range(0, len(valid_symbols), self.batch_size):
            batch = valid_symbols[i:i+self.batch_size]
            batches.append(batch)
        
        # 将批次添加到队列
        for batch in batches:
            self.queue.put(batch)
        
        print(f"将 {self.total_symbols} 个交易对分成 {len(batches)} 批处理")
        
        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix="Scanner")
        
        # 预热缓存 - 提前获取一些热门交易对的数据
        if len(valid_symbols) > 100:
            # 选取前20个交易对预热缓存
            popular_symbols = valid_symbols[:20]
            print(f"正在预热缓存，加载 {len(popular_symbols)} 个热门交易对...")
            
            def preheat_cache(symbol):
                from src.scanner.scanner_thread import get_ohlcv_with_cache
                return get_ohlcv_with_cache(self.exchange, symbol, self.timeframe, limit=500)
            
            # 并行预热缓存
            self.executor.map(preheat_cache, popular_symbols)
            print("缓存预热完成")
        
        # 创建并启动工作线程
        self.worker_threads = []
        for i in range(self.threads):
            thread = threading.Thread(target=self.worker, name=f"Scanner-{i+1}")
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)
        
        # 创建监控线程，用于检查是否所有工作都已完成
        self.monitor_thread = threading.Thread(target=self.monitor, name="Monitor")
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def worker(self):
        """工作线程函数，从队列获取交易对批次并进行扫描"""
        thread_name = threading.current_thread().name
        
        while not self.should_stop:
            try:
                # 尝试从队列中获取交易对批次，如果队列为空则退出循环
                try:
                    batch = self.queue.get(block=False)
                except queue.Empty:
                    break
                
                # 检查是否应该停止
                if self.should_stop:
                    self.queue.task_done()
                    break
                
                # 处理批次
                try:
                    start_time = time.time()
                    
                    # 创建扫描线程来处理整个批次
                    scanner = ScannerThread(
                        self.exchange,
                        batch,
                        self.is_long,
                        self.timeframe
                    )
                    
                    # 连接信号
                    scanner.signal_found.connect(self._on_signal_found)
                    scanner.short_signal_found.connect(self._on_signal_found)
                    scanner.error_occurred.connect(self._on_error)
                    
                    # 执行扫描
                    scanner.run()
                    
                    # 更新进度
                    with progress_lock:
                        self.processed_symbols += len(batch)
                        self.progress_updated.emit(self.processed_symbols, self.total_symbols)
                    
                    end_time = time.time()
                    print(f"{thread_name} 处理了 {len(batch)} 个交易对，耗时 {end_time - start_time:.2f} 秒")
                    
                except Exception as e:
                    print(f"{thread_name} 处理批次时出错: {str(e)}")
                    traceback.print_exc()
                    
                    # 尽管出错，仍更新处理数量
                    with progress_lock:
                        self.processed_symbols += len(batch)
                        self.progress_updated.emit(self.processed_symbols, self.total_symbols)
                
                # 标记任务完成
                self.queue.task_done()
                
                # 检查线程是否应该停止
                if self.should_stop:
                    break
                
            except Exception as e:
                print(f"{thread_name} 运行时出错: {str(e)}")
                traceback.print_exc()
                
                # 如果出现意外错误，休息一下再继续
                time.sleep(0.5)
    
    def monitor(self):
        """监控线程函数，检查是否所有工作都已完成"""
        try:
            # 等待队列处理完毕
            self.queue.join()
            
            # 如果没有被要求停止，则发送完成信号
            if not self.should_stop:
                print(f"扫描完成，共处理 {self.processed_symbols} 个交易对")
                
                # 缓存统计
                cache_size = len(OHLCV_CACHE)
                print(f"缓存统计: 共缓存了 {cache_size} 条K线数据")
                
                self.scan_completed.emit()
            
            # 关闭线程池
            self.executor.shutdown(wait=False)
            
            # 标记线程池不再运行
            self.running = False
            
        except Exception as e:
            print(f"监控线程出错: {str(e)}")
            traceback.print_exc()
            self.scan_error.emit(f"监控线程出错: {str(e)}")
    
    def stop(self):
        """停止扫描线程池"""
        if not self.running:
            return
        
        self.should_stop = True
        print("正在停止扫描线程池...")
        
        # 等待所有工作线程退出
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(0.5)
        
        # 清空队列
        try:
            while not self.queue.empty():
                self.queue.get(block=False)
                self.queue.task_done()
        except:
            pass
        
        # 关闭线程池
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        
        self.running = False
        print("扫描线程池已停止")
    
    def _on_signal_found(self, symbol, data):
        """信号发现处理函数"""
        self.signal_found.emit(symbol, data)
    
    def _on_error(self, error_msg):
        """错误处理函数"""
        self.scan_error.emit(error_msg) 