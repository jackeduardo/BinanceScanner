"""
扫描线程池模块，用于管理多个扫描线程。
"""

import os
import time
import queue
import threading
import traceback
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QCoreApplication
from src.scanner.scanner_thread import ScannerThread

class ScannerPool(QObject):
    """扫描线程池类，管理多个扫描线程"""
    
    # 定义信号
    progress_updated = pyqtSignal(int, int)  # 进度更新信号 (已处理数量, 总数量)
    signal_found = pyqtSignal(str, dict)  # 发现信号 (交易对, 信号数据)
    scan_completed = pyqtSignal()  # 扫描完成信号
    scan_error = pyqtSignal(str)  # 错误信号 (错误信息)
    
    def __init__(self, exchange, symbols, is_long=True, timeframe='15m', window=None, threads=5):
        """
        初始化扫描线程池
        
        Args:
            exchange: 交易所实例
            symbols: 要扫描的交易对列表
            is_long: 是否扫描做多信号，False为扫描做空信号
            timeframe: K线时间周期，默认为15分钟
            window: 主窗口实例，用于在UI上显示进度
            threads: 线程池中的线程数量，默认为5
        """
        super().__init__()
        self.exchange = exchange
        self.symbols = symbols
        self.is_long = is_long
        self.timeframe = timeframe
        self.window = window
        self.threads = threads
        self.running = False
        self.should_stop = False
        self.total_symbols = len(symbols)
        self.processed_symbols = 0
        self.worker_threads = []
    
    def run(self):
        """运行扫描线程池"""
        if self.running:
            print("扫描线程池已在运行")
            return
        
        self.running = True
        self.should_stop = False
        
        # 创建任务队列
        self.queue = queue.Queue()
        
        # 将交易对添加到队列
        for symbol in self.symbols:
            self.queue.put(symbol)
        
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
        """工作线程函数，从队列获取交易对并进行扫描"""
        thread_name = threading.current_thread().name
        
        while not self.should_stop:
            try:
                # 尝试从队列中获取交易对，如果队列为空则退出循环
                try:
                    symbol = self.queue.get(block=False)
                except queue.Empty:
                    break
                
                # 检查是否应该停止
                if self.should_stop:
                    self.queue.task_done()
                    break
                
                # 处理交易对
                try:
                    # 创建扫描线程
                    scanner = ScannerThread(
                        self.exchange,
                        [symbol],
                        self.is_long,
                        self.timeframe
                    )
                    
                    # 连接信号
                    scanner.signal_found.connect(self._on_signal_found)
                    scanner.short_signal_found.connect(self._on_signal_found)
                    scanner.error_occurred.connect(self._on_error)
                    
                    # 执行扫描
                    scanner.run()
                    
                    # 处理完成，更新进度
                    self.processed_symbols += 1
                    self.progress_updated.emit(self.processed_symbols, self.total_symbols)
                    
                except Exception as e:
                    print(f"{thread_name}处理{symbol}时出错: {str(e)}")
                    traceback.print_exc()
                
                # 标记任务完成
                self.queue.task_done()
                
                # 检查线程是否应该停止
                if self.should_stop:
                    break
                
            except Exception as e:
                print(f"{thread_name}运行时出错: {str(e)}")
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
                self.scan_completed.emit()
            
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
        
        self.running = False
    
    def _on_signal_found(self, symbol, data):
        """信号发现处理函数"""
        self.signal_found.emit(symbol, data)
    
    def _on_error(self, error_msg):
        """错误处理函数"""
        self.scan_error.emit(error_msg) 