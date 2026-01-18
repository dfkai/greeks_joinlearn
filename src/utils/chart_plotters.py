"""
图表绘制模块
包含所有Plotly图表绘制函数
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
try:
    from scipy.interpolate import make_interp_spline
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def get_sorted_unique_dates(series):
    """
    安全地获取并排序唯一的日期列表，过滤掉NaT值
    
    :param series: pandas Series，包含日期数据
    :return: 排序后的唯一日期列表
    """
    if series is None or series.empty:
        return []
    dates = pd.to_datetime(series).dt.date
    # 过滤掉NaT值并排序
    unique_dates = sorted([d for d in dates.unique() if pd.notna(d)])
    return unique_dates


def plot_all_greeks_cross_section(df: pd.DataFrame, greeks_params: list, expiration_dates: list):
    """
    绘制所有选中的Greeks参数截面分析图表（多子图模式）
    
    :param df: 准备好的数据（包含expiration_date列）
    :param greeks_params: Greeks参数列表
    :param expiration_dates: 到期日列表
    """
    if df.empty:
        st.warning("没有数据可显示")
        return
    
    # 维度标签（支持Greeks和非Greeks）- 必须在函数开头定义
    dimension_labels = {
        # Greeks参数
        'delta': 'Delta',
        'gamma': 'Gamma',
        'theta': 'Theta',
        'vega': 'Vega',
        'rho': 'Rho',
        # 非Greeks维度
        'mark_iv': 'IV (隐含波动率)',
        'mark_price': '期权价格 (USD)',
        'open_interest': '持仓量',
        'volume': '成交量'
    }
    
    # 检查哪些维度参数有数据，哪些全为NaN
    missing_data_params = []
    for param in greeks_params:
        if param not in df.columns:
            missing_data_params.append(f"{dimension_labels.get(param, param)}（字段不存在）")
        elif df[param].isna().all():
            missing_data_params.append(f"{dimension_labels.get(param, param)}（数据全为空）")
    
    if missing_data_params:
        st.warning(f"⚠️ 以下维度没有可用数据，将不会显示：{', '.join(missing_data_params)}")
    
    # 确保expiration_dates是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    
    num_greeks = len(greeks_params)
    
    # 创建子图
    fig = make_subplots(
        rows=num_greeks, 
        cols=1,
        subplot_titles=[f'{dimension_labels.get(greeks_params[i], greeks_params[i])} vs 行权价' for i in range(num_greeks)],
        shared_xaxes=True,  # 共享X轴
        vertical_spacing=0.05,  # 子图间距
        row_heights=[1] * num_greeks  # 每个子图等高
    )
    
    # 获取颜色方案
    call_colors = px.colors.qualitative.Set1[:5]
    put_colors = px.colors.qualitative.Pastel[:5]
    
    # 获取唯一的到期日
    unique_exp_dates = get_sorted_unique_dates(df['expiration_date']) if 'expiration_date' in df.columns else []
    
    # 为每个Greeks参数创建子图
    for greek_idx, greeks_param in enumerate(greeks_params):
        row_num = greek_idx + 1
        
        # 为每个到期日绘制数据
        for exp_idx, exp_date in enumerate(unique_exp_dates):
            exp_df = df[df['expiration_date'].dt.date == exp_date].copy()
            
            if exp_df.empty or greeks_param not in exp_df.columns:
                continue
            
            # 检查该维度参数是否全为NaN
            if exp_df[greeks_param].isna().all():
                # 如果全为NaN，跳过这个到期日的数据
                continue
            
            # 分离Call和Put期权
            if 'option_type' in exp_df.columns:
                call_df = exp_df[exp_df['option_type'] == 'C'].copy()
                put_df = exp_df[exp_df['option_type'] == 'P'].copy()
                
                # 判断是否使用柱状图（成交量或持仓量）
                use_bar_chart = greeks_param in ['volume', 'open_interest']
                
                # 绘制Call期权
                if not call_df.empty:
                    # 检查Call数据是否全为NaN
                    if call_df[greeks_param].isna().all():
                        # 跳过全为NaN的数据
                        pass
                    else:
                        exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
                        show_legend = (greek_idx == 0)  # 只在第一个子图显示图例
                        
                        if use_bar_chart:
                            # 使用柱状图（成交量、持仓量）
                            # 过滤掉NaN值，并按strike排序
                            call_df_valid = call_df.dropna(subset=[greeks_param]).sort_values('strike')
                            # 只显示非零值，避免显示大量零值柱状图
                            call_df_nonzero = call_df_valid[call_df_valid[greeks_param] > 0].copy()
                            if not call_df_nonzero.empty:
                                fig.add_trace(go.Bar(
                                    x=call_df_nonzero['strike'],
                                    y=call_df_nonzero[greeks_param],
                                    name=f'Call {exp_date_str}',
                                    marker_color=call_colors[exp_idx % len(call_colors)],
                                    opacity=0.7,
                                    showlegend=show_legend,
                                    legendgroup=f'call_{exp_date_str}',
                                    hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                '行权价: %{x}<br>' +
                                                f'{greeks_param}: %{{y:.0f}}<br>' +
                                                '<extra></extra>'
                                ), row=row_num, col=1)
                        else:
                            # 使用折线图（Delta、IV等连续数据）
                            # 过滤掉NaN值，并按strike排序
                            call_df_valid = call_df.dropna(subset=[greeks_param]).sort_values('strike')
                            if not call_df_valid.empty:
                                x_data = call_df_valid['strike'].values
                                y_data = call_df_valid[greeks_param].values
                                
                                # 如果数据点>=3个且scipy可用，使用spline平滑
                                if len(x_data) >= 3 and HAS_SCIPY:
                                    try:
                                        x_smooth = np.linspace(x_data.min(), x_data.max(), max(100, len(x_data) * 3))
                                        spline = make_interp_spline(x_data, y_data, k=min(3, len(x_data)-1))
                                        y_smooth = spline(x_smooth)
                                        
                                        fig.add_trace(go.Scatter(
                                            x=x_smooth,
                                            y=y_smooth,
                                            mode='lines',
                                            name=f'Call {exp_date_str}',
                                            line=dict(color=call_colors[exp_idx % len(call_colors)], width=2.5),
                                            showlegend=show_legend,
                                            legendgroup=f'call_{exp_date_str}',
                                            hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                        '行权价: %{x:.0f}<br>' +
                                                        f'{greeks_param}: %{{y:.4f}}<br>' +
                                                        '<extra></extra>'
                                        ), row=row_num, col=1)
                                    except Exception:
                                        # 如果spline失败，使用线性连接
                                        fig.add_trace(go.Scatter(
                                            x=x_data,
                                            y=y_data,
                                            mode='lines+markers',
                                            name=f'Call {exp_date_str}',
                                            line=dict(color=call_colors[exp_idx % len(call_colors)], width=2, shape='linear'),
                                            marker=dict(size=4, opacity=0.6),
                                            connectgaps=False,
                                            showlegend=show_legend,
                                            legendgroup=f'call_{exp_date_str}',
                                            hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                        '行权价: %{x:.0f}<br>' +
                                                        f'{greeks_param}: %{{y:.4f}}<br>' +
                                                        '<extra></extra>'
                                        ), row=row_num, col=1)
                                else:
                                    # 数据点太少或scipy不可用，直接绘制
                                    fig.add_trace(go.Scatter(
                                        x=x_data,
                                        y=y_data,
                                        mode='lines+markers',
                                        name=f'Call {exp_date_str}',
                                        line=dict(color=call_colors[exp_idx % len(call_colors)], width=2, shape='linear'),
                                        marker=dict(size=4, opacity=0.6),
                                        connectgaps=False,
                                        showlegend=show_legend,
                                        legendgroup=f'call_{exp_date_str}',
                                        hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                    '行权价: %{x:.0f}<br>' +
                                                    f'{greeks_param}: %{{y:.4f}}<br>' +
                                                    '<extra></extra>'
                                    ), row=row_num, col=1)
                
                # 绘制Put期权
                if not put_df.empty:
                    # 检查Put数据是否全为NaN
                    if not put_df[greeks_param].isna().all():
                        exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
                        show_legend = (greek_idx == 0)
                        
                        if use_bar_chart:
                            # 使用柱状图（成交量、持仓量）
                            # 过滤掉NaN值，并按strike排序
                            put_df_valid = put_df.dropna(subset=[greeks_param]).sort_values('strike')
                            # 只显示非零值，避免显示大量零值柱状图
                            put_df_nonzero = put_df_valid[put_df_valid[greeks_param] > 0].copy()
                            if not put_df_nonzero.empty:
                                fig.add_trace(go.Bar(
                                    x=put_df_nonzero['strike'],
                                    y=put_df_nonzero[greeks_param],
                                    name=f'Put {exp_date_str}',
                                    marker_color=put_colors[exp_idx % len(put_colors)],
                                    opacity=0.7,
                                    showlegend=show_legend,
                                    legendgroup=f'put_{exp_date_str}',
                                    hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                '行权价: %{x}<br>' +
                                                f'{greeks_param}: %{{y:.0f}}<br>' +
                                                '<extra></extra>'
                                ), row=row_num, col=1)
                        else:
                            # 使用折线图（Delta、IV等连续数据）
                            # 过滤掉NaN值，并按strike排序
                            put_df_valid = put_df.dropna(subset=[greeks_param]).sort_values('strike')
                            if not put_df_valid.empty:
                                x_data = put_df_valid['strike'].values
                                y_data = put_df_valid[greeks_param].values
                                
                                # 如果数据点>=3个且scipy可用，使用spline平滑
                                if len(x_data) >= 3 and HAS_SCIPY:
                                    try:
                                        x_smooth = np.linspace(x_data.min(), x_data.max(), max(100, len(x_data) * 3))
                                        spline = make_interp_spline(x_data, y_data, k=min(3, len(x_data)-1))
                                        y_smooth = spline(x_smooth)
                                        
                                        fig.add_trace(go.Scatter(
                                            x=x_smooth,
                                            y=y_smooth,
                                            mode='lines',
                                            name=f'Put {exp_date_str}',
                                            line=dict(color=put_colors[exp_idx % len(put_colors)], width=2.5, dash='dash'),
                                            showlegend=show_legend,
                                            legendgroup=f'put_{exp_date_str}',
                                            hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                        '行权价: %{x:.0f}<br>' +
                                                        f'{greeks_param}: %{{y:.4f}}<br>' +
                                                        '<extra></extra>'
                                        ), row=row_num, col=1)
                                    except Exception:
                                        # 如果spline失败，使用线性连接
                                        fig.add_trace(go.Scatter(
                                            x=x_data,
                                            y=y_data,
                                            mode='lines+markers',
                                            name=f'Put {exp_date_str}',
                                            line=dict(color=put_colors[exp_idx % len(put_colors)], width=2, dash='dash', shape='linear'),
                                            marker=dict(size=4, opacity=0.6),
                                            connectgaps=False,
                                            showlegend=show_legend,
                                            legendgroup=f'put_{exp_date_str}',
                                            hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                        '行权价: %{x:.0f}<br>' +
                                                        f'{greeks_param}: %{{y:.4f}}<br>' +
                                                        '<extra></extra>'
                                        ), row=row_num, col=1)
                                else:
                                    # 数据点太少或scipy不可用，直接绘制
                                    fig.add_trace(go.Scatter(
                                        x=x_data,
                                        y=y_data,
                                        mode='lines+markers',
                                        name=f'Put {exp_date_str}',
                                        line=dict(color=put_colors[exp_idx % len(put_colors)], width=2, dash='dash', shape='linear'),
                                        marker=dict(size=4, opacity=0.6),
                                        connectgaps=False,
                                        showlegend=show_legend,
                                        legendgroup=f'put_{exp_date_str}',
                                        hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                    '行权价: %{x:.0f}<br>' +
                                                    f'{greeks_param}: %{{y:.4f}}<br>' +
                                                    '<extra></extra>'
                                    ), row=row_num, col=1)
        
        # 更新Y轴标签
        fig.update_yaxes(title_text=dimension_labels.get(greeks_param, greeks_param), row=row_num, col=1)
    
    # 更新X轴标签（只在最后一个子图）
    fig.update_xaxes(title_text='行权价 (Strike Price)', row=num_greeks, col=1)
    
    # 构建标题
    if len(unique_exp_dates) == 1:
        title = f'维度分析 - 截面视图 (到期日: {unique_exp_dates[0]})'
    else:
        title = f'维度分析 - 截面视图 (对比 {len(unique_exp_dates)} 个到期日)'
    
    # 更新整体布局
    fig.update_layout(
        title=title,
        hovermode='closest',
        template='plotly_white',
        height=350 * num_greeks,  # 根据子图数量调整高度
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 显示图表
    st.plotly_chart(fig, width='stretch')


def plot_cross_section_chart(df: pd.DataFrame, greeks_param: str, expiration_dates: list):
    """
    绘制截面分析图表（支持多个到期日对比）
    
    :param df: 准备好的数据（包含expiration_date列）
    :param greeks_param: Greeks参数名称
    :param expiration_dates: 到期日列表
    """
    if df.empty:
        st.warning("没有数据可显示")
        return
    
    # 检查该维度参数是否有数据
    if greeks_param not in df.columns:
        st.warning(f"数据中不存在 '{greeks_param}' 字段")
        return
    elif df[greeks_param].isna().all():
        dimension_labels = {
            'delta': 'Delta', 'gamma': 'Gamma', 'theta': 'Theta', 'vega': 'Vega', 'rho': 'Rho',
            'mark_iv': 'IV (隐含波动率)', 'mark_price': '期权价格 (USD)',
            'open_interest': '持仓量', 'volume': '成交量'
        }
        dim_label = dimension_labels.get(greeks_param, greeks_param)
        st.warning(f"⚠️ {dim_label} 数据全为空，无法显示图表。可能是数据采集时该字段没有值。")
        return
    
    # 确保expiration_dates是列表
    if not isinstance(expiration_dates, list):
        expiration_dates = [expiration_dates]
    
    # 创建图表
    fig = go.Figure()
    
    # 获取颜色方案
    colors = px.colors.qualitative.Set3
    call_colors = px.colors.qualitative.Set1[:5]  # Call使用蓝色系
    put_colors = px.colors.qualitative.Pastel[:5]  # Put使用粉色系
    
    # 为每个到期日绘制数据（安全处理NaT值）
    unique_exp_dates = get_sorted_unique_dates(df['expiration_date']) if 'expiration_date' in df.columns else []
    
    for exp_idx, exp_date in enumerate(unique_exp_dates):
        exp_df = df[df['expiration_date'].dt.date == exp_date].copy()
        
        if exp_df.empty:
            continue
        
        # 检查该维度参数是否全为NaN
        if greeks_param not in exp_df.columns or exp_df[greeks_param].isna().all():
            continue
        
        # 分离Call和Put期权
        if 'option_type' in exp_df.columns:
            call_df = exp_df[exp_df['option_type'] == 'C'].copy()
            put_df = exp_df[exp_df['option_type'] == 'P'].copy()
            
            # 判断是否使用柱状图（成交量或持仓量）
            use_bar_chart = greeks_param in ['volume', 'open_interest']
            
            # 绘制Call期权
            if not call_df.empty and not call_df[greeks_param].isna().all():
                exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
                
                # 过滤掉NaN值
                call_df_valid = call_df.dropna(subset=[greeks_param])
                
                if not call_df_valid.empty:
                    # 确保按strike排序，保证图表连续性
                    call_df_valid = call_df_valid.sort_values('strike')
                    
                    if use_bar_chart:
                        # 使用柱状图（成交量、持仓量）
                        # 只显示非零值，避免显示大量零值柱状图
                        call_df_nonzero = call_df_valid[call_df_valid[greeks_param] > 0].copy()
                        if not call_df_nonzero.empty:
                            fig.add_trace(go.Bar(
                                x=call_df_nonzero['strike'],
                                y=call_df_nonzero[greeks_param],
                                name=f'Call {exp_date_str}',
                                marker_color=call_colors[exp_idx % len(call_colors)],
                                opacity=0.7,
                                hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                            '行权价: %{x}<br>' +
                                            f'{greeks_param}: %{{y:.0f}}<br>' +
                                            '<extra></extra>'
                            ))
                    else:
                        # 使用折线图（Delta、IV等连续数据）
                        # 如果数据点足够多，使用平滑插值
                        x_data = call_df_valid['strike'].values
                        y_data = call_df_valid[greeks_param].values
                        
                        # 如果数据点>=3个，使用spline平滑
                        if len(x_data) >= 3:
                            try:
                                # 创建平滑的插值曲线
                                x_smooth = np.linspace(x_data.min(), x_data.max(), max(100, len(x_data) * 3))
                                spline = make_interp_spline(x_data, y_data, k=min(3, len(x_data)-1))
                                y_smooth = spline(x_smooth)
                                
                                # 绘制平滑曲线
                                fig.add_trace(go.Scatter(
                                    x=x_smooth,
                                    y=y_smooth,
                                    mode='lines',
                                    name=f'Call {exp_date_str}',
                                    line=dict(
                                        color=call_colors[exp_idx % len(call_colors)], 
                                        width=2.5
                                    ),
                                    hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                '行权价: %{x:.0f}<br>' +
                                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                                '<extra></extra>',
                                    showlegend=True
                                ))
                                
                                # 绘制原始数据点（较小，半透明）
                                fig.add_trace(go.Scatter(
                                    x=x_data,
                                    y=y_data,
                                    mode='markers',
                                    name=f'Call {exp_date_str} (数据点)',
                                    marker=dict(
                                        size=3, 
                                        opacity=0.4,
                                        color=call_colors[exp_idx % len(call_colors)]
                                    ),
                                    hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                '行权价: %{x:.0f}<br>' +
                                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                                '<extra></extra>',
                                    showlegend=False
                                ))
                            except Exception:
                                # 如果spline失败，使用线性连接
                                fig.add_trace(go.Scatter(
                                    x=x_data,
                                    y=y_data,
                                    mode='lines+markers',
                                    name=f'Call {exp_date_str}',
                                    line=dict(
                                        color=call_colors[exp_idx % len(call_colors)], 
                                        width=2,
                                        shape='linear'
                                    ),
                                    marker=dict(size=4, opacity=0.6),
                                    hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                                '行权价: %{x:.0f}<br>' +
                                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                                '<extra></extra>',
                                    connectgaps=False
                                ))
                        else:
                            # 数据点太少，直接绘制
                            fig.add_trace(go.Scatter(
                                x=x_data,
                                y=y_data,
                                mode='lines+markers',
                                name=f'Call {exp_date_str}',
                                line=dict(
                                    color=call_colors[exp_idx % len(call_colors)], 
                                    width=2,
                                    shape='linear'
                                ),
                                marker=dict(size=4, opacity=0.6),
                                hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                            '行权价: %{x:.0f}<br>' +
                                            f'{greeks_param}: %{{y:.4f}}<br>' +
                                            '<extra></extra>',
                                connectgaps=False
                            ))
            
            # 绘制Put期权
            if not put_df.empty and not put_df[greeks_param].isna().all():
                exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
                
                # 过滤掉NaN值
                put_df_valid = put_df.dropna(subset=[greeks_param])
                
                if not put_df_valid.empty:
                    # 确保按strike排序，保证图表连续性
                    put_df_valid = put_df_valid.sort_values('strike')
                    
                    if use_bar_chart:
                        # 使用柱状图（成交量、持仓量）
                        # 只显示非零值，避免显示大量零值柱状图
                        put_df_nonzero = put_df_valid[put_df_valid[greeks_param] > 0].copy()
                        if not put_df_nonzero.empty:
                            fig.add_trace(go.Bar(
                                x=put_df_nonzero['strike'],
                                y=put_df_nonzero[greeks_param],
                                name=f'Put {exp_date_str}',
                                marker_color=put_colors[exp_idx % len(put_colors)],
                                opacity=0.7,
                                hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                            '行权价: %{x}<br>' +
                                            f'{greeks_param}: %{{y:.0f}}<br>' +
                                            '<extra></extra>'
                            ))
                    else:
                        # 使用折线图（Delta、IV等连续数据）
                        # 如果数据点足够多，使用平滑插值
                        x_data = put_df_valid['strike'].values
                        y_data = put_df_valid[greeks_param].values
                        
                        # 如果数据点>=3个，使用spline平滑
                        if len(x_data) >= 3:
                            try:
                                # 创建平滑的插值曲线
                                x_smooth = np.linspace(x_data.min(), x_data.max(), max(100, len(x_data) * 3))
                                spline = make_interp_spline(x_data, y_data, k=min(3, len(x_data)-1))
                                y_smooth = spline(x_smooth)
                                
                                # 绘制平滑曲线
                                fig.add_trace(go.Scatter(
                                    x=x_smooth,
                                    y=y_smooth,
                                    mode='lines',
                                    name=f'Put {exp_date_str}',
                                    line=dict(
                                        color=put_colors[exp_idx % len(put_colors)], 
                                        width=2.5,
                                        dash='dash'
                                    ),
                                    hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                '行权价: %{x:.0f}<br>' +
                                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                                '<extra></extra>',
                                    showlegend=True
                                ))
                                
                                # 绘制原始数据点（较小，半透明）
                                fig.add_trace(go.Scatter(
                                    x=x_data,
                                    y=y_data,
                                    mode='markers',
                                    name=f'Put {exp_date_str} (数据点)',
                                    marker=dict(
                                        size=3, 
                                        opacity=0.4,
                                        color=put_colors[exp_idx % len(put_colors)]
                                    ),
                                    hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                '行权价: %{x:.0f}<br>' +
                                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                                '<extra></extra>',
                                    showlegend=False
                                ))
                            except Exception:
                                # 如果spline失败，使用线性连接
                                fig.add_trace(go.Scatter(
                                    x=x_data,
                                    y=y_data,
                                    mode='lines+markers',
                                    name=f'Put {exp_date_str}',
                                    line=dict(
                                        color=put_colors[exp_idx % len(put_colors)], 
                                        width=2,
                                        dash='dash',
                                        shape='linear'
                                    ),
                                    marker=dict(size=4, opacity=0.6),
                                    hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                                '行权价: %{x:.0f}<br>' +
                                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                                '<extra></extra>',
                                    connectgaps=False
                                ))
                        else:
                            # 数据点太少，直接绘制
                            fig.add_trace(go.Scatter(
                                x=x_data,
                                y=y_data,
                                mode='lines+markers',
                                name=f'Put {exp_date_str}',
                                line=dict(
                                    color=put_colors[exp_idx % len(put_colors)], 
                                    width=2,
                                    dash='dash',
                                    shape='linear'
                                ),
                                marker=dict(size=4, opacity=0.6),
                                hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                            '行权价: %{x:.0f}<br>' +
                                            f'{greeks_param}: %{{y:.4f}}<br>' +
                                            '<extra></extra>',
                                connectgaps=False
                            ))
        else:
            # 如果没有option_type列，绘制所有数据
            exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
            # 确保按strike排序
            exp_df_sorted = exp_df.sort_values('strike')
            
            # 判断是否使用柱状图
            use_bar_chart = greeks_param in ['volume', 'open_interest']
            
            if use_bar_chart:
                # 只显示非零值
                exp_df_nonzero = exp_df_sorted[exp_df_sorted[greeks_param] > 0].copy()
                if not exp_df_nonzero.empty:
                    fig.add_trace(go.Bar(
                        x=exp_df_nonzero['strike'],
                        y=exp_df_nonzero[greeks_param],
                        name=f'{exp_date_str}',
                        marker_color=colors[exp_idx % len(colors)],
                        opacity=0.7
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=exp_df_sorted['strike'],
                    y=exp_df_sorted[greeks_param],
                    mode='lines+markers',
                    name=f'{exp_date_str}',
                    line=dict(color=colors[exp_idx % len(colors)], width=2, shape='linear'),
                    marker=dict(size=4, opacity=0.6),
                    connectgaps=False
                ))
    
    # 更新布局 - 支持Greeks和非Greeks维度
    dimension_labels = {
        # Greeks参数
        'delta': 'Delta',
        'gamma': 'Gamma',
        'theta': 'Theta',
        'vega': 'Vega',
        'rho': 'Rho',
        # 非Greeks维度
        'mark_iv': 'IV (隐含波动率)',
        'mark_price': '期权价格 (USD)',
        'open_interest': '持仓量',
        'volume': '成交量'
    }
    
    # 构建标题
    dim_label = dimension_labels.get(greeks_param, greeks_param)
    if len(unique_exp_dates) == 1:
        title = f'{dim_label} vs 行权价 (到期日: {unique_exp_dates[0]})'
    else:
        exp_dates_str = ', '.join([pd.to_datetime(ed).strftime('%Y-%m-%d') for ed in unique_exp_dates])
        title = f'{dim_label} vs 行权价 (对比 {len(unique_exp_dates)} 个到期日)'
    
    # 对于成交量，添加说明
    annotations = []
    if greeks_param == 'volume':
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            xanchor="left", yanchor="top",
            text="💡 提示：柱状图仅显示有成交量的行权价（零值已隐藏）",
            showarrow=False,
            font=dict(size=10, color="gray"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="gray",
            borderwidth=1
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='行权价 (Strike Price)',
        yaxis_title=dim_label,
        hovermode='closest',
        template='plotly_white',
        height=500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        annotations=annotations
    )
    
    # 显示图表
    st.plotly_chart(fig, width='stretch')


def plot_all_greeks_time_series(df: pd.DataFrame, greeks_params: list, strike_prices: list):
    """
    绘制所有选中的Greeks参数时序分析图表（多子图模式）
    
    :param df: 准备好的数据
    :param greeks_params: Greeks参数列表
    :param strike_prices: 行权价列表
    """
    if df.empty:
        st.warning("没有数据可显示")
        return
    
    # 维度标签（支持Greeks和非Greeks）- 必须在函数开头定义
    dimension_labels = {
        # Greeks参数
        'delta': 'Delta',
        'gamma': 'Gamma',
        'theta': 'Theta',
        'vega': 'Vega',
        'rho': 'Rho',
        # 非Greeks维度
        'mark_iv': 'IV (隐含波动率)',
        'mark_price': '期权价格 (USD)',
        'open_interest': '持仓量',
        'volume': '成交量'
    }
    
    num_greeks = len(greeks_params)
    
    # 创建子图
    fig = make_subplots(
        rows=num_greeks,
        cols=1,
        subplot_titles=[f'{dimension_labels.get(greeks_params[i], greeks_params[i])} vs 到期日' for i in range(num_greeks)],
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[1] * num_greeks
    )
    
    # 颜色方案
    colors = px.colors.qualitative.Set3
    call_colors = px.colors.qualitative.Set1[:10]
    put_colors = px.colors.qualitative.Pastel[:10]
    
    # 为每个Greeks参数创建子图
    for greek_idx, greeks_param in enumerate(greeks_params):
        row_num = greek_idx + 1
        
        # 为每个行权价绘制一条线
        for idx, strike in enumerate(strike_prices):
            strike_df = df[df['strike'] == strike].copy()
            
            if strike_df.empty or greeks_param not in strike_df.columns:
                continue
            
            # 分离Call和Put
            call_df = strike_df[strike_df['option_type'] == 'C'].copy() if 'option_type' in strike_df.columns else pd.DataFrame()
            put_df = strike_df[strike_df['option_type'] == 'P'].copy() if 'option_type' in strike_df.columns else pd.DataFrame()
            
            show_legend = (greek_idx == 0)  # 只在第一个子图显示图例
            
            # 绘制Call期权
            if not call_df.empty:
                fig.add_trace(go.Scatter(
                    x=call_df['expiration_date'],
                    y=call_df[greeks_param],
                    mode='lines+markers',
                    name=f'Call {strike:.0f}',
                    line=dict(color=call_colors[idx % len(call_colors)], width=2),
                    marker=dict(size=4),
                    showlegend=show_legend,
                    legendgroup=f'call_{strike}',
                    hovertemplate=f'<b>Call {strike:.0f}</b><br>' +
                                '到期日: %{x|%Y-%m-%d}<br>' +
                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                '<extra></extra>'
                ), row=row_num, col=1)
            
            # 绘制Put期权
            if not put_df.empty:
                fig.add_trace(go.Scatter(
                    x=put_df['expiration_date'],
                    y=put_df[greeks_param],
                    mode='lines+markers',
                    name=f'Put {strike:.0f}',
                    line=dict(color=put_colors[idx % len(put_colors)], width=2, dash='dash'),
                    marker=dict(size=4),
                    showlegend=show_legend,
                    legendgroup=f'put_{strike}',
                    hovertemplate=f'<b>Put {strike:.0f}</b><br>' +
                                '到期日: %{x|%Y-%m-%d}<br>' +
                                f'{greeks_param}: %{{y:.4f}}<br>' +
                                '<extra></extra>'
                ), row=row_num, col=1)
        
        # 更新Y轴标签
        fig.update_yaxes(title_text=dimension_labels.get(greeks_param, greeks_param), row=row_num, col=1)
    
    # 获取所有可能的到期日范围，确保X轴显示所有到期日
    all_exp_dates = get_sorted_unique_dates(df['expiration_date']) if 'expiration_date' in df.columns else []
    
    # 更新X轴标签和范围（只在最后一个子图）
    if all_exp_dates:
        # 设置X轴范围，确保包含所有到期日
        xaxis_range = [pd.Timestamp(min(all_exp_dates)) - pd.Timedelta(days=1),
                       pd.Timestamp(max(all_exp_dates)) + pd.Timedelta(days=1)]
        fig.update_xaxes(
            title_text='到期日 (Expiration Date)',
            type='date',
            tickformat='%Y-%m-%d',
            range=xaxis_range,
            row=num_greeks,
            col=1
        )
    else:
        fig.update_xaxes(title_text='到期日 (Expiration Date)', row=num_greeks, col=1)
    
    # 更新整体布局
    fig.update_layout(
        title=f'维度分析 - 时序视图 (按行权价分组)',
        hovermode='closest',
        template='plotly_white',
        height=350 * num_greeks,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 显示图表
    st.plotly_chart(fig, width='stretch')


def plot_time_series_chart(df: pd.DataFrame, greeks_param: str, strike_prices: list):
    """
    绘制时序分析图表
    
    :param df: 准备好的数据
    :param greeks_param: Greeks参数名称
    :param strike_prices: 行权价列表
    """
    if df.empty:
        st.warning("没有数据可显示")
        return
    
    # 创建图表
    fig = go.Figure()
    
    # 为每个行权价绘制一条线
    colors = px.colors.qualitative.Set3
    
    for idx, strike in enumerate(strike_prices):
        strike_df = df[df['strike'] == strike].copy()
        
        if strike_df.empty:
            continue
        
        # 分离Call和Put
        call_df = strike_df[strike_df['option_type'] == 'C'].copy() if 'option_type' in strike_df.columns else pd.DataFrame()
        put_df = strike_df[strike_df['option_type'] == 'P'].copy() if 'option_type' in strike_df.columns else pd.DataFrame()
        
        color = colors[idx % len(colors)]
        
        # 绘制Call期权
        if not call_df.empty:
            fig.add_trace(go.Scatter(
                x=call_df['expiration_date'],
                y=call_df[greeks_param],
                mode='lines+markers',
                name=f'Call {strike:.0f}',
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate='<b>Call %{fullData.name}</b><br>' +
                            '到期日: %{x|%Y-%m-%d}<br>' +
                            f'{greeks_param}: %{{y:.4f}}<br>' +
                            '<extra></extra>'
            ))
        
        # 绘制Put期权
        if not put_df.empty:
            # Put使用稍浅的颜色
            put_color = px.colors.qualitative.Pastel[idx % len(px.colors.qualitative.Pastel)]
            fig.add_trace(go.Scatter(
                x=put_df['expiration_date'],
                y=put_df[greeks_param],
                mode='lines+markers',
                name=f'Put {strike:.0f}',
                line=dict(color=put_color, width=2, dash='dash'),
                marker=dict(size=6),
                hovertemplate='<b>Put %{fullData.name}</b><br>' +
                            '到期日: %{x|%Y-%m-%d}<br>' +
                            f'{greeks_param}: %{{y:.4f}}<br>' +
                            '<extra></extra>'
            ))
        
        # 如果没有option_type列，绘制所有数据
        if call_df.empty and put_df.empty and not strike_df.empty:
            fig.add_trace(go.Scatter(
                x=strike_df['expiration_date'],
                y=strike_df[greeks_param],
                mode='lines+markers',
                name=f'Strike {strike:.0f}',
                line=dict(color=color, width=2),
                marker=dict(size=6)
            ))
    
    # 更新布局 - 支持Greeks和非Greeks维度
    dimension_labels = {
        # Greeks参数
        'delta': 'Delta',
        'gamma': 'Gamma',
        'theta': 'Theta',
        'vega': 'Vega',
        'rho': 'Rho',
        # 非Greeks维度
        'mark_iv': 'IV (隐含波动率)',
        'mark_price': '期权价格 (USD)',
        'open_interest': '持仓量',
        'volume': '成交量'
    }
    
    dim_label = dimension_labels.get(greeks_param, greeks_param)
    
    # 获取所有可能的到期日范围，确保X轴显示所有到期日
    all_exp_dates = get_sorted_unique_dates(df['expiration_date']) if 'expiration_date' in df.columns else []
    
    layout_updates = {
        'title': f'{dim_label} vs 到期日 (按行权价分组)',
        'xaxis_title': '到期日 (Expiration Date)',
        'yaxis_title': dim_label,
        'hovermode': 'closest',
        'template': 'plotly_white',
        'height': 500,
        'legend': dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    }
    
    # 设置X轴范围，确保包含所有到期日
    if all_exp_dates:
        layout_updates['xaxis'] = dict(
            type='date',
            tickformat='%Y-%m-%d',
            # 确保X轴范围包含所有到期日
            range=[pd.Timestamp(min(all_exp_dates)) - pd.Timedelta(days=1),
                   pd.Timestamp(max(all_exp_dates)) + pd.Timedelta(days=1)]
        )
    else:
        layout_updates['xaxis'] = dict(type='date', tickformat='%Y-%m-%d')
    
    fig.update_layout(**layout_updates)
    
    # 显示图表
    st.plotly_chart(fig, width='stretch')


def plot_breakeven_scatter(df: pd.DataFrame, current_spot_price: float = None):
    """
    绘制盈亏平衡点散点图
    
    :param df: 准备好的盈亏平衡数据（包含breakeven_price列）
    :param current_spot_price: 当前标的价格（用于绘制基准线）
    """
    if df.empty or 'breakeven_price' not in df.columns:
        st.warning("没有盈亏平衡数据可显示")
        return
    
    # 创建图表
    fig = go.Figure()
    
    # 获取唯一的到期日
    unique_exp_dates = get_sorted_unique_dates(df['expiration_date']) if 'expiration_date' in df.columns else []
    
    # 获取颜色方案
    call_colors = px.colors.qualitative.Set1[:5]
    put_colors = px.colors.qualitative.Pastel[:5]
    
    # 确定散点大小（基于volume或open_interest）
    size_column = None
    if 'volume' in df.columns and not df['volume'].isna().all():
        size_column = 'volume'
    elif 'open_interest' in df.columns and not df['open_interest'].isna().all():
        size_column = 'open_interest'
    
    # 为每个到期日绘制数据
    for exp_idx, exp_date in enumerate(unique_exp_dates):
        exp_df = df[df['expiration_date'].dt.date == exp_date].copy()
        
        if exp_df.empty:
            continue
        
        # 分离Call和Put期权
        if 'option_type' in exp_df.columns:
            call_df = exp_df[exp_df['option_type'] == 'C'].copy()
            put_df = exp_df[exp_df['option_type'] == 'P'].copy()
            
            # 绘制Call期权（绿色）
            if not call_df.empty:
                exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
                
                # 计算散点大小
                if size_column and size_column in call_df.columns:
                    # 归一化大小（最小10，最大50）
                    sizes = call_df[size_column].fillna(0)
                    if sizes.max() > 0:
                        sizes_normalized = 10 + (sizes / sizes.max()) * 40
                    else:
                        sizes_normalized = [15] * len(call_df)
                else:
                    sizes_normalized = [15] * len(call_df)
                
                fig.add_trace(go.Scatter(
                    x=call_df['strike'],
                    y=call_df['breakeven_price'],
                    mode='markers',
                    name=f'Call {exp_date_str}',
                    marker=dict(
                        color='#2E7D32',  # 绿色
                        size=sizes_normalized,
                        opacity=0.6,
                        line=dict(width=1, color='#1B5E20')
                    ),
                    hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                '行权价: %{x}<br>' +
                                '盈亏平衡点: %{y:.2f}<br>' +
                                (f'{size_column}: %{{customdata}}<br>' if size_column else '') +
                                '<extra></extra>',
                    customdata=call_df[size_column].values if size_column else None
                ))
            
            # 绘制Put期权（红色）
            if not put_df.empty:
                exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
                
                # 计算散点大小
                if size_column and size_column in put_df.columns:
                    sizes = put_df[size_column].fillna(0)
                    if sizes.max() > 0:
                        sizes_normalized = 10 + (sizes / sizes.max()) * 40
                    else:
                        sizes_normalized = [15] * len(put_df)
                else:
                    sizes_normalized = [15] * len(put_df)
                
                fig.add_trace(go.Scatter(
                    x=put_df['strike'],
                    y=put_df['breakeven_price'],
                    mode='markers',
                    name=f'Put {exp_date_str}',
                    marker=dict(
                        color='#C62828',  # 红色
                        size=sizes_normalized,
                        opacity=0.6,
                        line=dict(width=1, color='#B71C1C')
                    ),
                    hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                '行权价: %{x}<br>' +
                                '盈亏平衡点: %{y:.2f}<br>' +
                                (f'{size_column}: %{{customdata}}<br>' if size_column else '') +
                                '<extra></extra>',
                    customdata=put_df[size_column].values if size_column else None
                ))
    
    # 添加当前标的价格基准线
    if current_spot_price is not None:
        # 获取行权价范围
        if 'strike' in df.columns:
            strike_min = df['strike'].min()
            strike_max = df['strike'].max()
            
            fig.add_trace(go.Scatter(
                x=[strike_min, strike_max],
                y=[current_spot_price, current_spot_price],
                mode='lines',
                name='当前标的价格',
                line=dict(color='gray', width=2, dash='dash'),
                hovertemplate=f'当前标的价格: {current_spot_price:.2f}<extra></extra>'
            ))
    
    # 构建标题
    if len(unique_exp_dates) == 1:
        title = f'盈亏平衡点分布 (到期日: {unique_exp_dates[0]})'
    else:
        title = f'盈亏平衡点分布 (对比 {len(unique_exp_dates)} 个到期日)'
    
    fig.update_layout(
        title=title,
        xaxis_title='行权价 (Strike Price)',
        yaxis_title='盈亏平衡点 (Breakeven Price)',
        hovermode='closest',
        template='plotly_white',
        height=600,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 显示图表
    st.plotly_chart(fig, width='stretch')


def plot_delta_skew_chart(df: pd.DataFrame, show_risk_reversal: bool = False):
    """
    绘制Delta偏度分析图表（IV vs Delta绝对值）
    
    :param df: 准备好的Delta偏度数据（包含delta_abs和mark_iv列）
    :param show_risk_reversal: 是否显示风险逆转曲线（IV_Call - IV_Put）
    """
    if df.empty or 'delta_abs' not in df.columns or 'mark_iv' not in df.columns:
        st.warning("没有Delta偏度数据可显示")
        return
    
    # 创建图表
    if show_risk_reversal:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=['IV vs Delta (绝对值)', '风险逆转 (IV_Call - IV_Put)'],
            shared_xaxes=True,
            vertical_spacing=0.1
        )
    else:
        fig = go.Figure()
    
    # 获取唯一的到期日
    unique_exp_dates = get_sorted_unique_dates(df['expiration_date']) if 'expiration_date' in df.columns else []
    
    # 获取颜色方案
    call_colors = px.colors.qualitative.Set1[:5]
    put_colors = px.colors.qualitative.Pastel[:5]
    
    # 为每个到期日绘制数据
    for exp_idx, exp_date in enumerate(unique_exp_dates):
        exp_df = df[df['expiration_date'].dt.date == exp_date].copy()
        
        if exp_df.empty:
            continue
        
        # 分离Call和Put期权
        if 'option_type' in exp_df.columns:
            call_df = exp_df[exp_df['option_type'] == 'C'].copy()
            put_df = exp_df[exp_df['option_type'] == 'P'].copy()
            
            exp_date_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
            
            # 绘制Call期权IV曲线
            if not call_df.empty:
                call_df_sorted = call_df.sort_values('delta_abs')
                if show_risk_reversal:
                    fig.add_trace(go.Scatter(
                        x=call_df_sorted['delta_abs'],
                        y=call_df_sorted['mark_iv'],
                        mode='lines+markers',
                        name=f'Call {exp_date_str}',
                        line=dict(color=call_colors[exp_idx % len(call_colors)], width=2),
                        marker=dict(size=6),
                        hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                    'Delta: %{x:.2f}<br>' +
                                    'IV: %{y:.2%}<br>' +
                                    '<extra></extra>'
                    ), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(
                        x=call_df_sorted['delta_abs'],
                        y=call_df_sorted['mark_iv'],
                        mode='lines+markers',
                        name=f'Call {exp_date_str}',
                        line=dict(color=call_colors[exp_idx % len(call_colors)], width=2),
                        marker=dict(size=6),
                        hovertemplate=f'<b>Call {exp_date_str}</b><br>' +
                                    'Delta: %{x:.2f}<br>' +
                                    'IV: %{y:.2%}<br>' +
                                    '<extra></extra>'
                    ))
            
            # 绘制Put期权IV曲线
            if not put_df.empty:
                put_df_sorted = put_df.sort_values('delta_abs')
                if show_risk_reversal:
                    fig.add_trace(go.Scatter(
                        x=put_df_sorted['delta_abs'],
                        y=put_df_sorted['mark_iv'],
                        mode='lines+markers',
                        name=f'Put {exp_date_str}',
                        line=dict(color=put_colors[exp_idx % len(put_colors)], width=2, dash='dash'),
                        marker=dict(size=6),
                        hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                    'Delta: %{x:.2f}<br>' +
                                    'IV: %{y:.2%}<br>' +
                                    '<extra></extra>'
                    ), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(
                        x=put_df_sorted['delta_abs'],
                        y=put_df_sorted['mark_iv'],
                        mode='lines+markers',
                        name=f'Put {exp_date_str}',
                        line=dict(color=put_colors[exp_idx % len(put_colors)], width=2, dash='dash'),
                        marker=dict(size=6),
                        hovertemplate=f'<b>Put {exp_date_str}</b><br>' +
                                    'Delta: %{x:.2f}<br>' +
                                    'IV: %{y:.2%}<br>' +
                                    '<extra></extra>'
                    ))
            
            # 计算并绘制风险逆转曲线
            if show_risk_reversal and not call_df.empty and not put_df.empty:
                # 合并Call和Put数据，按Delta对齐
                call_sorted = call_df.sort_values('delta_abs')
                put_sorted = put_df.sort_values('delta_abs')
                
                # 找到共同的Delta值
                common_deltas = sorted(set(call_sorted['delta_abs']) & set(put_sorted['delta_abs']))
                
                if len(common_deltas) > 0:
                    risk_reversal = []
                    for delta_val in common_deltas:
                        call_iv = call_sorted[call_sorted['delta_abs'] == delta_val]['mark_iv'].values
                        put_iv = put_sorted[put_sorted['delta_abs'] == delta_val]['mark_iv'].values
                        if len(call_iv) > 0 and len(put_iv) > 0:
                            risk_reversal.append({
                                'delta_abs': delta_val,
                                'risk_reversal': call_iv[0] - put_iv[0]
                            })
                    
                    if risk_reversal:
                        rr_df = pd.DataFrame(risk_reversal)
                        fig.add_trace(go.Scatter(
                            x=rr_df['delta_abs'],
                            y=rr_df['risk_reversal'],
                            mode='lines+markers',
                            name=f'风险逆转 {exp_date_str}',
                            line=dict(color='purple', width=2),
                            marker=dict(size=6),
                            hovertemplate=f'<b>风险逆转 {exp_date_str}</b><br>' +
                                        'Delta: %{x:.2f}<br>' +
                                        'IV_Call - IV_Put: %{y:.2%}<br>' +
                                        '<extra></extra>'
                        ), row=2, col=1)
                        
                        # 添加零线
                        fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)
    
    # 更新布局
    if show_risk_reversal:
        fig.update_yaxes(title_text='IV (隐含波动率)', row=1, col=1)
        fig.update_yaxes(title_text='风险逆转 (IV_Call - IV_Put)', row=2, col=1)
        fig.update_xaxes(title_text='Delta (绝对值)', row=2, col=1)
        
        if len(unique_exp_dates) == 1:
            title = f'Delta偏度分析 (到期日: {unique_exp_dates[0]})'
        else:
            title = f'Delta偏度分析 (对比 {len(unique_exp_dates)} 个到期日)'
    else:
        fig.update_layout(
            xaxis_title='Delta (绝对值)',
            yaxis_title='IV (隐含波动率)'
        )
        
        if len(unique_exp_dates) == 1:
            title = f'Delta偏度分析 (到期日: {unique_exp_dates[0]})'
        else:
            title = f'Delta偏度分析 (对比 {len(unique_exp_dates)} 个到期日)'
    
    fig.update_layout(
        title=title,
        hovermode='closest',
        template='plotly_white',
        height=700 if show_risk_reversal else 500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 显示图表
    st.plotly_chart(fig, width='stretch')
