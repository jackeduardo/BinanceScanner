"""
交易所工具模块，用于处理交易所相关操作
"""

import ccxt
import os
import json
from datetime import datetime
import traceback
from src.utils.ccxt_helper import create_binance_futures_client

def setup_exchange(exchange_id, api_key=None, api_secret=None, **kwargs):
    """
    设置交易所配置

    Args:
        exchange_id: 交易所ID
        api_key: API密钥
        api_secret: API密钥
        **kwargs: 其他参数
    
    Returns:
        dict: 交易所配置
    """
    # 创建交易所配置
    exchange_config = {
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    }
    
    # 添加其他配置参数
    if kwargs:
        exchange_config.update(kwargs)
    
    return exchange_config

def get_exchange_instance(exchange_name, market_type, api_key=None, api_secret=None, **kwargs):
    """
    根据交易所名称和市场类型获取交易所实例
    
    Args:
        exchange_name: 交易所名称
        market_type: 市场类型
        api_key: API密钥
        api_secret: API密钥
        **kwargs: 其他参数
    
    Returns:
        ccxt.Exchange: 交易所实例
    """
    # 根据UI选择映射到ccxt交易所ID
    exchange_id = get_exchange_id(exchange_name, market_type)
    
    if not exchange_id:
        print(f"无法识别的交易所: {exchange_name}, 市场类型: {market_type}")
        return None
    
    try:
        # 检查是否为币安期货
        if exchange_id == 'binanceusdm':
            print("准备创建币安USDT期货交易所实例")
            
            # 处理代理设置
            proxies = None
            if 'proxies' in kwargs:
                proxies = kwargs['proxies']
                print(f"已配置代理: {proxies}")
            
            # 处理超时设置
            timeout = kwargs.get('timeout', 30000)
            
            # 使用我们自己的客户端类，但不立即连接
            return create_binance_futures_client(api_key, api_secret, proxies, timeout)
            
        # 对于其他交易所，检查ccxt是否支持
        if exchange_id not in ccxt.exchanges:
            print(f"交易所 {exchange_id} 不受支持")
            return None
            
        # 使用标准方式创建实例
        exchange_config = setup_exchange(exchange_id, api_key, api_secret, **kwargs)
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class(exchange_config)
        
        # 设置超时
        timeout = kwargs.get('timeout', 30000)
        exchange.timeout = timeout
        
        # 设置代理
        if 'proxies' in kwargs:
            exchange.proxies = kwargs['proxies']
            
        return exchange
    
    except Exception as e:
        print(f"创建交易所实例时出错: {str(e)}")
        traceback.print_exc()
        return None

def get_exchange_id(exchange_name, market_type=None):
    """
    根据交易所名称和市场类型获取交易所ID
    
    Args:
        exchange_name: 交易所名称
        market_type: 市场类型
    
    Returns:
        str: 交易所ID
    """
    # 映射交易所名称到ccxt交易所ID
    exchange_map = {
        '币安(Binance)': {
            '现货(Spot)': 'binance',
            '期货(U本位)': 'binanceusdm',
            '期货(币本位)': 'binancecoinm'
        },
        'OKX': {
            '现货(Spot)': 'okx',
            '期货': 'okx'
        },
        'Bybit': {
            '现货(Spot)': 'bybit',
            '期货': 'bybit'
        }
    }
    
    # 尝试从映射中获取交易所ID
    if exchange_name in exchange_map:
        if market_type and market_type in exchange_map[exchange_name]:
            return exchange_map[exchange_name][market_type]
        elif '现货(Spot)' in exchange_map[exchange_name]:
            # 默认使用现货
            return exchange_map[exchange_name]['现货(Spot)']
    
    # 如果找不到，尝试直接使用小写的交易所名称
    try:
        exchange_name_lower = exchange_name.lower()
        # 移除特殊字符
        exchange_name_clean = ''.join(c for c in exchange_name_lower if c.isalnum())
        
        if exchange_name_clean in ccxt.exchanges:
            return exchange_name_clean
    except:
        pass
    
    # 如果仍然找不到，返回None
    return None

def get_market_symbols(exchange, market_type=None, perpetual_only=False):
    """
    获取市场交易对
    
    Args:
        exchange: 交易所实例
        market_type: 市场类型
        perpetual_only: 是否只获取永续合约
    
    Returns:
        list: 交易对列表
    """
    try:
        if not exchange:
            print("交易所实例为空")
            return []
        
        # 加载市场数据
        markets = exchange.load_markets()
        
        # 获取所有交易对
        symbols = exchange.symbols
        
        # 检查是否为U本位期货
        if 'binanceusdm' in str(exchange):
            print("检测到币安U本位期货，使用特殊筛选逻辑")
            # 如果只需要永续合约
            if perpetual_only:
                perpetual_symbols = []
                for symbol in symbols:
                    # 排除交割合约
                    if '_' not in symbol and any(suffix not in symbol for suffix in ['_CW', '_NW', '_CQ', '_NQ']):
                        perpetual_symbols.append(symbol)
                print(f"已启用永续合约筛选，排除了交割合约")
                return perpetual_symbols
        
        # 仅返回USDT交易对
        usdt_symbols = [s for s in symbols if '/USDT' in s]
        return usdt_symbols
        
    except Exception as e:
        print(f"获取市场交易对时出错: {str(e)}")
        return [] 