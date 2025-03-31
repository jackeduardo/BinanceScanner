"""
信号检测模块，提供交易信号检测功能。
"""

import pandas as pd
import numpy as np


def check_long_signal(df, candle_count=10):
    """
    检查是否满足做多信号条件，支持可调整的K线检查数量
    
    条件:
    1. MA7向上穿越MA25（在最近candle_count根K线中）
    2. 穿越后连续3根K线的收盘价都在MA7之上
    3. 上一根K线（不是当前K线）的收盘价在MA7上方
    
    Args:
        df: 包含价格和均线数据的DataFrame
        candle_count: 检查的K线数量，默认为10
        
    Returns:
        dict or None: 包含信号数据的字典，如果没有信号则返回None
    """
    # 确保数据充足
    if len(df) < candle_count or 'ma7' not in df.columns or 'ma25' not in df.columns:
        return None
    
    # 在最近candle_count根K线中寻找MA7向上穿越MA25的点
    recent_df = df.tail(candle_count).reset_index(drop=True)
    
    # 寻找MA7向上穿越MA25的点
    cross_index = None
    for i in range(1, len(recent_df)):
        # 获取前一根K线的均线值
        prev_ma7 = recent_df.iloc[i-1]['ma7']
        prev_ma25 = recent_df.iloc[i-1]['ma25']
        
        # 获取当前K线的均线值
        curr_ma7 = recent_df.iloc[i]['ma7']
        curr_ma25 = recent_df.iloc[i]['ma25']
        
        # 检查是否发生穿越: 之前MA7<=MA25，现在MA7>MA25
        if prev_ma7 <= prev_ma25 and curr_ma7 > curr_ma25:
            cross_index = i
            break
    
    # 如果没有找到交叉点，返回None
    if cross_index is None:
        return None
    
    # 检查交叉点后是否有足够的K线进行判断
    if cross_index + 3 >= len(recent_df):
        # 如果交叉点太靠近最近几根K线，我们需要检查原始df中的后续K线
        # 计算对应在原始df中的索引位置
        orig_cross_index = len(df) - candle_count + cross_index
        
        # 确保有足够的K线用于检查
        if orig_cross_index + 3 >= len(df):
            return None
            
        # 检查交叉后连续3根K线收盘价是否都在MA7上方
        for j in range(orig_cross_index + 1, orig_cross_index + 4):
            if df.iloc[j]['close'] <= df.iloc[j]['ma7']:
                return None
                
        # 检查上一根K线的收盘价是否在MA7上方
        if df.iloc[-2]['close'] <= df.iloc[-2]['ma7']:
            return None
            
        # 所有条件都满足
        print(f"做多信号：MA7({df.iloc[orig_cross_index]['ma7']:.2f})上穿MA25({df.iloc[orig_cross_index]['ma25']:.2f})，"
              f"上一根K线收盘价({df.iloc[-2]['close']:.2f})在MA7({df.iloc[-2]['ma7']:.2f})上方")
              
        # 返回信号数据字典
        return {
            'timestamp': df.iloc[-1]['timestamp'],
            'close': float(df.iloc[-1]['close']),
            'ma7': float(df.iloc[-1]['ma7']),
            'ma25': float(df.iloc[-1]['ma25']),
            'ma99': float(df.iloc[-1]['ma99']),
            'cross_price': float(df.iloc[orig_cross_index]['close']),
            'cross_time': df.iloc[orig_cross_index]['timestamp']
        }
    else:
        # 检查交叉后连续3根K线收盘价是否都在MA7上方
        for j in range(cross_index + 1, cross_index + 4):
            if j >= len(recent_df):
                continue  # 跳过超出范围的索引
            if recent_df.iloc[j]['close'] <= recent_df.iloc[j]['ma7']:
                return None
                
        # 检查上一根K线的收盘价是否在MA7上方
        if recent_df.iloc[-2]['close'] <= recent_df.iloc[-2]['ma7']:
            return None
            
        # 所有条件都满足
        print(f"做多信号：MA7({recent_df.iloc[cross_index]['ma7']:.2f})上穿MA25({recent_df.iloc[cross_index]['ma25']:.2f})，"
              f"上一根K线收盘价({recent_df.iloc[-2]['close']:.2f})在MA7({recent_df.iloc[-2]['ma7']:.2f})上方")
              
        # 返回信号数据字典
        return {
            'timestamp': df.iloc[-1]['timestamp'],
            'close': float(df.iloc[-1]['close']),
            'ma7': float(df.iloc[-1]['ma7']),
            'ma25': float(df.iloc[-1]['ma25']),
            'ma99': float(df.iloc[-1]['ma99']),
            'cross_price': float(recent_df.iloc[cross_index]['close']),
            'cross_time': recent_df.iloc[cross_index]['timestamp']
        }


