"""
数据准备模块
包含所有数据准备和预处理函数
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def prepare_general_cross_section_data(df: pd.DataFrame, expiration_dates: list, 
                                       dimension_param: str, option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备通用截面分析数据（支持Greeks和非Greeks维度）
    
    :param df: 原始数据
    :param expiration_dates: 到期日列表
    :param dimension_param: 维度参数名称（可以是Greeks或价格、波动率等）
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame
    """
    if df.empty:
        return pd.DataFrame()
    
    # 确保expiration_dates是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    
    # 筛选指定到期日
    if 'expiration_date' in df.columns:
        df['expiration_date'] = pd.to_datetime(df['expiration_date'])
        exp_dates_set = {pd.to_datetime(ed).date() if isinstance(ed, pd.Timestamp) else pd.to_datetime(ed).date() for ed in expiration_dates}
        filtered_df = df[df['expiration_date'].dt.date.isin(exp_dates_set)].copy()
    else:
        return pd.DataFrame()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 检查维度参数是否存在
    if dimension_param not in filtered_df.columns:
        return pd.DataFrame()
    
    # 选择需要的列
    required_cols = ['expiration_date', 'strike', 'option_type', dimension_param]
    available_cols = [col for col in required_cols if col in filtered_df.columns]
    
    if len(available_cols) < 3:
        return pd.DataFrame()
    
    result_df = filtered_df[available_cols].copy()
    
    # 移除缺失值（只删除dimension_param、strike、expiration_date为NaN的行）
    # 对于volume等字段，允许NaN值存在（不强制要求）
    required_fields = [dimension_param, 'strike', 'expiration_date']
    result_df = result_df.dropna(subset=[f for f in required_fields if f in result_df.columns])
    
    # 按到期日和行权价排序
    result_df = result_df.sort_values(['expiration_date', 'strike'])
    
    return result_df


