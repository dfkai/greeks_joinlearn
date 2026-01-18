"""
工具函数模块
包含通用的工具函数、数据库加载、数据缓存和页面样式配置
"""

import streamlit as st
import pandas as pd
import logging
from pathlib import Path
from src.core import OptionsDatabase

logger = logging.getLogger(__name__)


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    应用筛选条件
    
    :param df: 原始数据
    :param filters: 筛选条件字典
    :return: 筛选后的DataFrame
    """
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # 到期日筛选
    if filters.get('expiration_date'):
        exp_date = filters['expiration_date']
        if 'expiration_date' in filtered_df.columns:
            filtered_df['expiration_date'] = pd.to_datetime(filtered_df['expiration_date'])
            filtered_df = filtered_df[filtered_df['expiration_date'].dt.date == exp_date.date()]
    
    # 行权价范围筛选
    if filters.get('min_strike') is not None:
        if 'strike' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['strike'] >= filters['min_strike']]
    
    if filters.get('max_strike') is not None:
        if 'strike' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['strike'] <= filters['max_strike']]
    
    # 期权类型筛选
    if filters.get('option_type'):
        option_type = filters['option_type']
        if option_type != '全部':
            if 'option_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['option_type'] == option_type]
    
    return filtered_df


def get_statistics(df: pd.DataFrame) -> dict:
    """
    获取数据统计信息
    
    :param df: DataFrame
    :return: 统计信息字典
    """
    stats = {
        'total_count': len(df),
        'unique_expirations': 0,
        'strike_range': (None, None),
        'option_types': []
    }
    
    if df.empty:
        return stats
    
    # 唯一到期日数量
    if 'expiration_date' in df.columns:
        stats['unique_expirations'] = df['expiration_date'].nunique()
    
    # 行权价范围
    if 'strike' in df.columns:
        stats['strike_range'] = (df['strike'].min(), df['strike'].max())
    
    # 期权类型
    if 'option_type' in df.columns:
        stats['option_types'] = df['option_type'].unique().tolist()
    
    return stats


@st.cache_resource
def load_database(db_path: str):
    """
    加载数据库连接（使用缓存）
    
    :param db_path: 数据库文件路径
    :return: 数据库对象
    """
    try:
        if not Path(db_path).exists():
            st.error(f"数据库文件不存在: {db_path}")
            return None
        db = OptionsDatabase(db_path=db_path)
        return db
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        logger.error(f"数据库连接失败: {e}")
        return None


@st.cache_data(ttl=60)  # 缓存60秒
def load_data(_db: OptionsDatabase, currency: str = None):
    """
    加载期权链数据
    
    :param _db: 数据库对象（使用_前缀避免缓存哈希问题）
    :param currency: 货币类型筛选
    :return: DataFrame
    """
    try:
        df = _db.get_latest_options_chain(limit=10000)
        if df.empty:
            return pd.DataFrame()
        
        # 如果指定了货币类型，进行筛选
        if currency and 'currency' in df.columns:
            df = df[df['currency'] == currency]
        
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        logger.error(f"数据加载失败: {e}")
        return pd.DataFrame()


def apply_custom_css():
    """
    应用自定义CSS样式
    在应用启动时调用一次即可
    """
    st.markdown("""
        <style>
        /* 全局容器样式 */
        .brand-container {
            display: flex;
            align-items: center;
            padding: 1.5rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        }
        
        /* 品牌图标 */
        .brand-icon {
            font-size: 3rem;
            margin-right: 1.2rem;
            line-height: 1;
        }
        
        /* 标题文字组 */
        .header-text-group {
            display: flex;
            flex-direction: column;
        }
        
        /* 主标题 */
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--text-color);
            margin: 0;
            line-height: 1.2;
            letter-spacing: -0.02em;
            font-family: 'Inter', sans-serif;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* 副标题/标签 */
        .sub-header {
            font-size: 0.9rem;
            color: var(--text-color);
            opacity: 0.7;
            margin-top: 0.4rem;
            font-weight: 400;
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }
        
        /* 标签样式 */
        .beta-tag {
            background-color: var(--primary-color);
            color: #ffffff;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            vertical-align: middle;
            text-transform: uppercase;
        }
        
        .author-tag {
            font-size: 0.8rem;
            font-family: monospace;
            background-color: var(--secondary-background-color);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(128, 128, 128, 0.2);
            transition: all 0.2s ease;
        }
        
        .author-link {
            text-decoration: none;
            color: inherit;
            display: inline-flex;
            align-items: center;
        }
        
        .author-link:hover .author-tag {
            border-color: var(--primary-color);
            color: var(--primary-color);
            background-color: rgba(31, 119, 180, 0.05);
            transform: translateY(-1px);
        }

        /* ------------------------------------------- */
        
        .metric-card {
            background-color: var(--secondary-background-color);
            padding: 1.2rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            border: 1px solid rgba(128, 128, 128, 0.1);
        }
        
        h2 {
            padding-bottom: 0.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            font-weight: 600;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        }
        
        h3 {
            margin-top: 1.5rem;
            font-weight: 600;
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        /* Metric 样式优化 - 移除强制白色背景，适应深色模式 */
        .stMetric {
            background-color: var(--secondary-background-color);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(128, 128, 128, 0.1);
        }
        
        /* 按钮样式微调 */
        .stButton>button {
            border-radius: 6px;
            font-weight: 500;
        }
        
        /* 标签过滤器 */
        .tag-filter-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 1rem 0;
        }
        .tag-button {
            padding: 0.4rem 0.8rem;
            border-radius: 0.4rem;
            border: 1px solid rgba(128, 128, 128, 0.2);
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            cursor: pointer;
            font-size: 0.9rem;
        }
        .tag-button:hover {
            border-color: var(--primary-color);
            color: var(--primary-color);
        }
        .tag-button.active {
            background-color: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }
        </style>
    """, unsafe_allow_html=True)


# 保持向后兼容
def init_page_style():
    """
    初始化页面样式（CSS）- 已弃用，请使用 apply_custom_css()
    在应用启动时调用一次即可
    """
    apply_custom_css()

