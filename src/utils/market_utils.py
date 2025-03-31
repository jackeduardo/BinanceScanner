"""
市场工具模块，用于处理交易对的获取和过滤
"""

def get_market_symbols(exchange, market_type=None, perpetual_only=False, coin_filter=None):
    """
    获取交易所的交易对列表
    
    Args:
        exchange: 交易所实例
        market_type: 市场类型
        perpetual_only: 是否只获取永续合约
        coin_filter: 币种过滤器
    
    Returns:
        list: 符合条件的交易对列表
    """
    try:
        if exchange is None:
            print("交易所实例为空")
            return []
        
        # 加载市场数据
        markets = exchange.load_markets()
        
        # 获取所有交易对
        symbols = exchange.symbols
        
        # 首先过滤出USDT交易对
        usdt_symbols = []
        for symbol in symbols:
            if '/USDT' in symbol or symbol.endswith('USDT'):
                usdt_symbols.append(symbol)
        
        # 处理特殊市场类型
        if 'binanceusdm' in str(exchange):
            print("检测到币安U本位期货，进行特殊处理")
            # 永续合约过滤
            if perpetual_only:
                perpetual_symbols = []
                for symbol in usdt_symbols:
                    # 排除交割合约 (如 BTC_210625)
                    if '_' not in symbol:
                        perpetual_symbols.append(symbol)
                usdt_symbols = perpetual_symbols
                print(f"已过滤永续合约，数量: {len(usdt_symbols)}")
        
        # 应用币种过滤
        if coin_filter:
            filtered_symbols = []
            
            # 处理多币种过滤
            if isinstance(coin_filter, list):
                coins = coin_filter
            elif isinstance(coin_filter, str):
                # 如果是逗号分隔的字符串
                if ',' in coin_filter:
                    coins = [c.strip().upper() for c in coin_filter.split(',') if c.strip()]
                else:
                    coins = [coin_filter.strip().upper()]
            else:
                coins = []
            
            if coins and coins[0] != '全部':
                for symbol in usdt_symbols:
                    base_coin = None
                    
                    # 处理不同格式的交易对
                    if '/' in symbol:  # BTC/USDT
                        base_coin = symbol.split('/')[0]
                    elif symbol.endswith('USDT'):  # BTCUSDT
                        base_coin = symbol[:-4]
                    
                    if base_coin and any(base_coin.upper() == coin.upper() for coin in coins):
                        filtered_symbols.append(symbol)
                
                usdt_symbols = filtered_symbols
                print(f"已应用币种过滤，筛选出 {len(filtered_symbols)} 个交易对")
        
        return usdt_symbols
    
    except Exception as e:
        print(f"获取市场交易对时出错: {str(e)}")
        return []

def format_symbol(symbol):
    """
    格式化交易对
    
    Args:
        symbol: 原始交易对
    
    Returns:
        str: 格式化后的交易对
    """
    # 处理不同格式的交易对
    if '/' in symbol:  # BTC/USDT
        return symbol
    
    # 尝试添加斜杠
    if symbol.endswith('USDT'):
        base = symbol[:-4]
        quote = 'USDT'
        return f"{base}/{quote}"
    
    return symbol

def split_symbol(symbol):
    """
    拆分交易对为基础币种和计价币种
    
    Args:
        symbol: 交易对
    
    Returns:
        tuple: (基础币种, 计价币种)
    """
    if '/' in symbol:
        parts = symbol.split('/')
        return parts[0], parts[1]
    
    if symbol.endswith('USDT'):
        base = symbol[:-4]
        return base, 'USDT'
    
    # 如果无法拆分，返回原始符号和空字符串
    return symbol, "" 