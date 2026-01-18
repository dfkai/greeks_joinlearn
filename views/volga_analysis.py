"""
Volga分析视图
基于期权链快照进行二阶风险分析：Volga-Vega散点图、IV-Vega收益热力图、Volga损耗计算器
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import List, Dict
from src.core import OptionsDatabase, BSCalculator, PortfolioAnalyzer
from src.utils import load_data


def safe_get_instrument_name(row):
    """
    安全获取合约名称，避免显示 undefined
    
    :param row: DataFrame row 或 Series
    :return: 合约名称字符串
    """
    name = row.get('instrument_name', None)
    
    # 检查是否有效
    if pd.isna(name) if isinstance(name, (float, np.floating)) else (name is None or name == ''):
        # 备用格式：类型-行权价
        opt_type = row.get('option_type', '?')
        strike = row.get('strike', 0)
        return f"{opt_type}-{strike:.0f}"
    
    return str(name)


def calculate_iv_percentile(df: pd.DataFrame, iv_col: str = 'mark_iv') -> pd.Series:
    """
    计算IV百分位（简化版：基于当前期权链的分布）
    如果没有历史数据，使用当前快照的分布作为参考
    
    :param df: 期权链数据
    :param iv_col: IV列名
    :return: IV百分位序列（0-100）
    """
    if df.empty or iv_col not in df.columns:
        return pd.Series([50.0] * len(df), index=df.index)
    
    iv_values = df[iv_col].dropna()
    if len(iv_values) == 0:
        return pd.Series([50.0] * len(df), index=df.index)
    
    # 使用当前快照的分布计算百分位
    percentiles = iv_values.rank(pct=True) * 100
    # 填充缺失值
    result = pd.Series([50.0] * len(df), index=df.index)
    result.loc[iv_values.index] = percentiles
    return result


def prepare_volga_data(df: pd.DataFrame, spot_price: float, risk_free_rate: float = 0.05) -> pd.DataFrame:
    """
    为期权链数据计算所有Greeks（Delta, Gamma, Vega, Volga, Vanna）
    用于完整泰勒展开PnL计算
    
    :param df: 期权链数据
    :param spot_price: 当前标的价格
    :param risk_free_rate: 无风险利率
    :return: 包含所有Greeks的DataFrame
    """
    if df.empty:
        return pd.DataFrame()
    
    result_df = df.copy()
    bs_calc = BSCalculator(risk_free_rate=risk_free_rate)
    
    # 确保必要的列存在
    required_cols = ['strike', 'expiration_date', 'mark_iv', 'option_type']
    missing_cols = [col for col in required_cols if col not in result_df.columns]
    if missing_cols:
        st.warning(f"缺少必要列: {missing_cols}")
        return pd.DataFrame()
    
    # 计算到期时间（年）
    result_df['expiration_date'] = pd.to_datetime(result_df['expiration_date'])
    current_date = pd.Timestamp.now()
    result_df['days_to_expiry'] = (result_df['expiration_date'] - current_date).dt.days
    result_df['time_to_maturity'] = result_df['days_to_expiry'] / 365.0
    result_df['time_to_maturity'] = result_df['time_to_maturity'].clip(lower=1e-6)  # 避免除零
    
    # 过滤掉已到期的期权
    result_df = result_df[result_df['days_to_expiry'] > 0].copy()
    
    if result_df.empty:
        return pd.DataFrame()
    
    # 准备计算参数
    S = spot_price
    K = result_df['strike'].values
    T = result_df['time_to_maturity'].values
    sigma = result_df['mark_iv'].fillna(0.5).values  # 缺失IV用0.5填充
    option_types = result_df['option_type'].values
    
    # 检测IV数据格式
    iv_max = result_df['mark_iv'].max()
    is_percentage_format = iv_max > 1.0
    if is_percentage_format:
        sigma = sigma / 100.0  # 转换为小数形式用于计算
    
    # 批量计算所有Greeks（使用calculate_all_greeks方法）
    deltas = []
    gammas = []
    vegas = []
    volgas = []
    vannas = []
    
    for i in range(len(result_df)):
        opt_type = 'call' if option_types[i] == 'C' else 'put'
        greeks = bs_calc.calculate_all_greeks(S, K[i], T[i], sigma[i], opt_type)
        
        deltas.append(greeks.get('delta', 0))
        gammas.append(greeks.get('gamma', 0))
        vegas.append(greeks.get('vega', 0))
        volgas.append(greeks.get('volga', 0))
        vannas.append(greeks.get('vanna', 0))
    
    result_df['delta'] = deltas
    result_df['gamma'] = gammas
    result_df['vega'] = vegas
    result_df['volga'] = volgas
    result_df['vanna'] = vannas
    
    # 保存原始IV格式用于显示
    if is_percentage_format:
        result_df['mark_iv_decimal'] = sigma
    else:
        result_df['mark_iv_decimal'] = result_df['mark_iv'].fillna(0.5)
    
    # 计算IV百分位
    result_df['iv_percentile'] = calculate_iv_percentile(result_df, 'mark_iv')
    
    return result_df


def render_volga_vega_scatter(df: pd.DataFrame):
    """
    模块1：风险地形图（Risk Topography）
    可视化Vega风险表面：识别对价格和波动率双重敏感的合约
    
    :param df: 包含所有Greeks的数据
    """
    st.subheader("📊 模块1：风险地形图（Risk Topography）")
    st.caption("X轴：Vega | Y轴：Volga | 点大小：未平仓量(OI) | 点颜色：Vanna（价格敏感度）")
    
    # 添加说明
    with st.expander("📚 解读指南", expanded=False):
        st.markdown("""
        **三维风险识别**：
        - **X轴（Vega）**：对IV变化的敏感度（一阶）
        - **Y轴（Volga）**：Vega对IV变化的敏感度（二阶，IV凸性）
        - **颜色（Vanna）**：Vega对价格变化的敏感度（二阶，价格×波动率交互）
        
        **高风险区域识别**：
        - **右上角+深色**：高Vega + 高Volga + 高Vanna = **三重高危合约**
          - 既怕IV变（Volga高）
          - 又怕价格变（Vanna高）
          - 且对IV变化本身敏感（Vega高）
        - **左下角+浅色**：低Vega + 低Volga + 低Vanna = **低风险合约**
        - **大点**：市场关注度高（高OI），需要重点关注
        """)
    
    if df.empty or 'vega' not in df.columns or 'volga' not in df.columns:
        st.warning("缺少必要的数据列（vega或volga）")
        return
    
    # 检查是否有Vanna
    has_vanna = 'vanna' in df.columns
    
    # 准备数据
    plot_cols = ['vega', 'volga', 'open_interest', 'instrument_name', 
                 'strike', 'option_type', 'expiration_date']
    if has_vanna:
        plot_cols.append('vanna')
    if 'iv_percentile' in df.columns:
        plot_cols.append('iv_percentile')
    
    plot_df = df[[col for col in plot_cols if col in df.columns]].copy()
    plot_df = plot_df.dropna(subset=['vega', 'volga'])
    
    if plot_df.empty:
        st.warning("没有有效的Vega/Volga数据")
        return
    
    # 处理OI缺失值
    if 'open_interest' in plot_df.columns:
        plot_df['open_interest'] = plot_df['open_interest'].fillna(0)
        plot_df['size'] = np.sqrt(plot_df['open_interest'] + 1) * 5  # 缩放点大小
    else:
        plot_df['size'] = 5  # 默认大小
    
    # 创建散点图
    if has_vanna and 'vanna' in plot_df.columns:
        # 使用Vanna作为颜色维度
        color_col = 'vanna'
        color_label = 'Vanna (价格敏感度)'
        color_scale = 'Viridis'  # 深色=高Vanna（高风险），浅色=低Vanna（低风险）
    elif 'iv_percentile' in plot_df.columns:
        # 回退到IV百分位
        color_col = 'iv_percentile'
        color_label = 'IV百分位'
        color_scale = 'RdYlGn_r'
    else:
        color_col = None
        color_label = None
        color_scale = None
    
    if color_col:
        fig = px.scatter(
            plot_df,
            x='vega',
            y='volga',
            size='size',
            color=color_col,
            hover_data=['instrument_name', 'strike', 'option_type', 'expiration_date', 'open_interest'],
            color_continuous_scale=color_scale,
            labels={
                'vega': 'Vega',
                'volga': 'Volga',
                color_col: color_label,
                'size': '未平仓量'
            },
            title='风险地形图：Vega风险表面（Volga vs Vega，颜色=Vanna）'
        )
    else:
        fig = px.scatter(
            plot_df,
            x='vega',
            y='volga',
            size='size',
            hover_data=['instrument_name', 'strike', 'option_type', 'expiration_date', 'open_interest'],
            labels={
                'vega': 'Vega',
                'volga': 'Volga',
                'size': '未平仓量'
            },
            title='Volga-Vega风险聚类图'
        )
    
    # 添加风险区域标注
    if len(plot_df) > 0:
        fig.add_annotation(
            x=plot_df['vega'].quantile(0.9),
            y=plot_df['volga'].quantile(0.9),
            text="三重高危区域<br>（高Vega+高Volga+高Vanna）" if has_vanna else "高风险区域<br>（高Vega+高Volga+高IV）",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            bgcolor="rgba(255,0,0,0.2)",
            bordercolor="red"
        )
    
    fig.update_layout(
        height=600,
        template='plotly_white',
        hovermode='closest'
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("数据点数", len(plot_df))
    with col2:
        high_risk_count = len(plot_df[(plot_df['vega'] > plot_df['vega'].quantile(0.8)) & 
                                     (plot_df['volga'] > plot_df['volga'].quantile(0.8)) &
                                     (plot_df['iv_percentile'] > 80)])
        st.metric("高风险合约数", high_risk_count)
    with col3:
        st.metric("Vega范围", f"{plot_df['vega'].min():.2f} ~ {plot_df['vega'].max():.2f}")
    with col4:
        st.metric("Volga范围", f"{plot_df['volga'].min():.2f} ~ {plot_df['volga'].max():.2f}")


def calculate_full_pnl(df: pd.DataFrame, spot_price: float, price_change_pct: float, iv_change_pct: float) -> pd.DataFrame:
    """
    使用完整泰勒展开计算PnL
    
    PnL = Delta * dS + 0.5 * Gamma * dS^2 + Vega * dVol + 0.5 * Volga * dVol^2 + Vanna * dS * dVol
    
    :param df: 包含所有Greeks的DataFrame
    :param spot_price: 当前标的价格
    :param price_change_pct: 价格变动百分比（如+2表示+2%）
    :param iv_change_pct: IV变动百分比（如-3表示-3%）
    :return: 添加了PnL归因列的DataFrame
    """
    result_df = df.copy()
    
    # 转换为绝对变动
    dS = spot_price * price_change_pct / 100.0  # 价格绝对变动
    dVol = iv_change_pct / 100.0  # IV相对变动（小数形式）
    
    # 确保IV是小数形式
    if 'mark_iv_decimal' in result_df.columns:
        current_iv = result_df['mark_iv_decimal']
    else:
        # 检测格式
        iv_max = result_df['mark_iv'].max()
        if iv_max > 1.0:
            current_iv = result_df['mark_iv'] / 100.0
        else:
            current_iv = result_df['mark_iv']
    
    # 计算PnL归因
    # 价格效应（一阶+二阶）
    result_df['pnl_price_delta'] = result_df['delta'] * dS
    result_df['pnl_price_gamma'] = 0.5 * result_df['gamma'] * dS * dS
    result_df['pnl_price_total'] = result_df['pnl_price_delta'] + result_df['pnl_price_gamma']
    
    # 波动率效应（一阶+二阶）
    result_df['pnl_vol_vega'] = result_df['vega'] * dVol * 100  # 转换为百分比显示
    result_df['pnl_vol_volga'] = 0.5 * result_df['volga'] * dVol * dVol * 100  # 转换为百分比显示
    result_df['pnl_vol_total'] = result_df['pnl_vol_vega'] + result_df['pnl_vol_volga']
    
    # 交互效应（Vanna）
    result_df['pnl_interaction'] = result_df['vanna'] * dS * dVol * 100  # 转换为百分比显示
    
    # 总PnL
    result_df['pnl_total'] = result_df['pnl_price_total'] + result_df['pnl_vol_total'] + result_df['pnl_interaction']
    
    return result_df


def render_iv_vega_heatmap(df: pd.DataFrame, spot_price: float):
    """
    模块2：动态情景推演引擎（Dynamic Scenario Engine）
    基于期权链快照，使用完整泰勒展开计算PnL，找出最佳可交易组合
    
    包含两种视图：
    1. 热力图视图：IV区间 × Vega区间的收益热力图
    2. 散点图视图：所有实际合约的IV-Vega散点图（带PnL颜色）
    
    :param df: 包含所有Greeks的数据
    :param spot_price: 当前标的价格
    """
    st.subheader("🔥 模块2：动态情景推演引擎（Dynamic Scenario Engine）")
    st.caption("控制变量法：定格时间（快照数据），推演价格与波动率双重变化下的最佳组合")
    
    # 添加说明
    with st.expander("📚 核心逻辑说明", expanded=True):
        st.markdown("""
        **控制变量法设计**：
        - ✅ **时间**：固定（使用数据库快照，时间停滞在T0）
        - 🎛️ **价格变动**：您控制（通过滑杆输入预期价格变动%）
        - 🎛️ **IV变动**：您控制（通过滑杆输入预期IV变动%）
        
        **完整泰勒展开PnL公式**：
        ```
        PnL = Δ·dS + ½·Γ·(dS)² + ν·dσ + ½·Volga·(dσ)² + Vanna·dS·dσ
        ```
        - **价格效应**：Delta贡献 + Gamma凸性
        - **波动率效应**：Vega贡献 + **Volga凸性**（核心！）
        - **交互效应**：Vanna（价格×波动率交叉项）
        
        **动态推荐**：调整价格/IV变动假设，最佳组合会实时变化
        
        **视图说明**：
        - **热力图视图**：将IV和Vega分成区间，显示每个区间的平均收益，适合快速识别收益-风险平衡区域
        - **散点图视图**：显示所有实际合约，颜色表示总PnL，适合精确选择具体合约
        """)
    
    # 检查必要列
    required_greeks = ['delta', 'gamma', 'vega', 'volga', 'vanna']
    missing_greeks = [g for g in required_greeks if g not in df.columns]
    if missing_greeks:
        st.warning(f"缺少必要的Greeks列: {missing_greeks}。请确保数据已计算所有Greeks。")
        return
    
    if df.empty:
        st.warning("没有有效数据")
        return
    
    # 准备实际合约数据
    required_cols = ['mark_iv', 'delta', 'gamma', 'vega', 'volga', 'vanna', 
                     'instrument_name', 'strike', 'option_type', 'expiration_date']
    available_cols = [col for col in required_cols if col in df.columns]
    
    plot_df = df[available_cols].copy()
    plot_df = plot_df.dropna(subset=required_greeks)
    
    if plot_df.empty:
        st.warning("没有有效的Greeks数据")
        return
    
    # 视图选择
    view_mode = st.radio(
        "选择视图模式",
        ["热力图视图", "散点图视图"],
        horizontal=True,
        help="热力图：快速识别收益-风险平衡区域 | 散点图：精确选择具体合约"
    )
    
    # 情景控制台
    st.subheader("🎛️ 情景控制台（Scenario Controls）")
    col1, col2 = st.columns(2)
    
    with col1:
        price_change_pct = st.slider(
            "预期价格变动 (%)",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            help="模拟标的价格变化（如+2%表示价格上涨2%）"
        )
    
    with col2:
        iv_change_pct = st.slider(
            "预期IV变动 (%)",
            min_value=-10.0,
            max_value=10.0,
            value=-3.0,
            step=0.5,
            help="模拟IV变化（如-3%表示IV下降3%）"
        )
    
    # 检查情景设置是否合理
    if abs(price_change_pct) < 0.01 and abs(iv_change_pct) < 0.01:
        st.warning("⚠️ **注意**：当前价格变动和IV变动都接近0%，所有合约的PnL都将为0。\n\n"
                  "**建议**：调整至少一个参数（价格变动或IV变动），以设定有意义的市场情景。\n"
                  "例如：\n"
                  "- IV压缩场景：IV变动 = -3%（预期波动率下降）\n"
                  "- IV扩张场景：IV变动 = +5%（预期波动率上升）\n"
                  "- 价格上涨场景：价格变动 = +5%\n"
                  "- 价格下跌场景：价格变动 = -5%")
    else:
        st.info(f"💡 **当前情景**：价格变动 **{price_change_pct:+.1f}%**，IV变动 **{iv_change_pct:+.1f}%**。最佳组合会基于此情景实时计算。")
        
        # 如果只有价格变动为0，给出提示
        if abs(price_change_pct) < 0.01 and abs(iv_change_pct) >= 0.01:
            st.info("📌 **提示**：当前价格变动为0%，因此所有合约的**价格贡献（Delta + Gamma）都为0**。"
                   "这是正常的，因为价格不变时，价格相关的Greeks不会产生PnL。"
                   "总PnL = 波动率贡献（Vega + Volga）+ 交互贡献（Vanna）。"
                   "调整价格变动滑杆可以观察价格变化对PnL的影响。")
    
    # 使用完整泰勒展开计算PnL
    plot_df = calculate_full_pnl(plot_df, spot_price, price_change_pct, iv_change_pct)
    
    # 根据视图模式显示不同图表
    if view_mode == "热力图视图":
        _render_heatmap_view(plot_df, spot_price, price_change_pct, iv_change_pct)
    else:
        _render_scatter_view(plot_df, spot_price, price_change_pct, iv_change_pct)
    
    # 显示最佳组合推荐和Top 10列表（两种视图都显示）
    _render_best_combinations(plot_df)


def _render_heatmap_view(plot_df: pd.DataFrame, spot_price: float, price_change_pct: float, iv_change_pct: float):
    """
    渲染热力图视图：IV区间 × Vega区间的收益热力图
    
    :param plot_df: 包含PnL数据的DataFrame
    :param spot_price: 当前标的价格
    :param price_change_pct: 价格变动百分比
    :param iv_change_pct: IV变动百分比
    """
    st.subheader("📊 热力图视图：IV-Vega收益热力图")
    
    # 准备IV显示格式
    if 'mark_iv_decimal' in plot_df.columns:
        iv_display = plot_df['mark_iv_decimal'] * 100
    else:
        iv_max = plot_df['mark_iv'].max()
        if iv_max > 1.0:
            iv_display = plot_df['mark_iv']
        else:
            iv_display = plot_df['mark_iv'] * 100
    
    # 设置区间数量
    num_bins = st.slider(
        "区间数量",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
        help="将IV和Vega分成多少个区间（区间越多，分辨率越高，但计算时间稍长）"
    )
    
    # 创建IV和Vega区间
    iv_min, iv_max = iv_display.min(), iv_display.max()
    vega_min, vega_max = plot_df['vega'].min(), plot_df['vega'].max()
    
    # 确保区间范围合理
    iv_bins = np.linspace(iv_min, iv_max, num_bins + 1)
    vega_bins = np.linspace(vega_min, vega_max, num_bins + 1)
    
    # 将数据分配到区间
    plot_df['iv_bin'] = pd.cut(iv_display, bins=iv_bins, include_lowest=True, labels=False)
    plot_df['vega_bin'] = pd.cut(plot_df['vega'], bins=vega_bins, include_lowest=True, labels=False)
    
    # 计算每个区间的平均PnL
    heatmap_data = plot_df.groupby(['iv_bin', 'vega_bin'])['pnl_total'].mean().reset_index()
    heatmap_pivot = heatmap_data.pivot(index='vega_bin', columns='iv_bin', values='pnl_total')
    
    # 统计空区间数量（用于说明）
    total_cells = heatmap_pivot.size
    empty_cells = heatmap_pivot.isna().sum().sum()
    filled_cells = total_cells - empty_cells
    empty_pct = empty_cells / total_cells * 100 if total_cells > 0 else 0
    
    # 如果空区间太多，给出提示
    if empty_cells > 0:
        if empty_pct > 50:
            st.warning(f"⚠️ **注意**：热力图中 {empty_cells}/{total_cells} ({empty_pct:.1f}%) 的区间没有数据点（显示为NaN）。"
                      f"这可能是因为：\n"
                      f"1. 期权链数据分布不均匀（某些IV-Vega组合在市场中不存在）\n"
                      f"2. 区间数量设置过多，导致数据过于分散\n"
                      f"**建议**：尝试减少区间数量（当前：{num_bins}），或切换到散点图视图查看所有实际合约")
    
    # 创建热力图（NaN值会被Plotly自动处理为空白）
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_pivot.values,
        x=[f"{iv_bins[i]:.1f}-{iv_bins[i+1]:.1f}%" for i in range(len(iv_bins)-1)],
        y=[f"{vega_bins[i]:.2f}-{vega_bins[i+1]:.2f}" for i in range(len(vega_bins)-1)],
        colorscale='RdYlGn',
        colorbar=dict(title="平均总PnL"),
        hovertemplate='IV区间: %{x}<br>Vega区间: %{y}<br>平均PnL: %{z:.2f}<extra></extra>',
        text=heatmap_pivot.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 8},
        zmid=0  # 设置颜色中点，使0值显示为中性色
    ))
    
    fig.update_layout(
        title=f'IV-Vega收益热力图（价格{price_change_pct:+.1f}%, IV{iv_change_pct:+.1f}%）- 基于完整泰勒展开',
        xaxis_title='IV区间 (%)',
        yaxis_title='Vega区间',
        height=600,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, width='stretch')
    
    st.caption("💡 **解读指南**：暖色（红/黄）表示正PnL（收益），冷色（蓝/绿）表示负PnL（损失）。"
              "通过热力图可以快速识别哪些IV-Vega组合区域具有最佳收益潜力。"
              f"**数据覆盖**：{filled_cells}/{total_cells} 区间有数据（{100-empty_pct:.1f}%），空白区域表示该IV-Vega组合在当前期权链中不存在。")


def _render_scatter_view(plot_df: pd.DataFrame, spot_price: float, price_change_pct: float, iv_change_pct: float):
    """
    渲染散点图视图：所有实际合约的IV-Vega散点图（带PnL颜色）
    
    :param plot_df: 包含PnL数据的DataFrame
    :param spot_price: 当前标的价格
    :param price_change_pct: 价格变动百分比
    :param iv_change_pct: IV变动百分比
    """
    st.subheader("📊 散点图视图：IV-Vega收益散点图")
    
    # 准备IV显示格式
    if 'mark_iv_decimal' in plot_df.columns:
        iv_display = plot_df['mark_iv_decimal'] * 100
    else:
        iv_max = plot_df['mark_iv'].max()
        if iv_max > 1.0:
            iv_display = plot_df['mark_iv']
        else:
            iv_display = plot_df['mark_iv'] * 100
    
    # 找出最佳组合（基于总PnL）
    best_buy = plot_df.loc[plot_df['pnl_total'].idxmax()]  # 买入：PnL最高
    best_sell = plot_df.loc[plot_df['pnl_total'].idxmin()]  # 卖出：PnL最低（负值最大）
    
    # 创建散点图：显示所有实际合约（颜色=总PnL）
    fig = go.Figure()
    
    # 添加所有合约的散点
    fig.add_trace(go.Scatter(
        x=iv_display,
        y=plot_df['vega'],
        mode='markers',
        marker=dict(
            size=8,
            color=plot_df['pnl_total'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="总PnL"),
            line=dict(width=1, color='gray')
        ),
        text=plot_df.apply(lambda row: f"{safe_get_instrument_name(row)}<br>"
                                       f"行权价: {row.get('strike', 0):.0f}<br>"
                                       f"类型: {row.get('option_type', 'N/A')}<br>"
                                       f"IV: {iv_display.iloc[plot_df.index.get_loc(row.name)]:.2f}%<br>"
                                       f"Vega: {row['vega']:.2f}<br>"
                                       f"总PnL: {row['pnl_total']:.2f}<br>"
                                       f"  - 价格: {row['pnl_price_total']:.2f}<br>"
                                       f"  - 波动率: {row['pnl_vol_total']:.2f} (Volga: {row['pnl_vol_volga']:.2f})<br>"
                                       f"  - 交互: {row['pnl_interaction']:.2f}", axis=1),
        hovertemplate='%{text}<extra></extra>',
        name='所有合约'
    ))
    
    # 高亮最佳买入合约
    best_buy_iv = iv_display.iloc[plot_df.index.get_loc(best_buy.name)]
    fig.add_trace(go.Scatter(
        x=[best_buy_iv],
        y=[best_buy['vega']],
        mode='markers',
        marker=dict(
            size=20,
            symbol='star',
            color='green',
            line=dict(width=2, color='darkgreen')
        ),
        name='最佳买入',
        hovertemplate=f"最佳买入合约<br>{safe_get_instrument_name(best_buy)}<br>总PnL: {best_buy['pnl_total']:.2f}<extra></extra>"
    ))
    
    # 高亮最佳卖出合约
    best_sell_iv = iv_display.iloc[plot_df.index.get_loc(best_sell.name)]
    fig.add_trace(go.Scatter(
        x=[best_sell_iv],
        y=[best_sell['vega']],
        mode='markers',
        marker=dict(
            size=20,
            symbol='star',
            color='red',
            line=dict(width=2, color='darkred')
        ),
        name='最佳卖出',
        hovertemplate=f"最佳卖出合约<br>{safe_get_instrument_name(best_sell)}<br>总PnL: {best_sell['pnl_total']:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        title=f'IV-Vega收益散点图（价格{price_change_pct:+.1f}%, IV{iv_change_pct:+.1f}%）- 基于完整泰勒展开',
        xaxis_title='IV (%)',
        yaxis_title='Vega',
        height=600,
        template='plotly_white',
        hovermode='closest',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, width='stretch')
    
    st.caption("💡 **解读指南**：每个点代表一个实际合约，颜色表示总PnL（暖色=收益，冷色=损失）。"
              "绿色星标=最佳买入合约，红色星标=最佳卖出合约。")


def _render_best_combinations(plot_df: pd.DataFrame):
    """
    渲染最佳组合推荐和Top 10列表
    
    :param plot_df: 包含PnL数据的DataFrame
    """
    # 检查是否所有PnL都接近0（说明没有价格或IV变动）
    pnl_range = plot_df['pnl_total'].max() - plot_df['pnl_total'].min()
    max_abs_pnl = max(abs(plot_df['pnl_total'].max()), abs(plot_df['pnl_total'].min()))
    
    if pnl_range < 0.01 and max_abs_pnl < 0.01:
        st.warning("⚠️ **注意**：当前所有合约的PnL都接近0，无法推荐最佳组合。\n\n"
                  "**原因**：您设置的价格变动和IV变动都接近0%，导致所有合约的收益预期都为0。\n\n"
                  "**建议**：\n"
                  "1. 调整\"预期价格变动\"滑杆（例如：±5%）\n"
                  "2. 调整\"预期IV变动\"滑杆（例如：-3%表示IV压缩，+5%表示IV扩张）\n"
                  "3. 设定有意义的市场情景后，最佳组合推荐才会有价值")
        return
    
    # 找出最佳组合（基于总PnL）
    best_buy = plot_df.loc[plot_df['pnl_total'].idxmax()]  # 买入：PnL最高
    best_sell = plot_df.loc[plot_df['pnl_total'].idxmin()]  # 卖出：PnL最低（负值最大）
    
    # 显示最佳组合推荐
    st.subheader("🎯 最佳组合推荐（基于当前情景）")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ 最佳买入合约**（总PnL最高）")
        st.write(f"- **合约**: {safe_get_instrument_name(best_buy)}")
        st.write(f"- **行权价**: {best_buy.get('strike', 0):.0f}")
        st.write(f"- **类型**: {best_buy.get('option_type', 'N/A')}")
        if 'mark_iv_decimal' in best_buy:
            st.write(f"- **当前IV**: {best_buy['mark_iv_decimal']*100:.2f}%")
        st.write(f"- **总PnL**: **{best_buy['pnl_total']:.2f}**")
        st.write(f"  - 价格贡献: {best_buy['pnl_price_total']:.2f} (Delta: {best_buy['pnl_price_delta']:.2f}, Gamma: {best_buy['pnl_price_gamma']:.2f})")
        st.write(f"  - 波动率贡献: {best_buy['pnl_vol_total']:.2f} (Vega: {best_buy['pnl_vol_vega']:.2f}, **Volga: {best_buy['pnl_vol_volga']:.2f}**)")
        st.write(f"  - 交互贡献: {best_buy['pnl_interaction']:.2f} (Vanna)")
    
    with col2:
        st.markdown("**❌ 最佳卖出合约**（总PnL最低，适合做空）")
        st.write(f"- **合约**: {safe_get_instrument_name(best_sell)}")
        st.write(f"- **行权价**: {best_sell.get('strike', 0):.0f}")
        st.write(f"- **类型**: {best_sell.get('option_type', 'N/A')}")
        if 'mark_iv_decimal' in best_sell:
            st.write(f"- **当前IV**: {best_sell['mark_iv_decimal']*100:.2f}%")
        st.write(f"- **总PnL**: **{best_sell['pnl_total']:.2f}**")
        st.write(f"  - 价格贡献: {best_sell['pnl_price_total']:.2f} (Delta: {best_sell['pnl_price_delta']:.2f}, Gamma: {best_sell['pnl_price_gamma']:.2f})")
        st.write(f"  - 波动率贡献: {best_sell['pnl_vol_total']:.2f} (Vega: {best_sell['pnl_vol_vega']:.2f}, **Volga: {best_sell['pnl_vol_volga']:.2f}**)")
        st.write(f"  - 交互贡献: {best_sell['pnl_interaction']:.2f} (Vanna)")
    
    st.success(f"💡 **归因分析**：最佳买入合约的总PnL为 **{best_buy['pnl_total']:.2f}**，其中波动率贡献（Vega+Volga）为 **{best_buy['pnl_vol_total']:.2f}**，"
              f"Volga凸性贡献为 **{best_buy['pnl_vol_volga']:.2f}**。这说明了Volga在PnL中的重要作用！")
    
    # 显示Top 10最佳组合（带归因分析）
    st.subheader("📊 Top 10 最佳买入合约（总PnL从高到低，带归因分析）")
    top_buy = plot_df.nlargest(10, 'pnl_total')[
        ['instrument_name', 'strike', 'option_type', 'pnl_total', 
         'pnl_price_total', 'pnl_vol_total', 'pnl_vol_volga', 'pnl_interaction']
    ].copy()
    top_buy_display = top_buy.copy()
    top_buy_display.columns = ['合约名称', '行权价', '类型', '总PnL', 
                               '价格贡献', '波动率贡献', 'Volga贡献', '交互贡献']
    top_buy_display = top_buy_display.round(2)
    st.dataframe(top_buy_display, width='stretch')
    
    st.caption("💡 **归因解读**：查看每个合约的PnL来源。如果'Volga贡献'很大，说明该合约的收益主要来自Volga凸性，而非简单的Vega线性效应。")
    
    st.subheader("📊 Top 10 最佳卖出合约（总PnL从低到高，适合做空）")
    top_sell = plot_df.nsmallest(10, 'pnl_total')[
        ['instrument_name', 'strike', 'option_type', 'pnl_total',
         'pnl_price_total', 'pnl_vol_total', 'pnl_vol_volga', 'pnl_interaction']
    ].copy()
    top_sell_display = top_sell.copy()
    top_sell_display.columns = ['合约名称', '行权价', '类型', '总PnL',
                               '价格贡献', '波动率贡献', 'Volga贡献', '交互贡献']
    top_sell_display = top_sell_display.round(2)
    st.dataframe(top_sell_display, width='stretch')


def render_volga_loss_calculator(df: pd.DataFrame, spot_price: float):
    """
    模块3：Volga损耗计算器（具体数值）
    
    :param df: 包含Volga和Vega的数据
    :param spot_price: 当前标的价格
    """
    st.subheader("🧮 模块3：Volga损耗计算器（具体数值）")
    st.caption("选择合约，对比线性Vega PnL vs 考虑Volga的凸性PnL")
    
    # 添加说明
    st.info("""
    **解读指南**：
    - **蓝色线（线性PnL）**：假设Vega不变时的PnL = Vega × IV变动
    - **红色线（凸性PnL）**：考虑Volga影响的实际PnL = (Vega + Volga×IV变动) × IV变动
    - **两条线的差值 = Volga损耗**：量化了忽略Volga导致的收益偏差
    - **Volga < 0时**：红色线在蓝色线下方（损耗），说明实际收益低于线性预期
    - **Volga > 0时**：红色线在蓝色线上方（增益），说明实际收益高于线性预期
    
    **计算点数说明**：
    - 计算点数 = 在IV变动范围内生成的数据点数量
    - 例如：IV变动范围是-10%到+10%，计算点数为50，则会在-10%、-9.6%、-9.2%...到+10%之间生成50个均匀分布的点
    - 每个点都会计算对应的线性PnL和凸性PnL，然后连接成曲线
    - 点数越多，曲线越平滑，但计算时间稍长（通常20-50点足够）
    """)
    
    # 检查必要列
    required_greeks = ['delta', 'gamma', 'vega', 'volga', 'vanna']
    missing_greeks = [g for g in required_greeks if g not in df.columns]
    if missing_greeks:
        st.warning(f"缺少必要的Greeks列: {missing_greeks}")
        return
    
    if df.empty:
        st.warning("没有有效数据")
        return
    
    # 准备合约列表
    required_cols = ['instrument_name', 'strike', 'option_type', 'expiration_date', 
                     'delta', 'gamma', 'vega', 'volga', 'vanna', 'mark_iv']
    available_cols = [col for col in required_cols if col in df.columns]
    
    contract_df = df[available_cols].copy()
    contract_df = contract_df.dropna(subset=required_greeks)
    
    if contract_df.empty:
        st.warning("没有有效的合约数据")
        return
    
    # 创建显示名称（使用apply避免Series格式化问题）
    def format_contract_name(row):
        inst_name = safe_get_instrument_name(row)
        strike = float(row.get('strike', 0))
        opt_type = str(row.get('option_type', '?'))
        vega_val = float(row.get('vega', 0))
        volga_val = float(row.get('volga', 0))
        exp_date = str(row.get('expiration_date', ''))[:10] if 'expiration_date' in row else ''
        
        # 简化显示：只显示关键信息
        return f"{inst_name} | 行权价:{strike:.0f} | {opt_type} | Vega:{vega_val:.2f} | Volga:{volga_val:.2f}"
    
    contract_df['display_name'] = contract_df.apply(format_contract_name, axis=1)
    
    # 合约选择器
    if len(contract_df) > 0:
        selected_idx = st.selectbox(
            "选择合约（用于Volga损耗分析）",
            options=range(len(contract_df)),
            format_func=lambda x: contract_df.iloc[x]['display_name'] if 0 <= x < len(contract_df) else "无效索引"
        )
        
        # 安全获取选中的合约
        if 0 <= selected_idx < len(contract_df):
            selected_contract = contract_df.iloc[selected_idx]
        else:
            st.error("选择的合约索引无效")
            return
    else:
        st.warning("没有可用的合约数据")
        return
    
    # 显示选中合约信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vega", f"{selected_contract['vega']:.2f}")
    with col2:
        st.metric("Volga", f"{selected_contract['volga']:.2f}")
    with col3:
        st.metric("当前IV", f"{selected_contract['mark_iv']:.2%}")
    with col4:
        st.metric("行权价", f"{selected_contract['strike']:.0f}")
    
    # 情景控制：价格和IV变动
    st.write("**情景设置**")
    col1, col2, col3 = st.columns(3)
    with col1:
        price_change_pct = st.number_input(
            "价格变动 (%)",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            help="模拟标的价格变化（固定值，用于观察Vanna影响）"
        )
    with col2:
        iv_change_min = st.number_input(
            "IV变动最小值 (%)",
            min_value=-50.0,
            max_value=0.0,
            value=-10.0,
            step=1.0
        )
    with col3:
        iv_change_max = st.number_input(
            "IV变动最大值 (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0
        )
    
    num_points = st.slider(
        "计算点数", 
        min_value=20, 
        max_value=100, 
        value=50, 
        step=10,
        help="在IV变动范围内生成多少个数据点来绘制PnL曲线"
    )
    
    # 计算PnL曲线
    iv_changes = np.linspace(iv_change_min, iv_change_max, num_points)
    
    # 获取合约Greeks
    delta = selected_contract['delta']
    gamma = selected_contract['gamma']
    vega = selected_contract['vega']
    volga = selected_contract['volga']
    vanna = selected_contract['vanna']
    
    # 价格变动（绝对）
    dS = spot_price * price_change_pct / 100.0
    
    # 线性PnL（只考虑一阶Greeks）
    # PnL = Delta × dS + Vega × dVol
    linear_pnl = delta * dS + vega * (iv_changes / 100.0) * 100  # 转换为百分比显示
    
    # 完整PnL（包含所有Greeks）
    # PnL = Delta×dS + ½×Gamma×(dS)² + Vega×dVol + ½×Volga×(dVol)² + Vanna×dS×dVol
    dVol = iv_changes / 100.0
    full_pnl = (delta * dS + 
                0.5 * gamma * dS * dS +
                vega * dVol * 100 +
                0.5 * volga * dVol * dVol * 100 +
                vanna * dS * dVol * 100)
    
    # 凸性贡献 = 完整PnL - 线性PnL
    convexity_contribution = full_pnl - linear_pnl
    
    # 创建图表
    fig = go.Figure()
    
    # 线性PnL线
    fig.add_trace(go.Scatter(
        x=iv_changes,
        y=linear_pnl,
        mode='lines',
        name='线性PnL（一阶Greeks）',
        line=dict(color='blue', width=2),
        hovertemplate='IV变动: %{x:.2f}%<br>PnL: %{y:.2f}<extra></extra>'
    ))
    
    # 完整PnL线
    fig.add_trace(go.Scatter(
        x=iv_changes,
        y=full_pnl,
        mode='lines',
        name='完整PnL（包含Volga/Vanna/Gamma）',
        line=dict(color='red', width=2),
        hovertemplate='IV变动: %{x:.2f}%<br>PnL: %{y:.2f}<extra></extra>'
    ))
    
    # 零线
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    fig.add_vline(x=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    # 安全获取合约名称
    contract_name = selected_contract.get('instrument_name', 'N/A')
    if contract_name is None or contract_name == '':
        contract_name = f"{selected_contract.get('option_type', '?')} {selected_contract.get('strike', 0):.0f}"
    
    fig.update_layout(
        title=f'凸性分析：{contract_name}（价格{price_change_pct:+.1f}%）',
        xaxis_title='IV变动 (%)',
        yaxis_title='PnL',
        height=500,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # 显示归因统计
    st.write("**凸性贡献统计**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if len(convexity_contribution) > 0:
            max_contrib = convexity_contribution.max()
            max_idx = np.argmax(convexity_contribution)
            if max_idx < len(iv_changes):
                st.metric("最大凸性贡献", f"{max_contrib:.2f}", 
                         delta=f"IV变动 {iv_changes[max_idx]:+.1f}%")
            else:
                st.metric("最大凸性贡献", f"{max_contrib:.2f}")
        else:
            st.metric("最大凸性贡献", "N/A")
    with col2:
        if len(convexity_contribution) > 0:
            min_contrib = convexity_contribution.min()
            st.metric("最小凸性贡献", f"{min_contrib:.2f}")
        else:
            st.metric("最小凸性贡献", "N/A")
    with col3:
        if len(convexity_contribution) > 0:
            avg_contrib = convexity_contribution.mean()
            st.metric("平均凸性贡献", f"{avg_contrib:.2f}")
        else:
            st.metric("平均凸性贡献", "N/A")
    with col4:
        if len(iv_changes) > 0 and len(convexity_contribution) > 0:
            target_idx = np.abs(iv_changes - -3.0).argmin()
            if target_idx < len(convexity_contribution):
                contrib_at_target = convexity_contribution[target_idx]
                st.metric("IV降3%时贡献", f"{contrib_at_target:.2f}")
            else:
                st.metric("IV降3%时贡献", "N/A")
        else:
            st.metric("IV降3%时贡献", "N/A")
    
    # 显示Greeks值
    st.write("**当前合约Greeks值**")
    greeks_col1, greeks_col2, greeks_col3, greeks_col4, greeks_col5 = st.columns(5)
    with greeks_col1:
        st.metric("Delta", f"{delta:.4f}")
    with greeks_col2:
        st.metric("Gamma", f"{gamma:.6f}")
    with greeks_col3:
        st.metric("Vega", f"{vega:.2f}")
    with greeks_col4:
        st.metric("Volga", f"{volga:.2f}")
    with greeks_col5:
        st.metric("Vanna", f"{vanna:.6f}")
    
    st.info(f"💡 **价格影响**：当前价格变动设置为 **{price_change_pct:+.1f}%**。调整此值可以观察Vanna（价格×波动率交互项）如何影响PnL曲线。"
            f"当价格变动=0时，Vanna项为0；当价格变动≠0时，Vanna会扭曲Vega PnL曲线。")


def render_volga_analysis_view(db: OptionsDatabase):
    """
    Volga分析主视图
    
    :param db: 数据库对象
    """
    st.header("🌊 Volga分析视图")
    st.caption("基于期权链快照进行二阶风险分析：识别高风险聚类、收益-风险平衡点、量化Volga损耗")
    
    # 理论解读部分（可展开）
    with st.expander("📚 理论解读：什么是Volga？", expanded=False):
        st.markdown("""
        ### Volga（又称Vomma）的定义
        
        **Volga = ∂²C/∂σ² = ∂Vega/∂σ**
        
        Volga衡量**Vega对波动率变化的敏感性**，是二阶Greeks参数。
        
        #### 核心概念
        
        1. **一阶Greeks - Vega**：
           - Vega = ∂C/∂σ，表示期权价格对波动率变化的敏感性
           - 当IV变化1%时，期权价格变化 = Vega × 1%
        
        2. **二阶Greeks - Volga**：
           - Volga = ∂Vega/∂σ，表示Vega本身对波动率变化的敏感性
           - 当IV变化时，Vega也会变化，Volga量化了这个变化速度
        
        #### 实际意义
        
        - **Volga > 0**：IV增加时，Vega也增加（凸性）
        - **Volga < 0**：IV增加时，Vega减少（凹性）
        - **Volga ≈ 0**：Vega对IV变化不敏感（线性）
        
        #### 为什么重要？
        
        1. **风险管理**：高Volga的合约，Vega会随IV快速变化，风险难以预测
        2. **收益优化**：Volga会影响IV变化时的实际收益，需要考虑凸性调整
        3. **策略选择**：不同Volga特征的合约适合不同的市场环境
        
        #### 计算公式
        
        ```
        Volga = Vega × d1 × d2 / σ
        其中：
        d1 = [ln(S/K) + (r + σ²/2)×T] / (σ×√T)
        d2 = d1 - σ×√T
        ```
        """)
    
    # 验证说明
    with st.expander("✅ 如何验证图表正确性？", expanded=False):
        st.markdown("""
        ### 模块1：Volga-Vega散点图验证
        
        1. **数据点分布**：
           - 检查散点是否合理分布（不应全部集中在原点）
           - 高风险区域（右上角）应该有红色点（高IV百分位）
        
        2. **点大小**：
           - 大点应该对应高OI的合约
           - 悬停查看OI值验证
        
        3. **点颜色**：
           - 红色区域 = 高IV百分位（80-100%）= 高风险
           - 绿色区域 = 低IV百分位（0-20%）= 低风险
        
        ### 模块2：IV-Vega收益热力图验证
        
        1. **理论PnL计算**：
           - PnL = Vega × IV变动
           - 调整IV变动滑杆，热力图应该实时更新
        
        2. **颜色映射**：
           - 暖色（红/黄）= 正PnL（收益）
           - 冷色（蓝/绿）= 负PnL（损失）
        
        3. **逻辑验证**：
           - 负Vega + IV下降 = 正PnL（卖期权，IV降赚）
           - 正Vega + IV上升 = 正PnL（买期权，IV升赚）
        
        ### 模块3：Volga损耗计算器验证
        
        1. **线性PnL验证**：
           - 蓝色线应该是直线：PnL = Vega × IV变动
           - 斜率 = Vega值
        
        2. **凸性PnL验证**：
           - 红色线应该是曲线（如果Volga ≠ 0）
           - 当Volga < 0时，曲线向下弯曲（损耗）
           - 当Volga > 0时，曲线向上弯曲（增益）
        
        3. **损耗计算验证**：
           - 损耗 = 线性PnL - 凸性PnL
           - 当IV变动较大时，损耗应该更明显
           - 验证"IV降3%时损耗"的数值合理性
        """)
    
    # 加载数据
    df = load_data(db, currency="ETH")
    
    if df.empty:
        st.warning("数据库中没有数据，请先采集数据")
        return
    
    # 标的价格设置
    col1, col2 = st.columns([1, 1])
    with col1:
        # 安全获取标的价格
        default_spot = 3000.0
        if 'underlying_price' in df.columns:
            valid_prices = df['underlying_price'].dropna()
            if len(valid_prices) > 0:
                default_spot = float(valid_prices.iloc[0])
        
        spot_price = st.number_input(
            "当前标的价格",
            min_value=0.0,
            value=default_spot,
            step=10.0,
            help="ETH当前价格"
        )
    with col2:
        risk_free_rate = st.number_input(
            "无风险利率",
            min_value=0.0,
            max_value=0.2,
            value=0.05,
            step=0.01,
            format="%.2f",
            help="年化无风险利率"
        )
    
    # 计算Volga和Vega数据
    with st.spinner("正在计算Volga和Vega数据..."):
        volga_df = prepare_volga_data(df, spot_price, risk_free_rate)
    
    if volga_df.empty:
        st.error("无法计算Volga数据，请检查数据完整性")
        return
    
    # 显示三个模块
    st.divider()
    render_volga_vega_scatter(volga_df)
    
    st.divider()
    render_iv_vega_heatmap(volga_df, spot_price)
    
    st.divider()
    render_volga_loss_calculator(volga_df, spot_price)
    
    st.divider()
    render_strategy_recommender(volga_df, spot_price, risk_free_rate)
    
    # 数据表格（可选）
    with st.expander("📋 查看计算数据"):
        display_cols = ['instrument_name', 'strike', 'option_type', 'expiration_date', 
                      'mark_iv', 'vega', 'volga', 'open_interest', 'iv_percentile']
        available_cols = [col for col in display_cols if col in volga_df.columns]
        st.dataframe(volga_df[available_cols], width='stretch')


def scan_long_vol_convexity_strategies(df: pd.DataFrame, spot_price: float, 
                                       price_change_pct: float, iv_change_pct: float,
                                       min_volga: float = 0.0, max_vega: float = 1000.0,
                                       max_iv_percentile: float = 80.0) -> List[Dict]:
    """
    扫描做多波动率凸性策略（Long Vol Convexity）
    寻找Volga>0且Vega相对合理的Long Straddle/Strangle组合
    
    :param df: 包含所有Greeks的数据
    :param spot_price: 当前标的价格
    :param price_change_pct: 价格变动百分比
    :param iv_change_pct: IV变动百分比
    :param min_volga: 最小Volga阈值
    :param max_vega: 最大Vega阈值
    :param max_iv_percentile: 最大IV百分位（避免高估）
    :return: 推荐策略列表
    """
    strategies = []
    
    # 计算PnL
    plot_df = calculate_full_pnl(df.copy(), spot_price, price_change_pct, iv_change_pct)
    
    # 按到期日分组
    for exp_date, exp_group in plot_df.groupby('expiration_date'):
        # 筛选符合条件的合约
        candidates = exp_group[
            (exp_group['volga'] > min_volga) &
            (exp_group['vega'] <= max_vega) &
            (exp_group['vega'] > 0) &
            (exp_group.get('iv_percentile', pd.Series([50] * len(exp_group))) <= max_iv_percentile)
        ].copy()
        
        if len(candidates) < 2:
            continue
        
        # 寻找Long Straddle（ATM Call + ATM Put）
        atm_strikes = candidates[candidates['strike'].abs() - spot_price < spot_price * 0.05]  # ATM范围：±5%
        
        for strike in atm_strikes['strike'].unique():
            call_candidates = candidates[(candidates['strike'] == strike) & (candidates['option_type'] == 'C')]
            put_candidates = candidates[(candidates['strike'] == strike) & (candidates['option_type'] == 'P')]
            
            if len(call_candidates) > 0 and len(put_candidates) > 0:
                call = call_candidates.iloc[0]
                put = put_candidates.iloc[0]
                
                # 计算组合Greeks和PnL
                portfolio = PortfolioAnalyzer()
                portfolio.current_spot_price = spot_price
                
                # 添加持仓
                call_iv = call.get('mark_iv_decimal', call.get('mark_iv', 0.5))
                if call_iv > 1.0:
                    call_iv = call_iv / 100.0
                put_iv = put.get('mark_iv_decimal', put.get('mark_iv', 0.5))
                if put_iv > 1.0:
                    put_iv = put_iv / 100.0
                
                portfolio.add_position(
                    expiration_date=str(exp_date)[:10],
                    strike=strike,
                    option_type='C',
                    quantity=1,
                    volatility=call_iv
                )
                portfolio.add_position(
                    expiration_date=str(exp_date)[:10],
                    strike=strike,
                    option_type='P',
                    quantity=1,
                    volatility=put_iv
                )
                
                # 计算组合Greeks
                greeks = portfolio.calculate_portfolio_greeks(spot_price)
                
                # 计算组合PnL
                combo_pnl = call['pnl_total'] + put['pnl_total']
                
                strategies.append({
                    'strategy_type': 'Long Straddle',
                    'expiration_date': str(exp_date)[:10],
                    'strike': strike,
                    'legs': [
                        {'type': 'C', 'strike': strike, 'quantity': 1, 'instrument': safe_get_instrument_name(call)},
                        {'type': 'P', 'strike': strike, 'quantity': 1, 'instrument': safe_get_instrument_name(put)}
                    ],
                    'greeks': greeks,
                    'pnl_total': combo_pnl,
                    'pnl_vol_total': call['pnl_vol_total'] + put['pnl_vol_total'],
                    'pnl_vol_volga': call['pnl_vol_volga'] + put['pnl_vol_volga'],
                    'score': combo_pnl + greeks.get('volga', 0) * 10  # 评分：PnL + Volga加权
                })
        
        # 寻找Long Strangle（OTM Call + OTM Put）
        otm_calls = candidates[(candidates['strike'] > spot_price * 1.02) & (candidates['option_type'] == 'C')]
        otm_puts = candidates[(candidates['strike'] < spot_price * 0.98) & (candidates['option_type'] == 'P')]
        
        for call_strike in otm_calls['strike'].unique()[:3]:  # 限制数量
            for put_strike in otm_puts['strike'].unique()[:3]:
                call_candidates = otm_calls[otm_calls['strike'] == call_strike]
                put_candidates = otm_puts[otm_puts['strike'] == put_strike]
                
                if len(call_candidates) > 0 and len(put_candidates) > 0:
                    call = call_candidates.iloc[0]
                    put = put_candidates.iloc[0]
                    
                    portfolio = PortfolioAnalyzer()
                    portfolio.current_spot_price = spot_price
                    
                    call_iv = call.get('mark_iv_decimal', call.get('mark_iv', 0.5))
                    if call_iv > 1.0:
                        call_iv = call_iv / 100.0
                    put_iv = put.get('mark_iv_decimal', put.get('mark_iv', 0.5))
                    if put_iv > 1.0:
                        put_iv = put_iv / 100.0
                    
                    portfolio.add_position(str(exp_date)[:10], call_strike, 'C', 1, volatility=call_iv)
                    portfolio.add_position(str(exp_date)[:10], put_strike, 'P', 1, volatility=put_iv)
                    
                    greeks = portfolio.calculate_portfolio_greeks(spot_price)
                    combo_pnl = call['pnl_total'] + put['pnl_total']
                    
                    strategies.append({
                        'strategy_type': 'Long Strangle',
                        'expiration_date': str(exp_date)[:10],
                        'strike': f"{put_strike:.0f}/{call_strike:.0f}",
                        'legs': [
                            {'type': 'C', 'strike': call_strike, 'quantity': 1, 'instrument': safe_get_instrument_name(call)},
                            {'type': 'P', 'strike': put_strike, 'quantity': 1, 'instrument': safe_get_instrument_name(put)}
                        ],
                        'greeks': greeks,
                        'pnl_total': combo_pnl,
                        'pnl_vol_total': call['pnl_vol_total'] + put['pnl_vol_total'],
                        'pnl_vol_volga': call['pnl_vol_volga'] + put['pnl_vol_volga'],
                        'score': combo_pnl + greeks.get('volga', 0) * 10
                    })
    
    # 按评分排序
    strategies.sort(key=lambda x: x['score'], reverse=True)
    return strategies[:10]  # 返回Top 10


def scan_vol_arbitrage_strategies(df: pd.DataFrame, spot_price: float,
                                  price_change_pct: float, iv_change_pct: float) -> List[Dict]:
    """
    扫描波动率套利策略
    买入高Volga(被低估) + 卖出低Volga(被高估)的对冲组合
    
    :param df: 包含所有Greeks的数据
    :param spot_price: 当前标的价格
    :param price_change_pct: 价格变动百分比
    :param iv_change_pct: IV变动百分比
    :return: 推荐策略列表
    """
    strategies = []
    
    plot_df = calculate_full_pnl(df.copy(), spot_price, price_change_pct, iv_change_pct)
    
    # 按到期日分组
    for exp_date, exp_group in plot_df.groupby('expiration_date'):
        # 寻找高Volga低IV（被低估）的合约
        undervalued = exp_group[
            (exp_group['volga'] > exp_group['volga'].quantile(0.7)) &
            (exp_group.get('iv_percentile', pd.Series([50] * len(exp_group))) < 50)
        ].copy()
        
        # 寻找低Volga高IV（被高估）的合约
        overvalued = exp_group[
            (exp_group['volga'] < exp_group['volga'].quantile(0.3)) &
            (exp_group.get('iv_percentile', pd.Series([50] * len(exp_group))) > 50)
        ].copy()
        
        if len(undervalued) == 0 or len(overvalued) == 0:
            continue
        
        # 尝试配对
        for _, buy_leg in undervalued.head(5).iterrows():
            for _, sell_leg in overvalued.head(5).iterrows():
                # 确保是同一类型（Call或Put）
                if buy_leg['option_type'] != sell_leg['option_type']:
                    continue
                
                portfolio = PortfolioAnalyzer()
                portfolio.current_spot_price = spot_price
                
                buy_iv = buy_leg.get('mark_iv_decimal', buy_leg.get('mark_iv', 0.5))
                if buy_iv > 1.0:
                    buy_iv = buy_iv / 100.0
                sell_iv = sell_leg.get('mark_iv_decimal', sell_leg.get('mark_iv', 0.5))
                if sell_iv > 1.0:
                    sell_iv = sell_iv / 100.0
                
                portfolio.add_position(str(exp_date)[:10], buy_leg['strike'], buy_leg['option_type'], 1, volatility=buy_iv)
                portfolio.add_position(str(exp_date)[:10], sell_leg['strike'], sell_leg['option_type'], -1, volatility=sell_iv)
                
                greeks = portfolio.calculate_portfolio_greeks(spot_price)
                
                # 检查Delta和Vega是否接近中性
                if abs(greeks['delta']) > 0.3 or abs(greeks['vega']) > 50:
                    continue
                
                combo_pnl = buy_leg['pnl_total'] - sell_leg['pnl_total']  # 买入-卖出
                
                strategies.append({
                    'strategy_type': 'Vol Arbitrage',
                    'expiration_date': str(exp_date)[:10],
                    'strike': f"{buy_leg['strike']:.0f}/{sell_leg['strike']:.0f}",
                    'legs': [
                        {'type': buy_leg['option_type'], 'strike': buy_leg['strike'], 'quantity': 1, 
                         'instrument': safe_get_instrument_name(buy_leg), 'volga': buy_leg['volga']},
                        {'type': sell_leg['option_type'], 'strike': sell_leg['strike'], 'quantity': -1,
                         'instrument': safe_get_instrument_name(sell_leg), 'volga': sell_leg['volga']}
                    ],
                    'greeks': greeks,
                    'pnl_total': combo_pnl,
                    'pnl_vol_total': buy_leg['pnl_vol_total'] - sell_leg['pnl_vol_total'],
                    'pnl_vol_volga': buy_leg['pnl_vol_volga'] - sell_leg['pnl_vol_volga'],
                    'score': combo_pnl + greeks.get('volga', 0) * 10
                })
    
    strategies.sort(key=lambda x: x['score'], reverse=True)
    return strategies[:10]


def render_strategy_recommender(df: pd.DataFrame, spot_price: float, risk_free_rate: float):
    """
    模块4：智能策略推荐引擎
    基于Volga/Vega/PnL分析，推荐可交易的期权组合策略
    
    :param df: 包含所有Greeks的数据
    :param spot_price: 当前标的价格
    :param risk_free_rate: 无风险利率
    """
    st.subheader("🎯 模块4：智能策略推荐引擎（Smart Strategy Recommender）")
    st.caption("基于Volga/Vega特征，自动扫描并推荐可交易的期权组合策略")
    
    # 详细使用指南
    with st.expander("📖 完整使用指南", expanded=True):
        st.markdown("""
        ### 🎯 推荐策略的考虑因素
        
        **1. 评分机制**：
        - **评分 = 预期总PnL + Volga × 10**
        - 评分越高，策略越优
        - 同时考虑收益（PnL）和凸性优势（Volga）
        
        **2. 筛选条件**：
        - **最小Volga**：确保策略具有凸性优势（Volga > 0）
        - **最大Vega**：控制波动率敞口，避免过度暴露
        - **最大IV百分位**：避免买入被高估的期权（IV百分位过高）
        
        **3. 策略特征**：
        - **Long Straddle/Strangle**：适合预期波动率大幅波动
        - **Vol Arbitrage**：适合波动率定价存在偏差时
        - 所有策略都基于**当前市场快照**和**您设定的预期情景**（价格变动、IV变动）
        
        ### 📋 使用步骤
        
        **步骤1：设置预期情景**
        - 调整"预期价格变动"和"预期IV变动"滑杆
        - 这决定了推荐策略的收益预期
        - 例如：如果预期IV下降3%，设置IV变动为-3%
        
        **步骤2：选择策略类型**
        - **做多波动率凸性**：适合预期波动率大幅波动
        - **波动率套利**：适合寻找定价偏差机会
        
        **步骤3：调整筛选条件（可选）**
        - 根据您的风险偏好调整筛选条件
        - 默认值已优化，通常无需修改
        
        **步骤4：查看推荐策略**
        - 查看Top 10推荐策略
        - 重点关注：
          - **评分**：综合收益和凸性优势
          - **组合Greeks**：Delta、Vega、Volga等风险指标
          - **PnL分析**：预期收益来源（价格/波动率/Volga）
        
        **步骤5：选择并执行**
        - 选择您感兴趣的策略
        - **记录组合详情**（合约名称、行权价、数量）
        - **在交易所手动开仓**
        - **开仓后，使用"Volga持仓跟踪"页面监控**
        
        ### ⚠️ 重要提示
        
        1. **推荐基于理论计算**：实际交易需考虑：
           - 交易成本和滑点
           - 流动性（OI和成交量）
           - 市场冲击
           - 时间衰减（Theta）
        
        2. **情景假设**：推荐基于您设定的价格/IV变动假设，实际市场可能不同
        
        3. **风险管理**：建议：
           - 从小仓位开始测试
           - 设置止损点
           - 定期监控和调整
        
        4. **验证闭环**：
           - 开仓后 → 在"Volga持仓跟踪"页面录入持仓
           - 定期查看风险敞口和PnL归因
           - 根据调整建议优化持仓
           - 验证Volga分析的实际效果
        """)
    
    with st.expander("📚 策略类型详解", expanded=False):
        st.markdown("""
        **1. 做多波动率凸性 (Long Vol Convexity)**：
        - **Long Straddle**: ATM Call + ATM Put（同一行权价）
        - **Long Strangle**: OTM Call + OTM Put（不同行权价）
        - **适用场景**：预期波动率大幅波动（无论方向）
        - **特点**: Volga > 0，IV大幅波动时收益放大
        - **风险**：时间衰减（Theta为负），需要IV大幅波动才能盈利
        
        **2. 波动率套利 (Vol Arbitrage)**：
        - 买入高Volga低IV（被低估）+ 卖出低Volga高IV（被高估）
        - **适用场景**：发现波动率定价偏差
        - **特点**: Delta和Vega接近中性，保留Volga优势
        - **风险**：需要准确识别定价偏差，偏差消失时需及时平仓
        
        **3. 评分说明**：
        - **评分 = 预期总PnL + Volga × 10**
        - 评分越高，策略越优
        - Volga权重为10，强调凸性优势的重要性
        """)
    
    # 检查必要列
    required_greeks = ['delta', 'gamma', 'vega', 'volga', 'vanna']
    missing_greeks = [g for g in required_greeks if g not in df.columns]
    if missing_greeks:
        st.warning(f"缺少必要的Greeks列: {missing_greeks}")
        return
    
    if df.empty:
        st.warning("没有有效数据")
        return
    
    # 策略类型选择
    st.write("**📋 步骤2：选择策略类型**")
    strategy_types = st.multiselect(
        "选择要扫描的策略类型",
        ["做多波动率凸性 (Long Vol Convexity)", "波动率套利 (Vol Arbitrage)"],
        default=["做多波动率凸性 (Long Vol Convexity)"],
        help="选择一种或多种策略类型进行扫描。做多波动率凸性适合预期IV大幅波动，波动率套利适合寻找定价偏差"
    )
    
    if not strategy_types:
        st.info("请至少选择一种策略类型")
        return
    
    # 情景设置（复用模块2的设置）
    st.write("**🎛️ 步骤1：设置预期情景**")
    st.caption("调整预期价格和IV变动，这将决定推荐策略的收益预期")
    
    col1, col2 = st.columns(2)
    with col1:
        price_change_pct = st.slider(
            "预期价格变动 (%)",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            key="strategy_price_change",
            help="例如：+5%表示预期价格上涨5%，-5%表示预期价格下跌5%"
        )
    with col2:
        iv_change_pct = st.slider(
            "预期IV变动 (%)",
            min_value=-10.0,
            max_value=10.0,
            value=-3.0,
            step=0.5,
            key="strategy_iv_change",
            help="例如：-3%表示预期IV下降3%（IV压缩），+5%表示预期IV上升5%（IV扩张）"
        )
    
    st.info(f"💡 **当前情景假设**：价格变动 **{price_change_pct:+.1f}%**，IV变动 **{iv_change_pct:+.1f}%**。"
           f"推荐策略将基于此情景计算预期收益。")
    
    # 筛选条件
    st.write("**🔧 步骤3：调整筛选条件（可选）**")
    with st.expander("高级筛选条件", expanded=False):
        st.caption("根据您的风险偏好调整筛选条件。默认值已优化，通常无需修改。")
        col1, col2, col3 = st.columns(3)
        with col1:
            min_volga = st.number_input(
                "最小Volga", 
                value=0.0, 
                step=10.0,
                help="只推荐Volga大于此值的策略，确保具有凸性优势"
            )
        with col2:
            max_vega = st.number_input(
                "最大Vega", 
                value=1000.0, 
                step=100.0,
                help="限制最大Vega敞口，避免过度暴露于波动率风险"
            )
        with col3:
            max_iv_percentile = st.number_input(
                "最大IV百分位", 
                value=80.0, 
                step=5.0,
                help="避免买入IV百分位过高的期权（可能被高估）"
            )
    
    # 扫描策略
    all_strategies = []
    
    if "做多波动率凸性 (Long Vol Convexity)" in strategy_types:
        with st.spinner("正在扫描做多波动率凸性策略..."):
            strategies = scan_long_vol_convexity_strategies(
                df, spot_price, price_change_pct, iv_change_pct,
                min_volga, max_vega, max_iv_percentile
            )
            all_strategies.extend(strategies)
    
    if "波动率套利 (Vol Arbitrage)" in strategy_types:
        with st.spinner("正在扫描波动率套利策略..."):
            strategies = scan_vol_arbitrage_strategies(
                df, spot_price, price_change_pct, iv_change_pct
            )
            all_strategies.extend(strategies)
    
    if not all_strategies:
        st.warning("未找到符合条件的策略组合。请尝试调整筛选条件。")
        return
    
    # 按评分排序
    all_strategies.sort(key=lambda x: x['score'], reverse=True)
    
    # 显示推荐策略
    st.subheader(f"📊 步骤4：查看推荐策略（共{len(all_strategies)}个，显示Top 10）")
    st.caption("策略按评分排序，评分 = 预期总PnL + Volga × 10。评分越高，策略越优。")
    
    # 显示评分说明
    st.info("💡 **评分说明**：评分 = 预期总PnL + Volga × 10。"
           "评分同时考虑了收益（PnL）和凸性优势（Volga），评分越高表示策略在您设定的情景下表现越好。")
    
    for idx, strategy in enumerate(all_strategies[:10], 1):
        # 计算风险等级
        greeks = strategy['greeks']
        risk_level = "低"
        risk_color = "🟢"
        if abs(greeks.get('delta', 0)) > 0.3:
            risk_level = "中"
            risk_color = "🟡"
        if abs(greeks.get('vega', 0)) > 500:
            risk_level = "高"
            risk_color = "🔴"
        
        with st.expander(
            f"{risk_color} 策略 #{idx}: {strategy['strategy_type']} - {strategy['strike']} "
            f"({strategy['expiration_date']}) | 评分: {strategy['score']:.2f} | 风险: {risk_level}", 
            expanded=(idx <= 3)
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write("**📋 组合详情（请记录这些信息用于开仓）**")
                
                # 构建代码块内容并一次性显示
                code_lines = []
                for leg in strategy['legs']:
                    sign = "+" if leg['quantity'] > 0 else ""
                    code_lines.append(f"{sign}{leg['quantity']} {leg['type']} {leg['strike']:.0f}")
                    code_lines.append(f"  合约: {leg['instrument']}")
                    if 'volga' in leg:
                        code_lines.append(f"  Volga: {leg['volga']:.2f}")
                
                st.code("\n".join(code_lines), language="text")
                
                st.write("**💰 PnL分析（基于当前情景假设）**")
                col_pnl1, col_pnl2 = st.columns(2)
                with col_pnl1:
                    st.metric("预期总PnL", f"{strategy['pnl_total']:.2f}")
                    st.metric("波动率贡献", f"{strategy['pnl_vol_total']:.2f}")
                with col_pnl2:
                    st.metric("Volga贡献", f"{strategy['pnl_vol_volga']:.2f}", 
                            delta="凸性优势" if strategy['pnl_vol_volga'] > 0 else "凸性劣势")
                    st.metric("价格贡献", f"{strategy['pnl_total'] - strategy['pnl_vol_total']:.2f}")
                
                # 解释PnL来源
                if strategy['pnl_vol_volga'] > 0:
                    st.success(f"✅ **Volga贡献为正** ({strategy['pnl_vol_volga']:.2f})，说明该策略具有凸性优势。"
                             f"当IV变化时，收益会放大（非线性效应）。")
                elif strategy['pnl_vol_volga'] < 0:
                    st.warning(f"⚠️ **Volga贡献为负** ({strategy['pnl_vol_volga']:.2f})，"
                             f"说明该策略具有凹性特征。IV变化时收益可能低于线性预期。")
            
            with col2:
                st.write("**📊 组合Greeks（风险指标）**")
                st.metric("Delta", f"{greeks['delta']:.4f}", 
                         delta="价格方向性" if abs(greeks['delta']) > 0.1 else "接近中性")
                st.metric("Gamma", f"{greeks['gamma']:.6f}")
                st.metric("Vega", f"{greeks['vega']:.2f}",
                         delta="波动率敞口" if abs(greeks['vega']) > 100 else "低敞口")
                st.metric("Volga", f"{greeks.get('volga', 0):.2f}",
                         delta="凸性敞口" if greeks.get('volga', 0) > 0 else "凹性敞口")
                st.metric("Vanna", f"{greeks.get('vanna', 0):.6f}")
                st.metric("**评分**", f"**{strategy['score']:.2f}**",
                         delta=f"排名 #{idx}")
            
            # 使用建议
            st.write("**📝 执行步骤**")
            st.write("1. **记录组合详情**：复制上面的合约信息（行权价、类型、数量）")
            st.write("2. **在交易所开仓**：按照组合详情手动开仓")
            st.write("3. **录入持仓**：开仓后，前往\"Volga持仓跟踪\"页面录入您的持仓")
            st.write("4. **监控调整**：定期查看风险敞口和PnL归因，根据调整建议优化持仓")
    
    st.divider()
    
    # 最终使用建议
    st.subheader("✅ 步骤5：执行和验证")
    st.markdown("""
    **执行清单**：
    
    1. ✅ **选择策略**：从推荐列表中选择您感兴趣的策略（建议选择评分高、风险等级低的策略）
    
    2. ✅ **记录详情**：记录组合的每个腿（合约名称、行权价、类型、数量）
    
    3. ✅ **在交易所开仓**：
       - 按照组合详情手动开仓
       - 注意交易成本和滑点
       - 建议从小仓位开始测试
    
    4. ✅ **录入持仓**：
       - 开仓后，前往 **\"Volga持仓跟踪\"** 页面
       - 手动录入您的持仓（或从数据库选择）
       - 系统会自动计算实时风险敞口
    
    5. ✅ **监控和调整**：
       - 定期查看Net Volga、Net Vanna等风险指标
       - 查看PnL归因分析，了解收益来源
       - 根据调整建议优化持仓
    
    6. ✅ **验证效果**：
       - 对比实际收益与理论预期
       - 验证Volga分析模块的准确性
       - 积累经验，优化策略选择
    """)
    
    st.warning("⚠️ **风险提示**：推荐策略基于理论计算和您设定的情景假设。实际交易需考虑交易成本、流动性、市场冲击等因素。"
              "建议从小仓位开始，设置止损点，并定期监控和调整。")

