"""
交易所处理模块，提供连接交易所和获取市场信息的功能。
"""

import ccxt
import time
import traceback
from src.utils.config import load_config


def connect_exchange(exchange_id, api_key=None, api_secret=None, **kwargs):
    """
    连接到交易所
    
    Args:
        exchange_id: 交易所ID
        api_key: API密钥
        api_secret: API密钥密码
        **kwargs: 额外参数，如timeout、proxies等
        
    Returns:
        Exchange: 交易所实例
    """
    try:
        # 加载配置，获取代理设置
        config = load_config()
        use_proxy = config.get('use_proxy', False)
        proxy_url = config.get('proxy_url', '')
        
        # 设置交易所参数
        params = {
            'enableRateLimit': True,  # 启用请求频率限制
            'timeout': 30000,  # 默认超时时间30秒
            'options': {
                'adjustForTimeDifference': True  # 启用时间同步调整
            }
        }
        
        # 合并传入的额外参数
        for key, value in kwargs.items():
            if key == 'proxies':
                params['proxies'] = value
            elif key == 'timeout':
                params['timeout'] = value
        
        # 如果提供了API密钥，添加到参数中
        if api_key and api_secret:
            params['apiKey'] = api_key
            params['secret'] = api_secret
        
        # 如果使用代理但没有通过kwargs传入，使用配置文件中的代理
        if 'proxies' not in params and use_proxy and proxy_url:
            print(f"使用配置文件中的代理: {proxy_url}")
            params['proxies'] = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # 创建交易所实例
        if exchange_id in ccxt.exchanges:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class(params)
            
            # 加载市场
            print("正在加载市场数据...")
            exchange.load_markets()
            print("市场数据加载成功")
            
            return exchange
        else:
            raise ValueError(f"不支持的交易所: {exchange_id}")
        
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"连接交易所时出错: {str(e)}")


def get_exchange_id(exchange_name):
    """
    根据交易所名称获取交易所ID
    
    Args:
        exchange_name: 交易所名称
        
    Returns:
        str: 交易所ID
    """
    exchange_map = {
        "币安(Binance)": "binance",
        "币安现货": "binance",
        "币安期货": "binanceusdm",
        "火币(Huobi)": "huobi",
        "OKX": "okx",
    }
    
    return exchange_map.get(exchange_name, exchange_name.lower())


def get_market_symbols(exchange, include_symbols=None, exclude_symbols=None, coin_filter=None, perpetual_only=False):
    """
    获取USDT交易对列表，可选择按币种筛选
    
    Args:
        exchange: 交易所实例
        include_symbols: 已废弃参数，不再使用
        exclude_symbols: 已废弃参数，不再使用
        coin_filter: 币种筛选字符串，多个币种用逗号分隔，如'BTC,ETH'；None或'全部'则不筛选
        perpetual_only: 是否只返回永续合约，默认为False，设为True时只返回不带日期后缀的永续合约
        
    Returns:
        list: USDT交易对列表
    """
    try:
        # 获取所有交易对
        markets = exchange.load_markets()
        print(f"总交易对数量: {len(markets)}")
        
        # 尝试打印一些交易对示例，帮助调试
        sample_keys = list(markets.keys())[:5]
        print(f"交易对示例: {sample_keys}")
        
        # 根据交易所类型调整筛选逻辑
        usdt_symbols = []
        if hasattr(exchange, 'id') and exchange.id == 'binanceusdm':
            # 币安U本位期货交易对通常以USDT结尾，没有分隔符
            print("检测到币安U本位期货，使用特殊筛选逻辑")
            for symbol in markets.keys():
                market = markets[symbol]
                
                # 如果只要永续合约，跳过带有日期后缀的交割合约
                if perpetual_only and "-" in symbol:
                    continue
                    
                # 尝试检查合约类型
                if 'quote' in market and market['quote'] == 'USDT':
                    usdt_symbols.append(symbol)
                elif 'settle' in market and market['settle'] == 'USDT':
                    usdt_symbols.append(symbol)
                elif symbol.endswith('USDT'):
                    usdt_symbols.append(symbol)
        else:
            # 标准现货市场格式 BASE/QUOTE
            usdt_symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT')]
        
        # 应用币种筛选
        if coin_filter and coin_filter.strip() and coin_filter != '全部':
            filtered_symbols = []
            # 处理多个币种 - 支持逗号分隔的多个币种
            filter_coins = [coin.strip().upper() for coin in coin_filter.split(',') if coin.strip()]
            
            if filter_coins:
                for symbol in usdt_symbols:
                    # 处理不同格式的交易对
                    if '/' in symbol:  # 标准格式 BTC/USDT
                        base_coin = symbol.split('/')[0]
                        if base_coin in filter_coins:
                            filtered_symbols.append(symbol)
                    elif symbol.endswith('USDT'):  # 期货格式 BTCUSDT
                        base_coin = symbol.replace('USDT', '')
                        if base_coin in filter_coins:
                            filtered_symbols.append(symbol)
                
                print(f"筛选币种 {','.join(filter_coins)}，找到 {len(filtered_symbols)} 个匹配交易对")
                usdt_symbols = filtered_symbols
        
        # 记录永续合约筛选结果
        if perpetual_only:
            print(f"已启用永续合约筛选，排除了交割合约")
            
        print(f"USDT交易对数量: {len(usdt_symbols)}")
        if len(usdt_symbols) > 0:
            print(f"USDT交易对示例: {usdt_symbols[:5]}")
        
        return usdt_symbols
        
    except Exception as e:
        traceback.print_exc()
        print(f"获取交易对列表时出错: {str(e)}")
        raise Exception(f"获取交易对列表时出错: {str(e)}")


def get_exchange_config(exchange_id):
    """
    获取交易所配置
    
    Args:
        exchange_id: 交易所ID
        
    Returns:
        dict: 交易所配置
    """
    try:
        # 返回交易所特定配置
        config = {
            'binance': {
                'timeframes': ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'],
                'limits': {
                    'ohlcv': 1000,  # 最大K线获取数量
                }
            },
            'binanceusdm': {
                'timeframes': ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'],
                'limits': {
                    'ohlcv': 1000,
                }
            },
            'huobi': {
                'timeframes': ['1m', '5m', '15m', '30m', '60m', '4h', '1d', '1w'],
                'limits': {
                    'ohlcv': 2000,
                }
            },
            'okx': {
                'timeframes': ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'],
                'limits': {
                    'ohlcv': 300,
                }
            }
        }
        
        return config.get(exchange_id, {})
        
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"获取交易所配置时出错: {str(e)}") 