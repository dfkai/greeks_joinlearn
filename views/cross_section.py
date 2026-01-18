"""
截面分析视图
按到期日进行截面分析
"""

import streamlit as st
import pandas as pd
from src.core import OptionsDatabase
from src.utils import render_tag_selector
from src.utils.data_preparers import (
    prepare_general_cross_section_data,
    prepare_cross_section_data_multi_greeks,
    prepare_breakeven_data,
    prepare_delta_skew_data
)
from src.utils.chart_plotters import (
    plot_all_greeks_cross_section,
    plot_cross_section_chart,
    plot_breakeven_scatter,
    plot_delta_skew_chart
)


def render_cross_section_view(db: OptionsDatabase):
    """
    截面分析视图页面
    
    :param db: 数据库对象
    """
    st.header("📈 截面分析视图")
    st.caption("多维度期权数据分析：按行权价、按Delta、盈亏平衡分析")
    
    # 获取所有可用到期日
    exp_dates = db.get_all_expiration_dates()
    
    if not exp_dates:
        st.warning("数据库中没有到期日数据，请先采集数据")
        return
    
    # 初始化session_state
    if 'cross_section_selected_exp_dates' not in st.session_state:
        st.session_state['cross_section_selected_exp_dates'] = [exp_dates[0]] if exp_dates else []
    if 'cross_section_option_type' not in st.session_state:
        st.session_state['cross_section_option_type'] = "全部"
    
    # 标签式到期日选择器（多选）
    selected_exp_dates = render_tag_selector(
        label="选择到期日（可多选，对比不同到期日的截面数据）",
        options=exp_dates,
        selected=st.session_state.get('cross_section_selected_exp_dates', [exp_dates[0]] if exp_dates else []),
        key_prefix="cross_exp_date",
        format_func=lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else str(x),
        allow_multiple=True
    )
    
    # 更新选中的到期日列表
    if selected_exp_dates:
        st.session_state['cross_section_selected_exp_dates'] = selected_exp_dates
    elif exp_dates:
        # 如果没有选中任何，默认选择第一个
        st.session_state['cross_section_selected_exp_dates'] = [exp_dates[0]]
    
    selected_exp_dates_list = st.session_state.get('cross_section_selected_exp_dates', [exp_dates[0]] if exp_dates else [])
    
    # 标签式期权类型筛选器（单选）
    option_types = ["全部", "C", "P"]
    selected_option_types = render_tag_selector(
        label="期权类型",
        options=option_types,
        selected=[st.session_state['cross_section_option_type']],
        key_prefix="cross_option_type",
        allow_multiple=False
    )
    
    # 更新选中的期权类型
    if selected_option_types:
        st.session_state['cross_section_option_type'] = selected_option_types[0]
    else:
        st.session_state['cross_section_option_type'] = "全部"
    
    option_type_filter = st.session_state['cross_section_option_type']
    
    # 加载数据（多个到期日）
    all_dfs = []
    for exp_date in selected_exp_dates_list:
        df = db.get_options_by_expiration(exp_date)
        if not df.empty:
            all_dfs.append(df)
    
    if not all_dfs:
        st.warning(f"选中的到期日没有数据")
        return
    
    # 合并所有到期日的数据
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # 获取当前标的价格（用于盈亏平衡分析）
    current_spot_price = None
    if 'underlying_price' in combined_df.columns:
        # 使用最新的标的价格
        non_null_prices = combined_df['underlying_price'].dropna()
        if not non_null_prices.empty:
            current_spot_price = float(non_null_prices.iloc[-1])
    
    # 创建三个选项卡
    tab1, tab2, tab3 = st.tabs([
        "📊 按行权价分析",
        "📈 按Delta分析",
        "💰 盈亏平衡分析"
    ])
    
    # 选项卡1：按行权价分析（原有功能）
    with tab1:
        st.subheader("📊 按行权价截面分析")
        st.caption("横轴：行权价 | 纵轴：分析维度 | 按到期日分组")
        
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
        if 'cross_section_selected_dimensions_list' not in st.session_state:
            st.session_state['cross_section_selected_dimensions_list'] = ['delta']
        
        selected_dimensions_list = render_tag_selector(
            label="选择分析维度（可多选，全选将上下排布多个子图）",
            options=list(all_dimensions.keys()),
            selected=st.session_state.get('cross_section_selected_dimensions_list', ['delta']),
            key_prefix="cross_dimensions",
            format_func=lambda x: all_dimensions[x],
            allow_multiple=True,
            min_selected=1  # 至少选择一个
        )
        
        # 更新选中的维度列表
        if selected_dimensions_list:
            st.session_state['cross_section_selected_dimensions_list'] = selected_dimensions_list
        else:
            st.session_state['cross_section_selected_dimensions_list'] = ['delta']
        
        selected_dimensions_list_final = st.session_state.get('cross_section_selected_dimensions_list', ['delta'])
        
        # 根据选中的维度数量决定使用哪种绘图模式
        if len(selected_dimensions_list_final) > 1:
            # 多维度模式：使用子图
            # 准备包含所有维度的数据
            prepared_df_multi = prepare_cross_section_data_multi_greeks(
                combined_df, 
                selected_exp_dates_list, 
                selected_dimensions_list_final, 
                option_type_filter
            )
            
            if prepared_df_multi.empty:
                st.warning("没有符合条件的数据")
            else:
                # 显示统计信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("数据点数", len(prepared_df_multi))
                with col2:
                    st.metric("选中到期日数", len(selected_exp_dates_list))
                with col3:
                    if 'strike' in prepared_df_multi.columns:
                        st.metric("行权价范围", f"{prepared_df_multi['strike'].min():.0f} - {prepared_df_multi['strike'].max():.0f}")
                with col4:
                    st.metric("选中维度数", len(selected_dimensions_list_final))
                
                st.divider()
                
                # 绘制多维度子图
                plot_all_greeks_cross_section(prepared_df_multi, selected_dimensions_list_final, selected_exp_dates_list)
        else:
            # 单维度模式：使用原有的单图模式
            selected_dimension = selected_dimensions_list_final[0]
            
            # 准备数据（使用通用函数支持任意维度）
            prepared_df = prepare_general_cross_section_data(combined_df, selected_exp_dates_list, selected_dimension, option_type_filter)
            
            if prepared_df.empty:
                st.warning("没有符合条件的数据")
            else:
                # 显示统计信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("数据点数", len(prepared_df))
                with col2:
                    st.metric("选中到期日数", len(selected_exp_dates_list))
                with col3:
                    if 'strike' in prepared_df.columns:
                        st.metric("行权价范围", f"{prepared_df['strike'].min():.0f} - {prepared_df['strike'].max():.0f}")
                with col4:
                    if selected_dimension in prepared_df.columns:
                        dim_label = all_dimensions.get(selected_dimension, selected_dimension)
                        st.metric(f"{dim_label}范围", 
                                 f"{prepared_df[selected_dimension].min():.4f} - {prepared_df[selected_dimension].max():.4f}")
                
                st.divider()
                
                # 绘制图表（支持多到期日对比）
                plot_cross_section_chart(prepared_df, selected_dimension, selected_exp_dates_list)
    
    # 选项卡2：按Delta分析（新增）
    with tab2:
        st.subheader("📈 按Delta截面分析")
        st.caption("横轴：Delta (绝对值) | 纵轴：IV (隐含波动率) | 对比Call/Put的波动率微笑和偏斜")
        
        # 准备Delta偏度数据
        delta_skew_df = prepare_delta_skew_data(combined_df, selected_exp_dates_list, option_type_filter)
        
        if delta_skew_df.empty:
            st.warning("没有符合条件的数据（需要delta和mark_iv字段）")
        else:
            # 显示统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("数据点数", len(delta_skew_df))
            with col2:
                st.metric("选中到期日数", len(selected_exp_dates_list))
            with col3:
                if 'delta_abs' in delta_skew_df.columns:
                    st.metric("Delta范围", f"{delta_skew_df['delta_abs'].min():.2f} - {delta_skew_df['delta_abs'].max():.2f}")
            
            st.divider()
            
            # 是否显示风险逆转曲线
            show_risk_reversal = st.checkbox(
                "显示风险逆转曲线 (IV_Call - IV_Put)",
                value=False,
                help="风险逆转曲线显示看涨和看跌期权IV的差异，正值表示看涨情绪，负值表示看跌情绪"
            )
            
            # 绘制Delta偏度图表
            plot_delta_skew_chart(delta_skew_df, show_risk_reversal=show_risk_reversal)
            
            # 说明文字
            st.info("💡 **分析提示**: 此视图按Delta绝对值（风险暴露程度）对比Call和Put的IV。相同Delta的Call和Put具有相似的实值概率，可以更准确地比较市场情绪。")
    
    # 选项卡3：盈亏平衡分析（新增）
    with tab3:
        st.subheader("💰 盈亏平衡点分析")
        st.caption("横轴：行权价 | 纵轴：盈亏平衡点 | 识别市场成本结构和潜在支撑/阻力位")
        
        # 准备盈亏平衡数据
        breakeven_df = prepare_breakeven_data(combined_df, selected_exp_dates_list, option_type_filter)
        
        if breakeven_df.empty:
            st.warning("没有符合条件的数据（需要mark_price字段）")
        else:
            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("数据点数", len(breakeven_df))
            with col2:
                st.metric("选中到期日数", len(selected_exp_dates_list))
            with col3:
                if 'strike' in breakeven_df.columns:
                    st.metric("行权价范围", f"{breakeven_df['strike'].min():.0f} - {breakeven_df['strike'].max():.0f}")
            with col4:
                if current_spot_price:
                    st.metric("当前标的价格", f"{current_spot_price:.2f}")
                else:
                    st.metric("当前标的价格", "未知")
            
            st.divider()
            
            # 标的价格输入（如果数据库中没有）
            if current_spot_price is None:
                current_spot_price = st.number_input(
                    "当前标的价格",
                    value=3000.0,
                    step=10.0,
                    help="用于绘制基准线"
                )
            
            # 绘制盈亏平衡散点图
            plot_breakeven_scatter(breakeven_df, current_spot_price=current_spot_price)
            
            # 说明文字
            st.info("💡 **分析提示**: 盈亏平衡点分布图显示市场参与者的成本线。密集区域代表市场共识目标，可能形成支撑/阻力。散点大小反映成交量或持仓量，越大表示市场关注度越高。")

