"""
配置模块，提供配置加载和管理功能。
"""

import os
import sys
import json
from dotenv import load_dotenv


def load_config():
    """
    加载配置文件
    
    Returns:
        dict: 配置信息
    """
    # 加载.env文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.env')
    
    if os.path.exists(config_path):
        load_dotenv(config_path)
    
    # 获取配置信息
    config = {
        'api_key': os.getenv('API_KEY', ''),
        'api_secret': os.getenv('API_SECRET', ''),
        'exchange': os.getenv('EXCHANGE', 'binance'),
        'scan_interval': int(os.getenv('SCAN_INTERVAL', '15')),
        'use_proxy': os.getenv('USE_PROXY', 'false').lower() == 'true',
        'proxy_url': os.getenv('PROXY_URL', ''),
        'filter_symbols': os.getenv('FILTER_SYMBOLS', ''),
        'exclude_symbols': os.getenv('EXCLUDE_SYMBOLS', '')
    }
    
    return config

def load_config_from_file(file_path=None):
    """
    从JSON文件加载配置
    
    Args:
        file_path: 配置文件路径，如果为None则使用默认路径
        
    Returns:
        dict: 配置信息，如果加载失败则返回空字典
    """
    try:
        # 如果未提供文件路径，使用默认路径
        if file_path is None:
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        else:
            print(f"配置文件不存在: {file_path}")
            return {}
    except Exception as e:
        print(f"加载配置文件出错: {str(e)}")
        return {}

def save_config_to_file(config, file_path=None):
    """
    保存配置到JSON文件
    
    Args:
        config: 配置信息字典
        file_path: 保存的文件路径，如果为None则使用默认路径
        
    Returns:
        bool: 是否保存成功
    """
    try:
        # 如果未提供文件路径，使用默认路径
        if file_path is None:
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置已保存到 {file_path}")
        return True
    except Exception as e:
        print(f"保存配置文件出错: {str(e)}")
        return False

def get_exchange_config(api_key, api_secret, timeout=30000, use_proxy=False, proxy_url=None):
    """
    生成交易所连接配置
    
    Args:
        api_key: API密钥
        api_secret: API密钥
        timeout: 超时设置（毫秒）
        use_proxy: 是否使用代理
        proxy_url: 代理URL
        
    Returns:
        dict: 交易所配置字典
    """
    # 创建交易所配置
    exchange_config = {
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'timeout': timeout,  # 毫秒
    }
    
    # 如果使用代理，添加代理配置
    if use_proxy and proxy_url:
        exchange_config['proxies'] = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    return exchange_config 