def prepare_cross_section_data_multi_greeks(df: pd.DataFrame, expiration_dates: list, 
                                            greeks_params: list, option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备截面分析数据（支持多个到期日和多个Greeks参数）
    
    :param df: 原始数据
    :param expiration_dates: 到期日列表
    :param greeks_params: Greeks参数列表
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame（包含所有Greeks列）
    """
    if df.empty:
        return pd.DataFrame()
    
    # 确保参数是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    if not isinstance(greeks_params, list):
        greeks_params = [greeks_params]
    
    # 筛选指定到期日
    if 'expiration_date' in df.columns:
        df['expiration_date'] = pd.to_datetime(df['expiration_date'])
        exp_dates_set = {pd.to_datetime(ed).date() if isinstance(ed, pd.Timestamp) else pd.to_datetime(ed).date() for ed in expiration_dates}
        filtered_df = df[df['expiration_date'].dt.date.isin(exp_dates_set)].copy()
    else:
        return pd.DataFrame()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 选择需要的列（包含所有Greeks参数）
    required_cols = ['expiration_date', 'strike', 'option_type'] + greeks_params
    available_cols = [col for col in required_cols if col in filtered_df.columns]
    
    # 检查是否所有维度参数都存在
    missing_params = [gp for gp in greeks_params if gp not in filtered_df.columns]
    if missing_params:
        logger.warning(f"数据中缺少以下维度参数: {missing_params}")
        return pd.DataFrame()
    
    result_df = filtered_df[available_cols].copy()
    
    # 移除缺失值
    # 对于volume等字段，允许部分NaN（只删除所有维度参数都为NaN的行）
    required_fields = ['strike', 'expiration_date']
    # 检查每个维度参数，如果某个参数全为NaN，则从检查列表中移除
    valid_params = []
    for param in greeks_params:
        if param in result_df.columns and not result_df[param].isna().all():
            valid_params.append(param)
    
    if valid_params:
        # 只删除所有有效参数都为NaN的行
        result_df = result_df.dropna(subset=required_fields + valid_params, how='all')
    else:
        # 如果所有参数都无效，至少保留strike和expiration_date不为NaN的行
        result_df = result_df.dropna(subset=required_fields)
    
    # 按到期日和行权价排序
    result_df = result_df.sort_values(['expiration_date', 'strike'])
    
    return result_df


def prepare_cross_section_data(df: pd.DataFrame, expiration_dates: list, 
                               greeks_param: str, option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备截面分析数据（支持多个到期日）
    
    :param df: 原始数据
    :param expiration_dates: 到期日列表（单个或多个）
    :param greeks_param: Greeks参数名称
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame（包含expiration_date列用于区分不同到期日）
    """
    if df.empty:
        return pd.DataFrame()
    
    # 确保expiration_dates是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    
    # 筛选指定到期日
    if 'expiration_date' in df.columns:
        df['expiration_date'] = pd.to_datetime(df['expiration_date'])
        # 筛选多个到期日
        exp_dates_set = {pd.to_datetime(ed).date() if isinstance(ed, pd.Timestamp) else pd.to_datetime(ed).date() for ed in expiration_dates}
        filtered_df = df[df['expiration_date'].dt.date.isin(exp_dates_set)].copy()
    else:
        return pd.DataFrame()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 检查Greeks参数是否存在
    if greeks_param not in filtered_df.columns:
        return pd.DataFrame()
    
    # 选择需要的列（包含expiration_date用于区分）
    required_cols = ['expiration_date', 'strike', 'option_type', greeks_param]
    available_cols = [col for col in required_cols if col in filtered_df.columns]
    
    if len(available_cols) < 3:
        return pd.DataFrame()
    
    result_df = filtered_df[available_cols].copy()
    
    # 移除缺失值
    result_df = result_df.dropna(subset=[greeks_param, 'strike', 'expiration_date'])
    
    # 按到期日和行权价排序
    result_df = result_df.sort_values(['expiration_date', 'strike'])
    
    return result_df


def prepare_time_series_data_multi_greeks(df: pd.DataFrame, strike_prices: list, 
                                          greeks_params: list, option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备时序分析数据（支持多个维度参数，包括Greeks和非Greeks）
    
    :param df: 原始数据
    :param strike_prices: 行权价列表
    :param greeks_params: 维度参数列表（可以是Greeks或IV、价格等）
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame（包含所有维度列）
    """
    if df.empty:
        return pd.DataFrame()
    
    # 确保参数是列表
    if not isinstance(greeks_params, list):
        greeks_params = [greeks_params]
    
    # 筛选指定行权价
    if 'strike' in df.columns:
        filtered_df = df[df['strike'].isin(strike_prices)].copy()
    else:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 选择需要的列（包含所有Greeks参数）
    required_cols = ['expiration_date', 'strike', 'option_type'] + greeks_params
    available_cols = [col for col in required_cols if col in filtered_df.columns]
    
    # 检查是否所有维度参数都存在
    missing_params = [gp for gp in greeks_params if gp not in filtered_df.columns]
    if missing_params:
        logger.warning(f"数据中缺少以下维度参数: {missing_params}")
        return pd.DataFrame()
    
    result_df = filtered_df[available_cols].copy()
    
    # 确保到期日是datetime类型
    if 'expiration_date' in result_df.columns:
        result_df['expiration_date'] = pd.to_datetime(result_df['expiration_date'])
    
    # 移除缺失值
    # 对于volume等字段，允许部分NaN（只删除所有维度参数都为NaN的行）
    required_fields = ['expiration_date', 'strike']
    # 检查每个维度参数，如果某个参数全为NaN，则从检查列表中移除
    valid_params = []
    for param in greeks_params:
        if param in result_df.columns and not result_df[param].isna().all():
            valid_params.append(param)
    
    if valid_params:
        # 只删除所有有效参数都为NaN的行
        result_df = result_df.dropna(subset=required_fields + valid_params, how='all')
    else:
        # 如果所有参数都无效，至少保留expiration_date和strike不为NaN的行
        result_df = result_df.dropna(subset=required_fields)
    
    # 按到期日排序
    result_df = result_df.sort_values('expiration_date')
    
    return result_df


def prepare_time_series_data(df: pd.DataFrame, strike_prices: list, 
                             greeks_param: str, option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备时序分析数据（支持任意维度参数）
    
    :param df: 原始数据
    :param strike_prices: 行权价列表
    :param greeks_param: 维度参数名称（可以是Greeks或IV、价格等）
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame
    """
    if df.empty:
        return pd.DataFrame()
    
    # 筛选指定行权价
    if 'strike' in df.columns:
        filtered_df = df[df['strike'].isin(strike_prices)].copy()
    else:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 检查Greeks参数是否存在
    if greeks_param not in filtered_df.columns:
        return pd.DataFrame()
    
    # 选择需要的列
    required_cols = ['expiration_date', 'strike', 'option_type', greeks_param]
    available_cols = [col for col in required_cols if col in filtered_df.columns]
    
    if len(available_cols) < 3:
        return pd.DataFrame()
    
    result_df = filtered_df[available_cols].copy()
    
    # 确保到期日是datetime类型
    if 'expiration_date' in result_df.columns:
        result_df['expiration_date'] = pd.to_datetime(result_df['expiration_date'])
    
    # 移除缺失值
    # 只删除expiration_date和strike为NaN的行（这是必需的）
    # 对于Greeks值，即使为NaN也保留数据点，让图表显示数据缺失情况
    required_fields = ['expiration_date', 'strike']
    result_df = result_df.dropna(subset=required_fields)
    
    # 注意：不删除Greeks值为NaN的行，这样可以：
    # 1. 保留数据点的存在（即使值为NaN）
    # 2. 在图表中可以看到哪些到期日有数据但Greeks值缺失
    # 3. 如果某个到期日+行权价组合完全没有数据，那才是真正的问题
    
    # 按到期日排序
    result_df = result_df.sort_values('expiration_date')
    
    return result_df


def prepare_breakeven_data(df: pd.DataFrame, expiration_dates: list, 
                           option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备盈亏平衡分析数据
    
    :param df: 原始数据
    :param expiration_dates: 到期日列表
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame，包含盈亏平衡点列
    """
    if df.empty:
        return pd.DataFrame()
    
    # 确保expiration_dates是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    
    # 筛选指定到期日
    if 'expiration_date' in df.columns:
        df['expiration_date'] = pd.to_datetime(df['expiration_date'])
        exp_dates_set = {pd.to_datetime(ed).date() if isinstance(ed, pd.Timestamp) else pd.to_datetime(ed).date() for ed in expiration_dates}
        filtered_df = df[df['expiration_date'].dt.date.isin(exp_dates_set)].copy()
    else:
        return pd.DataFrame()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 检查必需字段
    required_cols = ['expiration_date', 'strike', 'option_type', 'mark_price']
    if not all(col in filtered_df.columns for col in required_cols):
        return pd.DataFrame()
    
    # 选择需要的列（包括volume和open_interest如果存在）
    available_cols = required_cols.copy()
    if 'volume' in filtered_df.columns:
        available_cols.append('volume')
    if 'open_interest' in filtered_df.columns:
        available_cols.append('open_interest')
    
    result_df = filtered_df[available_cols].copy()
    
    # 移除缺失值
    result_df = result_df.dropna(subset=['strike', 'mark_price', 'expiration_date'])
    
    # 计算盈亏平衡点
    # Call: 盈亏平衡点 = Strike + Premium
    # Put: 盈亏平衡点 = Strike - Premium
    result_df['breakeven_price'] = result_df.apply(
        lambda row: row['strike'] + row['mark_price'] if row['option_type'] == 'C' 
        else row['strike'] - row['mark_price'], 
        axis=1
    )
    
    # 按到期日和行权价排序
    result_df = result_df.sort_values(['expiration_date', 'strike'])
    
    return result_df


def prepare_delta_skew_data(df: pd.DataFrame, expiration_dates: list,
                            option_type_filter: str = "全部") -> pd.DataFrame:
    """
    准备Delta偏度分析数据（按Delta绝对值排序和插值）
    
    :param df: 原始数据
    :param expiration_dates: 到期日列表
    :param option_type_filter: 期权类型筛选
    :return: 准备好的DataFrame，包含Delta绝对值和IV等字段
    """
    import numpy as np
    from scipy.interpolate import interp1d
    
    if df.empty:
        return pd.DataFrame()
    
    # 确保expiration_dates是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    
    # 筛选指定到期日
    if 'expiration_date' in df.columns:
        df['expiration_date'] = pd.to_datetime(df['expiration_date'])
        exp_dates_set = {pd.to_datetime(ed).date() if isinstance(ed, pd.Timestamp) else pd.to_datetime(ed).date() for ed in expiration_dates}
        filtered_df = df[df['expiration_date'].dt.date.isin(exp_dates_set)].copy()
    else:
        return pd.DataFrame()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # 筛选期权类型
    if option_type_filter != "全部" and 'option_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['option_type'] == option_type_filter]
    
    # 检查必需字段
    required_cols = ['expiration_date', 'strike', 'option_type', 'delta', 'mark_iv']
    if not all(col in filtered_df.columns for col in required_cols):
        return pd.DataFrame()
    
    result_df = filtered_df[required_cols].copy()
    
    # 移除缺失值
    result_df = result_df.dropna(subset=['delta', 'mark_iv', 'expiration_date'])
    
    # 计算Delta绝对值
    result_df['delta_abs'] = result_df['delta'].abs()
    
    # 按到期日、期权类型和Delta绝对值排序
    result_df = result_df.sort_values(['expiration_date', 'option_type', 'delta_abs'])
    
    # 对每个到期日和期权类型组合进行插值
    interpolated_data = []
    standard_deltas = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    
    unique_exp_dates = sorted(result_df['expiration_date'].dt.date.unique())
    
    for exp_date in unique_exp_dates:
        exp_df = result_df[result_df['expiration_date'].dt.date == exp_date].copy()
        
        for opt_type in ['C', 'P']:
            type_df = exp_df[exp_df['option_type'] == opt_type].copy()
            
            if type_df.empty or len(type_df) < 2:
                continue
            
            # 获取Delta和IV数据
            delta_values = type_df['delta_abs'].values
            iv_values = type_df['mark_iv'].values
            
            # 去除重复的Delta值（取平均值）
            unique_deltas = []
            unique_ivs = []
            for delta_val in sorted(set(delta_values)):
                mask = delta_values == delta_val
                unique_deltas.append(delta_val)
                unique_ivs.append(np.mean(iv_values[mask]))
            
            if len(unique_deltas) < 2:
                continue
            
            # 创建插值函数
            try:
                interp_func = interp1d(unique_deltas, unique_ivs, kind='linear', 
                                     bounds_error=False, fill_value='extrapolate')
                
                # 对标准Delta点进行插值
                for std_delta in standard_deltas:
                    if std_delta >= min(unique_deltas) and std_delta <= max(unique_deltas):
                        interp_iv = float(interp_func(std_delta))
                        interpolated_data.append({
                            'expiration_date': pd.Timestamp(exp_date),
                            'option_type': opt_type,
                            'delta_abs': std_delta,
                            'mark_iv': interp_iv,
                            'strike': None  # 插值后没有对应的行权价
                        })
            except Exception as e:
                logger.warning(f"插值失败 (到期日: {exp_date}, 类型: {opt_type}): {e}")
                continue
    
    if interpolated_data:
        interpolated_df = pd.DataFrame(interpolated_data)
        return interpolated_df
    else:
        # 如果没有插值数据，返回原始数据（按Delta绝对值排序）
        return result_df