def check_short_signal(df, candle_count=10):
    """
    检查是否满足做空信号条件，支持可调整的K线检查数量
    
    Args:
        df: 包含价格和均线数据的DataFrame
        candle_count: 检查的K线数量，默认为10
        
    Returns:
        dict or None: 包含信号数据的字典，如果没有信号则返回None
    """
    # 确保数据充足
    if len(df) < candle_count or 'ma7' not in df.columns or 'ma25' not in df.columns:
        return None
    
    # 在最近candle_count根K线中寻找MA7向下穿越MA25的点
    recent_df = df.tail(candle_count).reset_index(drop=True)
    
    # 寻找MA7向下穿越MA25的点
    cross_index = None
    for i in range(1, len(recent_df)):
        # 获取前一根K线的均线值
        prev_ma7 = recent_df.iloc[i-1]['ma7']
        prev_ma25 = recent_df.iloc[i-1]['ma25']
        
        # 获取当前K线的均线值
        curr_ma7 = recent_df.iloc[i]['ma7']
        curr_ma25 = recent_df.iloc[i]['ma25']
        
        # 检查是否发生穿越: 之前MA7>=MA25，现在MA7<MA25
        if prev_ma7 >= prev_ma25 and curr_ma7 < curr_ma25:
            cross_index = i
            break
    
    # 如果没有找到交叉点，返回None
    if cross_index is None:
        return None
    
    # 检查交叉点后是否有足够的K线进行判断
    if cross_index + 3 >= len(recent_df):
        # 如果交叉点太靠近最近几根K线，我们需要检查原始df中的后续K线
        # 计算对应在原始df中的索引位置
        orig_cross_index = len(df) - candle_count + cross_index
        
        # 确保有足够的K线用于检查
        if orig_cross_index + 3 >= len(df):
            return None
            
        # 检查交叉后连续3根K线收盘价是否都在MA7下方
        for j in range(orig_cross_index + 1, orig_cross_index + 4):
            if df.iloc[j]['close'] >= df.iloc[j]['ma7']:
                return None
                
        # 检查上一根K线的收盘价是否在MA7下方
        if df.iloc[-2]['close'] >= df.iloc[-2]['ma7']:
            return None
            
        # 所有条件都满足
        print(f"做空信号：MA7({df.iloc[orig_cross_index]['ma7']:.2f})下穿MA25({df.iloc[orig_cross_index]['ma25']:.2f})，"
              f"上一根K线收盘价({df.iloc[-2]['close']:.2f})在MA7({df.iloc[-2]['ma7']:.2f})下方")
              
        # 返回信号数据字典
        return {
            'timestamp': df.iloc[-1]['timestamp'],
            'close': float(df.iloc[-1]['close']),
            'ma7': float(df.iloc[-1]['ma7']),
            'ma25': float(df.iloc[-1]['ma25']),
            'ma99': float(df.iloc[-1]['ma99']),
            'cross_price': float(df.iloc[orig_cross_index]['close']),
            'cross_time': df.iloc[orig_cross_index]['timestamp']
        }
    else:
        # 检查交叉后连续3根K线收盘价是否都在MA7下方
        for j in range(cross_index + 1, cross_index + 4):
            if j >= len(recent_df):
                continue  # 跳过超出范围的索引
            if recent_df.iloc[j]['close'] >= recent_df.iloc[j]['ma7']:
                return None
                
        # 检查上一根K线的收盘价是否在MA7下方
        if recent_df.iloc[-2]['close'] >= recent_df.iloc[-2]['ma7']:
            return None
            
        # 所有条件都满足
        print(f"做空信号：MA7({recent_df.iloc[cross_index]['ma7']:.2f})下穿MA25({recent_df.iloc[cross_index]['ma25']:.2f})，"
              f"上一根K线收盘价({recent_df.iloc[-2]['close']:.2f})在MA7({recent_df.iloc[-2]['ma7']:.2f})下方")
              
        # 返回信号数据字典
        return {
            'timestamp': df.iloc[-1]['timestamp'],
            'close': float(df.iloc[-1]['close']),
            'ma7': float(df.iloc[-1]['ma7']),
            'ma25': float(df.iloc[-1]['ma25']),
            'ma99': float(df.iloc[-1]['ma99']),
            'cross_price': float(recent_df.iloc[cross_index]['close']),
            'cross_time': recent_df.iloc[cross_index]['timestamp']
        }


def check_additional_condition(df, is_long):
    """
    检查额外的交易条件
    
    Args:
        df: 包含价格和均线数据的DataFrame
        is_long: 是否为做多条件
        
    Returns:
        bool: 是否满足附加条件
    """
    if len(df) < 3:
        return False
    
    last_row = df.iloc[-1]
    
    if is_long:
        # 做多附加条件示例: 
        # MA7上穿MA25的同时，价格也在上升趋势中(近3根K线价格呈上升趋势)
        if last_row['close'] > df.iloc[-2]['close'] > df.iloc[-3]['close']:
            return True
    else:
        # 做空附加条件示例: 
        # MA7下穿MA25的同时，价格也在下降趋势中(近3根K线价格呈下降趋势)
        if last_row['close'] < df.iloc[-2]['close'] < df.iloc[-3]['close']:
            return True
    
    return False 


def check_long_conditions(df):
    """
    检查是否满足做多信号条件（兼容原有代码）
    
    条件:
    1. MA7向上穿越MA25（在最近10根K线中）
    2. 穿越后连续3根K线的收盘价都在MA7之上
    3. 上一根K线（不是当前K线）的收盘价在MA7上方
    
    Args:
        df: 包含价格和均线数据的DataFrame
        
    Returns:
        dict or None: 包含信号数据的字典，如果没有信号则返回None
    """
    return check_long_signal(df, candle_count=10)


def check_short_conditions(df):
    """
    检查是否满足做空信号条件（兼容原有代码）

    条件:
    1. MA7向下穿越MA25（在最近10根K线中）
    2. 穿越后连续3根K线的收盘价都在MA7之下
    3. 上一根K线（不是当前K线）的收盘价在MA7下方

    Args:
        df: 包含价格和均线数据的DataFrame

    Returns:
        dict or None: 包含信号数据的字典，如果没有信号则返回None
    """
    return check_short_signal(df, candle_count=10) 