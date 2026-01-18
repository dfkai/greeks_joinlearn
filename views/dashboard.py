"""
数据概览视图
显示数据统计、筛选器和数据表格
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.utils import load_data, get_statistics, apply_filters


def render_dashboard_view(db, currency: str = "全部"):
    """
    渲染数据概览页面
    
    :param db: 数据库对象
    :param currency: 货币类型筛选
    """
    # 加载数据
    currency_filter = None if currency == "全部" else currency
    df = load_data(db, currency=currency_filter)
    
    if not df.empty:
        # 数据概览卡片
        st.header("📊 数据概览")
        stats = get_statistics(df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记录数", stats['total_count'])
        with col2:
            st.metric("唯一到期日", stats['unique_expirations'])
        with col3:
            if stats['strike_range'][0] is not None:
                st.metric("行权价范围", f"{stats['strike_range'][0]:.0f} - {stats['strike_range'][1]:.0f}")
        with col4:
            st.metric("期权类型", len(stats['option_types']))
        
        st.divider()
        
        # 筛选器
        st.header("🔍 数据筛选")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # 到期日选择
            if 'expiration_date' in df.columns:
                # 过滤掉NaT值，避免排序错误
                df_exp = df[df['expiration_date'].notna()].copy()  # 先过滤掉NaT
                if not df_exp.empty:
                    exp_dates_series = pd.to_datetime(df_exp['expiration_date']).dt.date
                    exp_dates = sorted([d for d in exp_dates_series.unique() if d is not None and pd.notna(d)])
                else:
                    exp_dates = []
                selected_exp_date = st.selectbox(
                    "到期日",
                    options=[None] + exp_dates,
                    format_func=lambda x: "全部" if x is None else str(x)
                )
            else:
                selected_exp_date = None
        
        with col2:
            # 行权价范围
            if 'strike' in df.columns:
                min_strike = st.number_input(
                    "最小行权价",
                    min_value=float(df['strike'].min()) if not df.empty else 0.0,
                    max_value=float(df['strike'].max()) if not df.empty else 100000.0,
                    value=float(df['strike'].min()) if not df.empty else 0.0,
                    step=100.0
                )
            else:
                min_strike = None
        
        with col3:
            if 'strike' in df.columns:
                max_strike = st.number_input(
                    "最大行权价",
                    min_value=float(df['strike'].min()) if not df.empty else 0.0,
                    max_value=float(df['strike'].max()) if not df.empty else 100000.0,
                    value=float(df['strike'].max()) if not df.empty else 100000.0,
                    step=100.0
                )
            else:
                max_strike = None
        
        with col4:
            # 期权类型
            option_type = st.selectbox(
                "期权类型",
                options=["全部", "C", "P"]
            )
        
        # 应用筛选
        filters = {
            'expiration_date': selected_exp_date,
            'min_strike': min_strike,
            'max_strike': max_strike,
            'option_type': option_type
        }
        
        filtered_df = apply_filters(df, filters)
        
        # 数据表格
        st.header("📋 数据表格")
        st.caption(f"显示 {len(filtered_df)} 条记录（共 {len(df)} 条）")
        
        # 选择显示的列
        if not filtered_df.empty:
            default_cols = ['instrument_name', 'expiration_date', 'strike', 'option_type', 
                          'mark_price', 'mark_iv', 'delta', 'gamma', 'theta', 'vega']
            available_cols = [col for col in default_cols if col in filtered_df.columns]
            
            # 显示数据表格
            st.dataframe(
                filtered_df[available_cols],
                width='stretch',
                height=400
            )
            
            # 数据下载按钮
            csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下载数据 (CSV)",
                data=csv,
                file_name=f"options_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("没有符合筛选条件的数据")
    else:
        st.warning("数据库中没有数据，请先运行数据采集脚本")
        st.info("可以使用以下命令采集数据：\n```python\nfrom data_collector import DataCollector\ncollector = DataCollector()\ncollector.collect_summary_data()\n```")

