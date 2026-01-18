"""
Volga持仓跟踪与调整视图
专注于二阶Greeks的持仓管理和动态调整建议
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.core import OptionsDatabase, PortfolioAnalyzer, BSCalculator
from src.utils import load_data
from views.volga_analysis import prepare_volga_data, calculate_full_pnl


def render_volga_holding_view(db: OptionsDatabase):
    """
    Volga持仓跟踪主视图
    
    :param db: 数据库对象
    """
    st.header("📈 Volga持仓跟踪与调整")
    st.caption("实时跟踪持仓的Volga/Vanna敞口，基于最新市场快照提供调整建议")
    
    with st.expander("📚 使用说明", expanded=False):
        st.markdown("""
        **功能说明**：
        1. **持仓录入**：手动输入您的当前持仓（到期日、行权价、类型、数量等）
        2. **实时快照分析**：结合最新市场快照，计算持仓的实时Volga/Vanna/Vega敞口
        3. **风险仪表盘**：展示组合的Net Volga（凸性敞口）和Net Vanna（交互敞口）
        4. **调整建议**：基于当前敞口和市场快照，提供优化建议
        
        **使用流程**：
        1. 在"Volga分析"页面找到推荐的策略组合
        2. 在交易所手动开仓
        3. 回到此页面，录入您的持仓
        4. 查看风险敞口和调整建议
        5. 根据建议调整持仓
        """)
    
    # 加载最新市场快照
    df = load_data(db, currency="ETH")
    
    if df.empty:
        st.warning("数据库中没有数据，请先采集数据")
        return
    
    # 标的价格设置
    col1, col2 = st.columns([1, 1])
    with col1:
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
    
    # 初始化持仓分析器
    if 'volga_portfolio_analyzer' not in st.session_state:
        st.session_state['volga_portfolio_analyzer'] = PortfolioAnalyzer(risk_free_rate=risk_free_rate)
        st.session_state['volga_portfolio_analyzer'].current_spot_price = spot_price
    
    analyzer = st.session_state['volga_portfolio_analyzer']
    analyzer.current_spot_price = spot_price
    
    st.divider()
    
    # 持仓录入区
    st.subheader("📝 持仓录入")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.expander("➕ 添加持仓", expanded=True):
            entry_method = st.radio(
                "录入方式",
                ["手动输入", "从数据库选择"],
                horizontal=True
            )
            
            if entry_method == "手动输入":
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    expiration_date = st.date_input("到期日", value=datetime.now().date() + timedelta(days=30))
                    strike = st.number_input("行权价", min_value=0.0, value=spot_price, step=10.0)
                with col_b:
                    option_type = st.selectbox("类型", ["C", "P"])
                    quantity = st.number_input("数量", min_value=-100, max_value=100, value=1, step=1,
                                              help="正数=买入，负数=卖出")
                with col_c:
                    entry_price = st.number_input("建仓价格", min_value=0.0, value=0.0, step=1.0,
                                                 help="实际建仓时的价格（可选）")
                    entry_iv = st.number_input("建仓IV (%)", min_value=0.0, value=50.0, step=1.0,
                                              help="建仓时的IV（百分比形式）")
                
                if st.button("添加持仓", width='stretch'):
                    analyzer.add_position(
                        expiration_date=str(expiration_date),
                        strike=strike,
                        option_type=option_type,
                        quantity=quantity,
                        volatility=entry_iv / 100.0,
                        entry_price=entry_price
                    )
                    st.success(f"已添加持仓: {quantity} {option_type} {strike:.0f} ({expiration_date})")
                    st.rerun()
            
            else:  # 从数据库选择
                # 筛选可用合约
                available_contracts = df[['instrument_name', 'strike', 'option_type', 'expiration_date', 
                                         'mark_iv', 'mark_price']].drop_duplicates()
                
                if len(available_contracts) > 0:
                    contract_options = []
                    for idx, row in available_contracts.iterrows():
                        label = f"{row['instrument_name']} | {row['strike']:.0f} {row['option_type']} | IV:{row['mark_iv']:.1f}%"
                        contract_options.append((idx, label, row))
                    
                    selected_idx = st.selectbox(
                        "选择合约",
                        options=range(len(contract_options)),
                        format_func=lambda x: contract_options[x][1] if x < len(contract_options) else "无效"
                    )
                    
                    quantity = st.number_input("数量", min_value=-100, max_value=100, value=1, step=1,
                                              key="db_quantity")
                    
                    if st.button("添加持仓", width='stretch', key="add_from_db"):
                        if 0 <= selected_idx < len(contract_options):
                            _, _, contract = contract_options[selected_idx]
                            analyzer.add_position(
                                expiration_date=str(contract['expiration_date'])[:10],
                                strike=float(contract['strike']),
                                option_type=str(contract['option_type']),
                                quantity=quantity,
                                volatility=float(contract['mark_iv']) / 100.0 if contract['mark_iv'] > 1.0 else float(contract['mark_iv']),
                                entry_price=float(contract['mark_price']) if pd.notna(contract['mark_price']) else None
                            )
                            st.success(f"已添加持仓: {quantity} {contract['option_type']} {contract['strike']:.0f}")
                            st.rerun()
    
    with col2:
        st.write("**当前持仓列表**")
        positions_df = analyzer.get_positions_df()
        
        if len(positions_df) > 0:
            st.dataframe(
                positions_df[['expiration_date', 'strike', 'option_type', 'quantity', 'volatility', 'days_to_expiry']],
                width='stretch',
                hide_index=True
            )
            
            if st.button("清空所有持仓", width='stretch'):
                analyzer.clear_positions()
                st.rerun()
            
            # 删除单个持仓
            if len(positions_df) > 0:
                st.write("**删除持仓**")
                del_idx = st.selectbox("选择要删除的持仓", options=range(len(positions_df)), 
                                      format_func=lambda x: f"#{x}: {positions_df.iloc[x]['option_type']} {positions_df.iloc[x]['strike']:.0f}")
                if st.button("删除", width='stretch'):
                    analyzer.remove_position(del_idx)
                    st.rerun()
        else:
            st.info("暂无持仓，请添加持仓")
    
    if len(analyzer.positions) == 0:
        st.info("💡 **提示**：请先添加持仓，然后查看风险分析和调整建议。")
        return
    
    st.divider()
    
    # 计算组合Greeks（使用最新市场快照的IV）
    st.subheader("📊 实时风险分析")
    
    # 准备市场快照数据（计算Volga/Vanna）
    with st.spinner("正在计算组合风险敞口..."):
        volga_df = prepare_volga_data(df, spot_price, risk_free_rate)
        
        # 更新持仓的IV（使用最新市场快照）
        updated_positions = []
        for pos in analyzer.positions:
            # 在快照中查找匹配的合约
            pos_exp_date = pd.to_datetime(pos.expiration_date).date()
            matching = volga_df[
                (volga_df['strike'] == pos.strike) &
                (volga_df['option_type'] == pos.option_type) &
                (volga_df['expiration_date'].dt.date == pos_exp_date)
            ]
            
            if len(matching) > 0:
                # 使用最新快照的IV
                latest_iv = matching.iloc[0].get('mark_iv_decimal', matching.iloc[0].get('mark_iv', pos.volatility))
                if latest_iv > 1.0:
                    latest_iv = latest_iv / 100.0
                pos.volatility = latest_iv
            updated_positions.append(pos)
        
        analyzer.positions = updated_positions
        
        # 计算组合Greeks
        portfolio_greeks = analyzer.calculate_portfolio_greeks(spot_price)
        
        # 计算组合PnL（基于当前情景）
        price_change_pct = 0.0  # 默认价格不变
        iv_change_pct = 0.0  # 默认IV不变
        
        # 计算每个持仓的PnL贡献
        portfolio_pnl_components = []
        for pos in analyzer.positions:
            pos_exp_date = pd.to_datetime(pos.expiration_date).date()
            matching = volga_df[
                (volga_df['strike'] == pos.strike) &
                (volga_df['option_type'] == pos.option_type) &
                (volga_df['expiration_date'].dt.date == pos_exp_date)
            ]
            
            if len(matching) > 0:
                contract_data = matching.iloc[0:1].copy()
                contract_data = calculate_full_pnl(contract_data, spot_price, price_change_pct, iv_change_pct)
                
                if len(contract_data) > 0:
                    contract = contract_data.iloc[0]
                    portfolio_pnl_components.append({
                        'position': f"{pos.option_type} {pos.strike:.0f}",
                        'quantity': pos.quantity,
                        'pnl_total': contract['pnl_total'] * pos.quantity,
                        'pnl_price': contract['pnl_price_total'] * pos.quantity,
                        'pnl_vol': contract['pnl_vol_total'] * pos.quantity,
                        'pnl_volga': contract['pnl_vol_volga'] * pos.quantity,
                        'pnl_interaction': contract['pnl_interaction'] * pos.quantity
                    })
        
        portfolio_pnl_df = pd.DataFrame(portfolio_pnl_components)
        total_pnl = portfolio_pnl_df['pnl_total'].sum() if len(portfolio_pnl_df) > 0 else 0.0
    
    # 风险仪表盘
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        net_volga = portfolio_greeks.get('volga', 0.0)
        volga_color = "normal" if abs(net_volga) < 100 else ("inverse" if net_volga > 0 else "off")
        st.metric("Net Volga", f"{net_volga:.2f}", 
                 delta="凸性敞口" if net_volga > 0 else "凹性敞口")
    
    with col2:
        net_vanna = portfolio_greeks.get('vanna', 0.0)
        st.metric("Net Vanna", f"{net_vanna:.6f}",
                 delta="交互敏感度")
    
    with col3:
        net_vega = portfolio_greeks.get('vega', 0.0)
        st.metric("Net Vega", f"{net_vega:.2f}",
                 delta="波动率敞口")
    
    with col4:
        volga_vega_ratio = net_volga / net_vega if abs(net_vega) > 0.01 else 0.0
        st.metric("Volga/Vega比率", f"{volga_vega_ratio:.4f}",
                 delta="凸性效率")
    
    with col5:
        vanna_vega_ratio = net_vanna / net_vega if abs(net_vega) > 0.01 else 0.0
        st.metric("Vanna/Vega比率", f"{vanna_vega_ratio:.6f}",
                 delta="交互敏感度")
    
    # 风险等级评估
    st.write("**风险等级评估**")
    risk_level = "低"
    risk_color = "green"
    risk_notes = []
    
    if abs(net_volga) > 200:
        risk_level = "高"
        risk_color = "red"
        risk_notes.append(f"Net Volga过高 ({net_volga:.2f})，凸性敞口过大")
    elif abs(net_volga) > 100:
        risk_level = "中"
        risk_color = "orange"
        risk_notes.append(f"Net Volga中等 ({net_volga:.2f})")
    
    if abs(net_vanna) > 0.01:
        if risk_level == "低":
            risk_level = "中"
            risk_color = "orange"
        risk_notes.append(f"Net Vanna较高 ({net_vanna:.6f})，价格×波动率交互敏感")
    
    if risk_level == "低":
        st.success(f"✅ **风险等级：{risk_level}** - 当前持仓的Volga/Vanna敞口在合理范围内")
    elif risk_level == "中":
        st.warning(f"⚠️ **风险等级：{risk_level}** - {'; '.join(risk_notes)}")
    else:
        st.error(f"🔴 **风险等级：{risk_level}** - {'; '.join(risk_notes)}")
    
    st.divider()
    
    # PnL归因分析
    st.subheader("💰 PnL归因分析（当前持仓）")
    
    if len(portfolio_pnl_df) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**持仓PnL明细**")
            pnl_display = portfolio_pnl_df[['position', 'quantity', 'pnl_total', 'pnl_price', 
                                           'pnl_vol', 'pnl_volga', 'pnl_interaction']].copy()
            pnl_display.columns = ['持仓', '数量', '总PnL', '价格贡献', '波动率贡献', 'Volga贡献', '交互贡献']
            pnl_display = pnl_display.round(2)
            st.dataframe(pnl_display, width='stretch', hide_index=True)
        
        with col2:
            st.write("**组合总PnL**")
            st.metric("总PnL", f"{total_pnl:.2f}")
            
            total_price_pnl = portfolio_pnl_df['pnl_price'].sum()
            total_vol_pnl = portfolio_pnl_df['pnl_vol'].sum()
            total_volga_pnl = portfolio_pnl_df['pnl_volga'].sum()
            total_interaction_pnl = portfolio_pnl_df['pnl_interaction'].sum()
            
            st.write("**归因分解**")
            st.write(f"- 价格贡献: {total_price_pnl:.2f}")
            st.write(f"- 波动率贡献: {total_vol_pnl:.2f}")
            st.write(f"- Volga贡献: {total_volga_pnl:.2f}")
            st.write(f"- 交互贡献: {total_interaction_pnl:.2f}")
    
    st.divider()
    
    # 调整建议引擎
    st.subheader("💡 调整建议")
    
    suggestions = []
    
    # 建议1: Net Volga过高
    if net_volga > 200:
        suggestions.append({
            'type': '降低Volga敞口',
            'reason': f'当前Net Volga为{net_volga:.2f}，凸性敞口过高',
            'action': '建议卖出部分高Volga合约，或买入低Volga合约对冲'
        })
    elif net_volga < -200:
        suggestions.append({
            'type': '增加Volga敞口',
            'reason': f'当前Net Volga为{net_volga:.2f}，凹性敞口过大',
            'action': '建议买入高Volga合约，或卖出低Volga合约'
        })
    
    # 建议2: Net Vanna过高
    if abs(net_vanna) > 0.01:
        suggestions.append({
            'type': '对冲Vanna敞口',
            'reason': f'当前Net Vanna为{net_vanna:.6f}，价格×波动率交互敏感',
            'action': '建议调整持仓结构，使Vanna接近中性'
        })
    
    # 建议3: Volga/Vega比率不合理
    if abs(net_vega) > 0.01:
        volga_vega_ratio = net_volga / net_vega
        if abs(volga_vega_ratio) > 2.0:
            suggestions.append({
                'type': '优化Volga/Vega比率',
                'reason': f'当前Volga/Vega比率为{volga_vega_ratio:.4f}，可能不合理',
                'action': '建议调整组合结构，使Volga/Vega比率在合理范围内（-2到2）'
            })
    
    if suggestions:
        for idx, suggestion in enumerate(suggestions, 1):
            with st.expander(f"建议 #{idx}: {suggestion['type']}", expanded=True):
                st.write(f"**原因**: {suggestion['reason']}")
                st.write(f"**行动**: {suggestion['action']}")
                
                # 尝试从市场快照中找到调整建议的具体合约
                if 'Volga' in suggestion['type']:
                    if net_volga > 0:
                        # 寻找低Volga合约（用于卖出对冲）
                        low_volga = volga_df[volga_df['volga'] < volga_df['volga'].quantile(0.3)]
                        if len(low_volga) > 0:
                            st.write("**推荐合约（用于对冲）**:")
                            for _, contract in low_volga.head(3).iterrows():
                                st.write(f"- {contract['option_type']} {contract['strike']:.0f} "
                                       f"(Volga: {contract['volga']:.2f}, Vega: {contract['vega']:.2f})")
                    else:
                        # 寻找高Volga合约（用于买入）
                        high_volga = volga_df[volga_df['volga'] > volga_df['volga'].quantile(0.7)]
                        if len(high_volga) > 0:
                            st.write("**推荐合约（用于增加敞口）**:")
                            for _, contract in high_volga.head(3).iterrows():
                                st.write(f"- {contract['option_type']} {contract['strike']:.0f} "
                                       f"(Volga: {contract['volga']:.2f}, Vega: {contract['vega']:.2f})")
    else:
        st.success("✅ **当前持仓结构良好**，无需调整建议。")
    
    st.divider()
    
    # 组合Greeks详情
    with st.expander("📊 组合Greeks详情"):
        greeks_display = {
            'Delta': portfolio_greeks['delta'],
            'Gamma': portfolio_greeks['gamma'],
            'Theta (年)': portfolio_greeks['theta'],
            'Theta (日)': portfolio_greeks['theta_daily'],
            'Vega': portfolio_greeks['vega'],
            'Rho': portfolio_greeks['rho'],
            'Vanna': portfolio_greeks.get('vanna', 0.0),
            'Volga': portfolio_greeks.get('volga', 0.0),
            '组合价值': portfolio_greeks.get('position_value', 0.0)
        }
        
        greeks_df = pd.DataFrame([greeks_display]).T
        greeks_df.columns = ['值']
        st.dataframe(greeks_df, width='stretch')

