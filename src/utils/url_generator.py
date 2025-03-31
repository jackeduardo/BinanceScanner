"""
URL生成器模块，用于生成交易所交易URL链接
"""

def generate_trade_url(exchange, symbol, is_short=False):
    """
    根据交易对生成交易URL
    
    Args:
        exchange: 交易所实例
        symbol: 交易对
        is_short: 是否为做空链接
    
    Returns:
        str: 交易URL链接
    """
    try:
        # 清理交易对，移除后缀
        clean_symbol = symbol.split(':')[0] if ':' in symbol else symbol
        
        # 从交易所实例获取交易所ID
        exchange_id = get_exchange_id_from_instance(exchange)
        
        # 根据交易所ID生成URL
        if 'binance' in exchange_id:
            return generate_binance_url(exchange_id, clean_symbol, is_short)
        elif 'okx' in exchange_id:
            return generate_okx_url(clean_symbol, is_short)
        elif 'bybit' in exchange_id:
            return generate_bybit_url(clean_symbol, is_short)
        else:
            # 默认返回币安URL
            return generate_binance_url('binance', clean_symbol, is_short)
    
    except Exception as e:
        print(f"生成交易URL时出错: {str(e)}")
        return f"https://www.google.com/search?q={symbol}+price+chart"

def get_exchange_url(exchange_id, symbol, is_short=False):
    """
    根据交易所ID和交易对生成交易URL（兼容旧接口）
    
    Args:
        exchange_id: 交易所ID或实例
        symbol: 交易对
        is_short: 是否为做空链接
    
    Returns:
        str: 交易URL链接
    """
    try:
        # 处理exchange_id为实例的情况
        if hasattr(exchange_id, 'id'):
            return generate_trade_url(exchange_id, symbol, is_short)
        
        # 清理交易对，移除后缀
        clean_symbol = symbol.split(':')[0] if ':' in symbol else symbol
        
        # 根据交易所ID生成URL
        if 'binance' in str(exchange_id).lower():
            return generate_binance_url(exchange_id, clean_symbol, is_short)
        elif 'okx' in str(exchange_id).lower():
            return generate_okx_url(clean_symbol, is_short)
        elif 'bybit' in str(exchange_id).lower():
            return generate_bybit_url(clean_symbol, is_short)
        else:
            # 默认返回币安URL
            return generate_binance_url('binance', clean_symbol, is_short)
    
    except Exception as e:
        print(f"生成交易URL时出错: {str(e)}")
        return f"https://www.google.com/search?q={symbol}+price+chart"

def get_exchange_id_from_instance(exchange):
    """
    从交易所实例获取交易所ID
    
    Args:
        exchange: 交易所实例
    
    Returns:
        str: 交易所ID
    """
    if exchange is None:
        return 'binance'
    
    # 从实例中获取交易所ID
    exchange_id = type(exchange).__name__.lower()
    
    # 处理特殊情况
    if hasattr(exchange, 'id'):
        exchange_id = exchange.id
    
    return exchange_id

def generate_binance_url(exchange_id, symbol, is_short=False):
    """
    生成币安交易URL
    
    Args:
        exchange_id: 交易所ID
        symbol: 交易对
        is_short: 是否为做空链接
    
    Returns:
        str: 交易URL链接
    """
    # 处理交易对格式
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
    
    # 根据市场类型生成不同的URL
    if 'usdm' in exchange_id.lower() or 'futuresusdt' in exchange_id.lower():
        # U本位期货 - 使用正确的期货URL格式 (无下划线，无type参数)
        symbol_formatted = f"{base}{quote}".upper()
        return f"https://www.binance.com/zh-CN/futures/{symbol_formatted}"
    elif 'coinm' in exchange_id.lower():
        # 币本位期货
        symbol_formatted = f"{base}{quote}".upper()
        return f"https://www.binance.com/zh-CN/delivery/{symbol_formatted}"
    else:
        # 现货 - 使用带下划线的格式
        spot_symbol = f"{base}_{quote}".upper()
        return f"https://www.binance.com/zh-CN/trade/{spot_symbol}?type=spot"

def generate_okx_url(symbol, is_short=False):
    """
    生成OKX交易URL
    
    Args:
        symbol: 交易对
        is_short: 是否为做空链接
    
    Returns:
        str: 交易URL链接
    """
    # 处理交易对格式
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
    
    # OKX的URL格式
    return f"https://www.okx.com/cn/trade-spot/{base.lower()}-{quote.lower()}"

def generate_bybit_url(symbol, is_short=False):
    """
    生成Bybit交易URL
    
    Args:
        symbol: 交易对
        is_short: 是否为做空链接
    
    Returns:
        str: 交易URL链接
    """
    # 处理交易对格式
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
    
    # Bybit的URL格式
    return f"https://www.bybit.com/zh-CN/trade/spot/{base}/{quote}" 