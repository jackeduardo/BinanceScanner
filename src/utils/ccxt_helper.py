"""
CCXT辅助模块 - 提供直接的币安API调用功能，避免CCXT库的问题
"""

import time
import hmac
import json
import hashlib
import requests
from urllib.parse import urlencode
import traceback
from typing import Dict, List, Optional, Any, Tuple

class BinanceFuturesClient:
    """币安期货API客户端，不依赖CCXT库的实现"""
    
    def __init__(self, api_key=None, api_secret=None, proxies=None, timeout=30000):
        self.api_key = api_key
        self.api_secret = api_secret
        self.proxies = proxies
        self.timeout = timeout / 1000  # 转换为秒
        
        # API基本URL
        self.base_url = 'https://fapi.binance.com'
        
        # 设置默认的HTTP头
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-MBX-APIKEY': api_key
        }
        
        # 市场数据缓存
        self.markets = {}
        self.symbols = []
        self.last_market_update = 0
        
    def _get_timestamp(self) -> int:
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)
    
    def _generate_signature(self, query_string: str) -> str:
        """生成API请求签名"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _handle_response(self, response: requests.Response) -> Dict:
        """处理API响应"""
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
    
    def _public_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """发送公共API请求（不需要签名）"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == 'GET':
                if params:
                    url = f"{url}?{urlencode(params)}"
                response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            else:
                response = requests.post(url, json=params, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            
            return self._handle_response(response)
        except Exception as e:
            print(f"公共API请求失败: {e}")
            traceback.print_exc()
            raise
    
    def _private_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """发送私有API请求（需要签名）"""
        if params is None:
            params = {}
        
        # 添加时间戳
        params['timestamp'] = self._get_timestamp()
        
        # 生成签名
        query_string = urlencode(params)
        params['signature'] = self._generate_signature(query_string)
        
        # 发送请求
        url = f"{self.base_url}{endpoint}"
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            else:
                response = requests.post(url, data=params, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            
            return self._handle_response(response)
        except Exception as e:
            print(f"私有API请求失败: {e}")
            traceback.print_exc()
            raise
    
    # 公共API方法
    def ping(self) -> Dict:
        """测试连接 - 不需要签名"""
        return self._public_request('GET', '/fapi/v1/ping')
    
    def get_time(self) -> Dict:
        """获取服务器时间"""
        return self._public_request('GET', '/fapi/v1/time')
    
    def get_exchange_info(self) -> Dict:
        """获取交易规则和交易对"""
        return self._public_request('GET', '/fapi/v1/exchangeInfo')
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List:
        """获取K线数据"""
        params = {
            'symbol': symbol.replace('/', ''),
            'interval': interval,
            'limit': limit
        }
        return self._public_request('GET', '/fapi/v1/klines', params)
    
    def load_markets(self, force: bool = False) -> Dict:
        """加载所有市场数据"""
        # 检查是否需要更新缓存（每5分钟更新一次）
        current_time = time.time()
        if not force and self.markets and (current_time - self.last_market_update) < 300:
            return self.markets
        
        # 获取交易所信息
        exchange_info = self.get_exchange_info()
        
        # 处理交易对
        self.markets = {}
        self.symbols = []
        
        for market in exchange_info['symbols']:
            if market['status'] == 'TRADING':
                symbol = f"{market['baseAsset']}/{market['quoteAsset']}"
                self.symbols.append(symbol)
                self.markets[symbol] = {
                    'id': market['symbol'],
                    'symbol': symbol,
                    'base': market['baseAsset'],
                    'quote': market['quoteAsset'],
                    'limits': {
                        'amount': {
                            'min': float(market.get('minQty', 0)),
                            'max': float(market.get('maxQty', 0))
                        },
                        'price': {
                            'min': float(market.get('minPrice', 0)),
                            'max': float(market.get('maxPrice', 0))
                        }
                    },
                    'precision': {
                        'price': market.get('pricePrecision', 0),
                        'amount': market.get('quantityPrecision', 0)
                    },
                    'info': market
                }
        
        # 更新最后更新时间
        self.last_market_update = current_time
        
        return self.markets
    
    # 私有API方法
    def get_account(self) -> Dict:
        """获取账户信息"""
        return self._private_request('GET', '/fapi/v1/account')
    
    def get_positions(self) -> List:
        """获取仓位信息"""
        account = self.get_account()
        return [position for position in account['positions'] if float(position['positionAmt']) != 0]
    
    # OHLCV数据获取
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', since: Optional[int] = None, limit: int = 500) -> List:
        """获取OHLCV数据"""
        # 转换交易所接受的交易对格式
        market_symbol = symbol.replace('/', '')
        
        # 映射时间周期
        timeframe_map = {
            '1m': '1m',
            '3m': '3m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d',
            '3d': '3d',
            '1w': '1w',
            '1M': '1M',
        }
        
        if timeframe not in timeframe_map:
            raise ValueError(f"不支持的时间周期: {timeframe}")
        
        # 构建请求参数
        params = {
            'symbol': market_symbol,
            'interval': timeframe_map[timeframe],
            'limit': limit
        }
        
        if since:
            params['startTime'] = since
        
        # 获取K线数据
        response = self._public_request('GET', '/fapi/v1/klines', params)
        
        # 转换为OHLCV格式 [timestamp, open, high, low, close, volume]
        ohlcv = []
        for candle in response:
            ohlcv.append([
                candle[0],                # 时间戳
                float(candle[1]),         # 开盘价
                float(candle[2]),         # 最高价
                float(candle[3]),         # 最低价
                float(candle[4]),         # 收盘价
                float(candle[5])          # 成交量
            ])
        
        return ohlcv
        
    # 辅助方法，与CCXT库兼容
    def describe(self) -> Dict:
        """返回交易所描述"""
        return {
            'id': 'binanceusdm',
            'name': 'Binance USDT-M Futures',
            'countries': ['JP', 'MT'],
            'version': 'v1',
            'rateLimit': 50,
            'has': {
                'fetchOHLCV': True,
                'fetchBalance': True,
                'fetchPositions': True,
            },
            'timeframes': {
                '1m': '1m',
                '3m': '3m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '2h': '2h',
                '4h': '4h',
                '6h': '6h',
                '8h': '8h',
                '12h': '12h',
                '1d': '1d',
                '3d': '3d',
                '1w': '1w',
                '1M': '1M',
            },
            'urls': {
                'api': {
                    'public': 'https://fapi.binance.com/fapi/v1',
                    'private': 'https://fapi.binance.com/fapi/v1',
                },
                'www': 'https://www.binance.com',
                'doc': [
                    'https://binance-docs.github.io/apidocs/futures/en/',
                ],
            },
            'api': {
                'public': {
                    'get': [
                        'ping',
                        'time',
                        'exchangeInfo',
                        'depth',
                        'trades',
                        'historicalTrades',
                        'aggTrades',
                        'klines',
                        'ticker/24hr',
                        'ticker/price',
                        'ticker/bookTicker',
                    ],
                },
                'private': {
                    'get': [
                        'account',
                        'balance',
                        'positionRisk',
                        'userTrades',
                    ],
                },
            },
        }

# 方便的工厂方法
def create_binance_futures_client(api_key=None, api_secret=None, proxies=None, timeout=30000):
    """
    创建币安期货客户端实例
    
    Args:
        api_key: API密钥
        api_secret: API密钥
        proxies: 代理设置
        timeout: 超时设置（毫秒）
    
    Returns:
        BinanceFuturesClient: 币安期货客户端实例
    """
    # 创建客户端实例
    client = BinanceFuturesClient(api_key, api_secret, proxies, timeout)
    
    # 返回客户端实例，但不立即连接
    return client 