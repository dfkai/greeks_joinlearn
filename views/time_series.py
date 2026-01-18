"""
时序分析视图
按行权价进行时序分析
"""

import streamlit as st
import pandas as pd
from src.core import OptionsDatabase
from src.utils import render_tag_selector
from src.utils.data_preparers import (
    prepare_time_series_data_multi_greeks,
    prepare_time_series_data
)
from src.utils.chart_plotters import (
    plot_all_greeks_time_series,
    plot_time_series_chart
)


def render_time_series_view(db: OptionsDatabase):
    """
    时序分析视图页面
    
    :param db: 数据库对象
    """
    st.header("📈 时序分析视图（按行权价）")
    st.caption("横轴：到期日 | 纵轴：分析维度 | 按行权价分组")
    
    # 加载所有数据以获取可用行权价和所有到期日
    # 使用get_all_options_chain获取所有到期日的数据，而不仅仅是"最新"的数据
    df_all = db.get_all_options_chain()
    
    if df_all.empty:
        st.warning("数据库中没有数据，请先采集数据")
        return
    
    # 获取所有可用行权价
    if 'strike' not in df_all.columns:
        st.warning("数据中缺少行权价信息")
        return
    
    available_strikes = sorted(df_all['strike'].unique().tolist())
    
    if not available_strikes:
        st.warning("没有可用的行权价数据")
        return
    
    # 初始化session_state
    if 'time_series_selected_strikes' not in st.session_state:
        default_strikes = available_strikes[:min(5, len(available_strikes))]
        st.session_state['time_series_selected_strikes'] = default_strikes
    
    if 'time_series_selected_greeks' not in st.session_state:
        st.session_state['time_series_selected_greeks'] = 'delta'
    if 'time_series_option_type' not in st.session_state:
        st.session_state['time_series_option_type'] = "全部"
    
    # 标签式行权价选择器（多选，允许完全取消）
    selected_strikes_list = render_tag_selector(
        label="选择行权价（可多选，点击取消选中）",
        options=available_strikes,
        selected=st.session_state.get('time_series_selected_strikes', available_strikes[:min(5, len(available_strikes))]),
        key_prefix="time_strike",
        format_func=lambda x: f"{x:.0f}",
        allow_multiple=True,
        min_selected=0  # 允许完全取消所有选项
    )
    
    # 更新选中的行权价
    if selected_strikes_list:
        st.session_state['time_series_selected_strikes'] = selected_strikes_list
    else:
        # 如果没有选中任何，清空选择（允许用户完全取消）
        st.session_state['time_series_selected_strikes'] = []
    
    selected_strikes = st.session_state.get('time_series_selected_strikes', [])
    
    # 扩展维度选择器（Greeks + 非Greeks维度）
    all_dimensions = {
        # Greeks参数
        'delta': 'Delta',
        'gamma': 'Gamma',
        'theta': 'Theta',
        'vega': 'Vega',
        'rho': 'Rho',
        # 非Greeks维度
        'mark_iv': 'IV (隐含波动率)',
        'mark_price': '期权价格',
        'open_interest': '持仓量',
        'volume': '成交量'
    }
    
    # 初始化维度选择状态
    if 'time_series_selected_dimensions_list' not in st.session_state:
        st.session_state['time_series_selected_dimensions_list'] = ['delta']
    
    selected_dimensions_list = render_tag_selector(
        label="选择分析维度（可多选，全选将上下排布多个子图）",
        options=list(all_dimensions.keys()),
        selected=st.session_state.get('time_series_selected_dimensions_list', ['delta']),
        key_prefix="time_dimensions",
        format_func=lambda x: all_dimensions[x],
        allow_multiple=True,
        min_selected=1
    )
    
    # 更新选中的维度列表
    if selected_dimensions_list:
        st.session_state['time_series_selected_dimensions_list'] = selected_dimensions_list
    else:
        st.session_state['time_series_selected_dimensions_list'] = ['delta']
    
    selected_dimensions_list_final = st.session_state.get('time_series_selected_dimensions_list', ['delta'])
    
    # 标签式期权类型筛选器（单选）
    option_types = ["全部", "C", "P"]
    selected_option_types = render_tag_selector(
        label="期权类型",
        options=option_types,
        selected=[st.session_state['time_series_option_type']],
        key_prefix="time_option_type",
        allow_multiple=False
    )
    
    # 更新选中的期权类型
    if selected_option_types:
        st.session_state['time_series_option_type'] = selected_option_types[0]
    else:
        st.session_state['time_series_option_type'] = "全部"
    
    option_type_filter = st.session_state['time_series_option_type']
    
    if not selected_strikes:
        st.warning("请至少选择一个行权价")
        return
    
    # 根据选中的维度数量决定使用哪种绘图模式
    if len(selected_dimensions_list_final) > 1:
        # 多维度模式：使用子图
        # 准备包含所有维度的数据
        prepared_df_multi = prepare_time_series_data_multi_greeks(
            df_all, 
            selected_strikes, 
            selected_dimensions_list_final, 
            option_type_filter
        )
        
        if prepared_df_multi.empty:
            st.warning("没有符合条件的数据")
            return
        
        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("数据点数", len(prepared_df_multi))
        with col2:
            st.metric("选中行权价数", len(selected_strikes))
        with col3:
            if 'expiration_date' in prepared_df_multi.columns:
                unique_dates = prepared_df_multi['expiration_date'].nunique()
                st.metric("唯一到期日", unique_dates)
        with col4:
            st.metric("选中维度数", len(selected_dimensions_list_final))
        
        # 添加数据完整性诊断信息
        with st.expander("🔍 数据完整性诊断", expanded=False):
            if 'expiration_date' in prepared_df_multi.columns:
                # 按到期日统计
                exp_date_counts = prepared_df_multi.groupby(prepared_df_multi['expiration_date'].dt.date).size()
                st.write("**各到期日的数据点数:**")
                for exp_date, count in exp_date_counts.items():
                    st.write(f"- {exp_date}: {count} 条记录")
                
                # 检查每个维度的缺失值情况
                st.write("\n**各维度的缺失值统计:**")
                for dim in selected_dimensions_list_final:
                    if dim in prepared_df_multi.columns:
                        total = len(prepared_df_multi)
                        missing = prepared_df_multi[dim].isna().sum()
                        missing_pct = (missing / total * 100) if total > 0 else 0
                        st.write(f"- {dim}: 缺失 {missing}/{total} ({missing_pct:.1f}%)")
                
                # 检查每个行权价在每个到期日的数据情况
                st.write("\n**各行权价在各到期日的数据覆盖情况:**")
                for strike in selected_strikes[:5]:  # 只显示前5个行权价
                    strike_df = prepared_df_multi[prepared_df_multi['strike'] == strike]
                    if not strike_df.empty:
                        valid_expirations = strike_df['expiration_date'].dropna()
                        exp_dates_with_data = sorted(valid_expirations.dt.date.unique())
                        st.write(f"- 行权价 {strike:.0f}: {len(exp_dates_with_data)} 个到期日有数据")
        
        st.divider()
        
        # 绘制多维度子图
        plot_all_greeks_time_series(prepared_df_multi, selected_dimensions_list_final, selected_strikes)
        
    else:
        # 单维度模式：使用原有的单图模式
        selected_dimension = selected_dimensions_list_final[0]
        
        # 准备数据（使用通用函数支持任意维度）
        prepared_df = prepare_time_series_data(df_all, selected_strikes, selected_dimension, option_type_filter)
        
        if prepared_df.empty:
            st.warning("没有符合条件的数据")
            return
        
        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("数据点数", len(prepared_df))
        with col2:
            st.metric("选中行权价数", len(selected_strikes))
        with col3:
            if 'expiration_date' in prepared_df.columns:
                unique_dates = prepared_df['expiration_date'].nunique()
                st.metric("唯一到期日", unique_dates)
        with col4:
            if selected_dimension in prepared_df.columns:
                dim_label = all_dimensions.get(selected_dimension, selected_dimension)
                valid_values = prepared_df[selected_dimension].dropna()
                if len(valid_values) > 0:
                    st.metric(f"{dim_label}范围", 
                             f"{valid_values.min():.4f} - {valid_values.max():.4f}")
                else:
                    st.metric(f"{dim_label}范围", "无有效数据")
        
        # 添加数据完整性诊断信息
        with st.expander("🔍 数据完整性诊断", expanded=False):
            if 'expiration_date' in prepared_df.columns:
                # 按到期日统计
                exp_date_counts = prepared_df.groupby(prepared_df['expiration_date'].dt.date).size()
                st.write("**各到期日的数据点数:**")
                for exp_date, count in exp_date_counts.items():
                    st.write(f"- {exp_date}: {count} 条记录")
                
                # 检查当前维度的缺失值情况
                if selected_dimension in prepared_df.columns:
                    total = len(prepared_df)
                    missing = prepared_df[selected_dimension].isna().sum()
                    missing_pct = (missing / total * 100) if total > 0 else 0
                    st.write(f"\n**{selected_dimension} 缺失值:** {missing}/{total} ({missing_pct:.1f}%)")
                    
                    # 检查每个行权价在每个到期日的数据情况
                    st.write("\n**各行权价在各到期日的数据覆盖情况:**")
                    for strike in selected_strikes[:5]:  # 只显示前5个行权价
                        strike_df = prepared_df[prepared_df['strike'] == strike]
                        if not strike_df.empty:
                            valid_expirations = strike_df['expiration_date'].dropna()
                            exp_dates_with_data = sorted(valid_expirations.dt.date.unique())
                            valid_values_exp = strike_df[strike_df[selected_dimension].notna()]['expiration_date'].dropna()
                            exp_dates_with_value = sorted(valid_values_exp.dt.date.unique())
                            st.write(f"- 行权价 {strike:.0f}: {len(exp_dates_with_data)} 个到期日有数据, {len(exp_dates_with_value)} 个到期日有{selected_dimension}值")
        
        st.divider()
        
        # 绘制图表
        plot_time_series_chart(prepared_df, selected_dimension, selected_strikes)
    
    # 显示数据表格（可选）
    with st.expander("📋 查看数据表格"):
        # 根据模式选择要显示的列
        if len(selected_dimensions_list_final) > 1:
            # 多维度模式：显示所有选中的维度
            display_cols = ['expiration_date', 'strike', 'option_type'] + selected_dimensions_list_final
            display_df = prepared_df_multi
        else:
            # 单维度模式
            selected_dimension = selected_dimensions_list_final[0]
            display_cols = ['expiration_date', 'strike', 'option_type', selected_dimension]
            display_df = prepared_df
        
        available_cols = [col for col in display_cols if col in display_df.columns]
        st.dataframe(display_df[available_cols], width='stretch')

