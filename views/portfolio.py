"""
持仓组合Greeks分析视图
构建期权组合，基于BS模型计算组合Greeks，可视化风险分析
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.core import PortfolioAnalyzer


def render_portfolio_view(db):
    """
    持仓组合Greeks分析视图
    
    :param db: 数据库对象
    """
    st.header("📊 持仓组合Greeks分析")
    st.caption("构建期权组合，基于BS模型计算组合Greeks，可视化风险分析")        
    
    # 初始化组合分析器
    if 'portfolio_analyzer' not in st.session_state:
        st.session_state['portfolio_analyzer'] = PortfolioAnalyzer(risk_free_rate=0.05)
        st.session_state['portfolio_positions_count'] = 0
    
    analyzer = st.session_state['portfolio_analyzer']
    
    # 检查持仓数量是否变化，如果变化则更新计数（用于触发图表重新计算）
    current_positions_count = len(analyzer.positions)
    if 'portfolio_positions_count' not in st.session_state:
        st.session_state['portfolio_positions_count'] = current_positions_count
    elif st.session_state['portfolio_positions_count'] != current_positions_count:
        st.session_state['portfolio_positions_count'] = current_positions_count
    
    # 确保analyzer对象的状态正确同步（重要：每次获取时都重新从session_state读取）
    # 这样可以避免引用问题
    analyzer = st.session_state['portfolio_analyzer']
    
    # 侧边栏：基础参数设置
    with st.sidebar:
        st.header("⚙️ 组合参数设置")
        
        analyzer.current_spot_price = st.number_input(
            "当前标的价格",
            value=3000.0,
            step=10.0,
            help="ETH当前价格"
        )
        
        st.divider()
    
    # 创建两列布局
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🔧 组合构建器")
        
        # 策略模板
        st.write("**快速加载策略模板**")
        
        strategy_options = {
            'long_straddle': 'Long Straddle (买入跨式)',
            'short_straddle': 'Short Straddle (卖出跨式)',
            'long_strangle': 'Long Strangle (买入宽跨)',
            'short_strangle': 'Short Strangle (卖出宽跨)',
            'bull_call_spread': 'Bull Call Spread (牛市价差)',
            'bear_put_spread': 'Bear Put Spread (熊市价差)',
            'iron_condor': 'Iron Condor (铁秃鹰)',
            'butterfly': 'Butterfly (蝶式价差)'
        }
        
        selected_strategy = st.selectbox(
            "选择策略模板",
            options=list(strategy_options.keys()),
            format_func=lambda x: strategy_options[x]
        )
        
        if st.button("📥 加载模板", width='stretch'):
            try:
                analyzer.load_strategy_template(selected_strategy, analyzer.current_spot_price)
                
                # 为模板中的每个持仓设置entry_price（使用当前价格下的BS理论价格）
                for pos in analyzer.positions:
                    if pos.entry_price is None:
                        T = pos.time_to_maturity()
                        if T > 0:
                            pos.entry_price = analyzer.bs_calculator.calculate_option_price(
                                analyzer.current_spot_price,
                                pos.strike,
                                T,
                                pos.volatility,
                                pos.option_type.lower()
                            )
                
                # 显式更新session_state，确保状态同步
                st.session_state['portfolio_analyzer'] = analyzer
                # 更新持仓计数，用于触发图表重新计算
                st.session_state['portfolio_positions_count'] = len(analyzer.positions)
                st.success(f"已加载 {strategy_options[selected_strategy]}")
                st.rerun()
            except Exception as e:
                st.error(f"加载失败: {e}")
        
        st.divider()
        
        # 手动添加持仓
        st.write("**手动添加持仓**")
        
        add_col1, add_col2 = st.columns(2)
        with add_col1:
            add_expiry = st.date_input(
                "到期日",
                value=datetime.now() + timedelta(days=30)
            )
            add_strike = st.number_input(
                "行权价",
                value=float(analyzer.current_spot_price),
                step=100.0
            )
        
        with add_col2:
            add_type = st.selectbox(
                "类型",
                options=['C', 'P'],
                format_func=lambda x: 'Call' if x == 'C' else 'Put'
            )
            add_quantity = st.number_input(
                "数量",
                value=1,
                step=1,
                help="正=买，负=卖"
            )
        
        add_vol = st.slider(
            "波动率 (IV)",
            min_value=0.1,
            max_value=2.0,
            value=1.0,
            step=0.1,
            format="%.1f",
            help="输入小数形式：1.0 = 100%，0.5 = 50%，2.0 = 200%"
        )
        
        # 自动计算建仓价格（使用当前价格下的BS理论价格）
        # 这样可以确保建仓成本计算正确，PnL计算准确
        T = (add_expiry - datetime.now().date()).days / 365.0
        if T > 0:
            calculated_entry_price = analyzer.bs_calculator.calculate_option_price(
                analyzer.current_spot_price,
                add_strike,
                T,
                add_vol,
                add_type.lower()
            )
        else:
            calculated_entry_price = 0.0
        
        # 允许用户手动覆盖建仓价格（用于从数据库获取实际mark_price）
        use_custom_entry_price = st.checkbox(
            "手动指定建仓价格",
            value=False,
            help="勾选后可以手动输入建仓时的实际期权价格（mark_price）。默认使用当前价格下的BS理论价格。"
        )
        
        entry_price = calculated_entry_price
        if use_custom_entry_price:
            entry_price = st.number_input(
                "建仓价格 (entry_price)",
                min_value=0.0,
                value=calculated_entry_price,
                step=0.01,
                format="%.2f",
                help="建仓时实际支付的期权价格（mark_price），用于准确计算建仓成本和PnL"
            )
        else:
            st.caption(f"💡 将使用当前价格下的BS理论价格作为建仓价格: ${calculated_entry_price:.2f}")
        
        if st.button("➕ 添加持仓", width='stretch'):
            analyzer.add_position(
                add_expiry.strftime('%Y-%m-%d'),
                add_strike,
                add_type,
                add_quantity,
                add_vol,
                entry_price=entry_price
            )
            # 显式更新session_state，确保状态同步
            st.session_state['portfolio_analyzer'] = analyzer
            # 更新持仓计数，用于触发图表重新计算
            st.session_state['portfolio_positions_count'] = len(analyzer.positions)
            st.success(f"已添加: {add_type} {add_strike} x {add_quantity}")
            st.rerun()
        
        st.divider()
        
        if st.button("🗑️ 清空所有持仓", width='stretch'):
            analyzer.clear_positions()
            # 显式更新session_state，确保状态同步
            st.session_state['portfolio_analyzer'] = analyzer
            # 更新持仓计数，用于触发图表重新计算
            st.session_state['portfolio_positions_count'] = 0
            st.rerun()
    
    with col_right:
        st.subheader("📋 当前持仓")
        
        positions_df = analyzer.get_positions_df()
        
        if positions_df.empty:
            st.info("暂无持仓，请添加持仓或加载策略模板")
        else:
            # 显示持仓列表（带操作列）
            # 创建带删除按钮的显示表格
            display_df = positions_df.copy()
            
            # 计算每个持仓的期权价格和持仓价值
            option_prices = []
            position_values = []
            for idx, row in display_df.iterrows():
                # 找到对应的持仓对象
                pos_idx = int(row['index'])
                if pos_idx < len(analyzer.positions):
                    pos = analyzer.positions[pos_idx]
                    # 计算期权价格
                    option_price = analyzer.bs_calculator.calculate_option_price(
                        analyzer.current_spot_price,
                        pos.strike,
                        pos.time_to_maturity(),
                        pos.volatility,
                        pos.option_type.lower()
                    )
                    option_prices.append(option_price)
                    # 计算持仓价值 = 期权价格 * 数量
                    position_value = option_price * pos.quantity
                    position_values.append(position_value)
                else:
                    option_prices.append(0.0)
                    position_values.append(0.0)
            
            # 添加价格列
            display_df['option_price'] = option_prices
            display_df['position_value'] = position_values
            
            # 添加建仓价格列
            entry_prices = []
            entry_costs = []
            for idx, row in display_df.iterrows():
                pos_idx = int(row['index'])
                if pos_idx < len(analyzer.positions):
                    pos = analyzer.positions[pos_idx]
                    entry_price = pos.entry_price if pos.entry_price is not None else 0.0
                    entry_prices.append(entry_price)
                    # 建仓成本 = entry_price * quantity
                    entry_cost = entry_price * pos.quantity
                    entry_costs.append(entry_cost)
                else:
                    entry_prices.append(0.0)
                    entry_costs.append(0.0)
            
            display_df['entry_price'] = entry_prices
            display_df['entry_cost'] = entry_costs
            
            # 格式化显示
            display_df_formatted = display_df.copy()
            display_df_formatted['option_price'] = display_df_formatted['option_price'].apply(lambda x: f"${x:.2f}")
            display_df_formatted['position_value'] = display_df_formatted['position_value'].apply(lambda x: f"${x:.2f}")
            display_df_formatted['entry_price'] = display_df_formatted['entry_price'].apply(lambda x: f"${x:.2f}" if x > 0 else "未设置")
            display_df_formatted['entry_cost'] = display_df_formatted['entry_cost'].apply(lambda x: f"${x:.2f}")
            display_df_formatted['volatility'] = display_df_formatted['volatility'].apply(lambda x: f"{x*100:.1f}%")
            
            # 添加删除按钮区域
            st.write("**持仓列表**")
            st.dataframe(display_df_formatted[['index', 'expiration_date', 'strike', 'option_type', 'quantity', 
                                                'entry_price', 'entry_cost', 'option_price', 'position_value', 'volatility', 'days_to_expiry']], 
                        width='stretch', height=300,
                        column_config={
                            'index': '索引',
                            'expiration_date': '到期日',
                            'strike': st.column_config.NumberColumn('行权价', format="%.0f"),
                            'option_type': '类型',
                            'quantity': '数量',
                            'entry_price': '建仓价格',
                            'entry_cost': '建仓成本',
                            'option_price': '当前价格',
                            'position_value': '持仓价值',
                            'volatility': '波动率',
                            'days_to_expiry': '剩余天数'
                        })
            
            # 计算建仓成本总额和组合总价值
            total_cost_basis = sum(entry_costs)
            total_portfolio_value = sum(position_values)
            
            # 显示建仓成本总额和组合总价值
            st.caption(f"💡 **建仓成本总额**: ${total_cost_basis:.2f} | **组合总价值**: ${total_portfolio_value:.2f} (当前价格: ${analyzer.current_spot_price:.2f})")
            
            # 删除操作区域
            st.write("**删除持仓**")
            # 使用多列布局，每行最多5个按钮
            num_cols = min(len(positions_df), 5)
            delete_cols = st.columns(num_cols)
            
            for idx, row in positions_df.iterrows():
                col_idx = idx % num_cols
                with delete_cols[col_idx]:
                    # 显示持仓信息
                    position_info = f"{row['option_type']} {row['strike']:.0f} x{row['quantity']}"
                    position_index = int(row['index'])  # 使用DataFrame中的index列
                    
                    if st.button(
                        f"🗑️ #{position_index}",
                        key=f"delete_pos_{position_index}_{idx}",  # 使用双重key确保唯一性
                        help=f"删除持仓: {position_info}",
                        width='stretch'
                    ):
                        # 删除持仓（使用DataFrame中的index列）
                        if position_index < len(analyzer.positions):
                            removed_pos = analyzer.positions[position_index]
                            analyzer.remove_position(position_index)
                            # 显式更新session_state，确保状态同步
                            st.session_state['portfolio_analyzer'] = analyzer
                            # 更新持仓计数，用于触发图表重新计算
                            st.session_state['portfolio_positions_count'] = len(analyzer.positions)
                            st.success(f"已删除持仓: {removed_pos.option_type} {removed_pos.strike:.0f} x{removed_pos.quantity}")
                            st.rerun()
                        else:
                            st.error(f"索引错误：无法删除索引 {position_index}（当前持仓数：{len(analyzer.positions)}）")
                            st.rerun()
            
            # 如果持仓数量超过5个，显示提示
            if len(positions_df) > 5:
                st.caption(f"💡 提示：当前有 {len(positions_df)} 个持仓，删除按钮已分多行显示")
            
            # 组合摘要
            summary = analyzer.summary()
            sum_col1, sum_col2, sum_col3 = st.columns(3)
            with sum_col1:
                st.metric("总持仓数", summary['total_positions'])
            with sum_col2:
                st.metric("多头/空头", f"{summary['long_positions']}/{summary['short_positions']}")
            with sum_col3:
                st.metric("净数量", summary['net_quantity'])
    
    st.divider()
    
    # 组合分析（只有持仓时才显示）
    if not analyzer.get_positions_df().empty:
        # 计算当前Greeks
        current_greeks = analyzer.calculate_portfolio_greeks()
        
        # 显示组合IV信息
        st.subheader("📊 组合IV信息")
        positions_df = analyzer.get_positions_df()
        if not positions_df.empty and 'volatility' in positions_df.columns:
            # 计算加权平均IV（按持仓价值加权）
            # volatility存储的是小数形式（1.0表示100%）
            total_abs_value = 0.0
            weighted_iv_sum = 0.0
            
            for pos in analyzer.positions:
                # 计算该持仓的期权价格
                option_price = analyzer.bs_calculator.calculate_option_price(
                    analyzer.current_spot_price,
                    pos.strike,
                    pos.time_to_maturity(),
                    pos.volatility,
                    pos.option_type.lower()
                )
                # 持仓价值 = 期权价格 * 数量（取绝对值用于加权）
                position_value = abs(option_price * pos.quantity)
                total_abs_value += position_value
                # 累加：IV * 持仓价值
                weighted_iv_sum += pos.volatility * position_value
            
            # 加权平均IV = 总和(IV * 价值) / 总价值
            if total_abs_value > 0:
                weighted_iv = weighted_iv_sum / total_abs_value
            else:
                # 如果总价值为0，使用简单平均
                weighted_iv = sum(pos.volatility for pos in analyzer.positions) / len(analyzer.positions) if analyzer.positions else 0
            
            # 获取IV范围（volatility已经是小数形式）
            min_iv_raw = positions_df['volatility'].min()
            max_iv_raw = positions_df['volatility'].max()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("加权平均IV", f"{weighted_iv*100:.2f}%", 
                         help="按持仓价值加权的平均隐含波动率")
            with col2:
                st.metric("最低IV", f"{min_iv_raw*100:.2f}%")
            with col3:
                st.metric("最高IV", f"{max_iv_raw*100:.2f}%")
            with col4:
                iv_range = (max_iv_raw - min_iv_raw) * 100
                st.metric("IV范围", f"{iv_range:.2f}%")
        
        st.divider()
        
        # 显示当前持仓详情（调试用）
        with st.expander("🔍 当前持仓详情（用于计算）", expanded=False):
            if analyzer.positions:
                debug_df = pd.DataFrame([{
                    'index': i,
                    'option_type': pos.option_type,
                    'strike': pos.strike,
                    'quantity': pos.quantity,
                    'expiration_date': pos.expiration_date.strftime('%Y-%m-%d'),
                    'volatility': pos.volatility
                } for i, pos in enumerate(analyzer.positions)])
                st.dataframe(debug_df, width='stretch')
                st.caption(f"共 {len(analyzer.positions)} 个持仓参与计算")
            else:
                st.warning("当前没有持仓")
        
        # 显示组合Greeks（一阶Greeks）
        st.subheader("🎯 一阶Greeks（当前价格）")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Delta", f"{current_greeks['delta']:.4f}")
        with col2:
            st.metric("Gamma", f"{current_greeks['gamma']:.6f}")
        with col3:
            st.metric("Theta(日)", f"{current_greeks['theta_daily']:.4f}")
        with col4:
            st.metric("Vega", f"{current_greeks['vega']:.2f}")
        with col5:
            st.metric("Rho", f"{current_greeks['rho']:.2f}")
        with col6:
            st.metric("组合价值", f"{current_greeks['position_value']:.2f}")
        
        # 显示二阶Greeks
        st.write("**二阶Greeks**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Vanna", f"{current_greeks.get('vanna', 0.0):.6f}", 
                     help="∂Vega/∂S - Vega对价格变化的敏感性")
        with col2:
            st.metric("Volga", f"{current_greeks.get('volga', 0.0):.6f}", 
                     help="∂Vega/∂σ - Vega对波动率变化的敏感性")
        with col3:
            st.write("")  # 占位
        
        st.divider()
        
        # 情景分析参数设置
        st.subheader("⚙️ 情景分析参数")
        
        # 价格范围模式选择
        price_range_mode = st.selectbox(
            "价格范围模式",
            options=["smart", "linear", "log", "strike_based", "manual"],
            format_func=lambda x: {
                "smart": "智能范围（推荐）",
                "linear": "线性范围（0.01x-100x）",
                "log": "对数范围（0.01x-100x，对数分布）",
                "strike_based": "基于行权价（min*0.1 - max*10）",
                "manual": "手动设置"
            }[x],
            index=0,
            help="智能范围：自动根据当前价格和行权价计算合理范围"
        )
        
        # 根据模式显示不同的输入控件
        if price_range_mode == "manual":
            param_col1, param_col2, param_col3 = st.columns(3)
            with param_col1:
                spot_min = st.number_input(
                    "最低价格",
                    value=float(analyzer.current_spot_price * 0.7),
                    step=100.0,
                    min_value=0.0
                )
            with param_col2:
                spot_max = st.number_input(
                    "最高价格",
                    value=float(analyzer.current_spot_price * 1.3),
                    step=100.0,
                    min_value=0.0
                )
            with param_col3:
                num_points = st.slider(
                    "价格点数",
                    min_value=20,
                    max_value=200,
                    value=50,
                    step=10
                )
            use_log_scale = False
        else:
            # 自动计算价格范围
            calculated_min, calculated_max = analyzer.calculate_smart_price_range(price_range_mode)
            spot_min = calculated_min
            spot_max = calculated_max
            
            param_col1, param_col2 = st.columns(2)
            with param_col1:
                num_points = st.slider(
                    "价格点数",
                    min_value=20,
                    max_value=200,
                    value=50,
                    step=10,
                    help="极端范围建议使用更多点数（100-200）"
                )
            with param_col2:
                use_log_scale = st.checkbox(
                    "使用对数分布点",
                    value=(price_range_mode == "log"),
                    help="适用于极端价格范围（0.01x-100x），当前价格附近精度更高"
                )
            
            # 显示计算出的价格范围
            st.info(f"📊 价格范围：{spot_min:.2f} - {spot_max:.2f} （当前价格：{analyzer.current_spot_price:.2f}）")
        
        st.divider()
        
        # 波动率和时间调整滑杆
        st.subheader("🎛️ 情景调整")
        slider_col1, slider_col2 = st.columns(2)
        
        with slider_col1:
            volatility_change = st.slider(
                "波动率变化",
                min_value=-50,
                max_value=100,
                value=0,
                step=5,
                format="%d%%",
                help="调整所有持仓的波动率（+10%表示波动率增加10%）"
            )
            volatility_multiplier = 1.0 + volatility_change / 100.0
            if volatility_change != 0:
                st.caption(f"当前调整：{volatility_change:+.0f}% (倍数: {volatility_multiplier:.2f})")
        
        with slider_col2:
            # 计算最大剩余天数
            if not analyzer.get_positions_df().empty:
                positions_df = analyzer.get_positions_df()
                max_days = int(positions_df['days_to_expiry'].max()) if 'days_to_expiry' in positions_df.columns else 30
                max_days = min(max_days, 90)  # 上限90天
            else:
                max_days = 30
            
            time_days_offset = st.slider(
                "时间流逝",
                min_value=0,
                max_value=max_days,
                value=0,
                step=1,
                format="%d天后",
                help="模拟时间向前推进（0=当前，1=1天后，30=30天后）"
            )
            if time_days_offset > 0:
                st.caption(f"当前调整：{time_days_offset}天后")
        
        st.divider()
        
        # PnL图表显示选项
        with st.expander("⚙️ 图表显示选项", expanded=False):
            pnl_calc_mode = st.radio(
                "PnL计算模式",
                options=["到期时PnL（内在价值）", "当前PnL（含时间价值）"],
                index=0,
                help="到期时PnL：基于期权到期时的内在价值计算，显示最终盈亏（推荐）\n当前PnL：基于当前时间的期权理论价格计算，包含时间价值"
            )
            
            auto_y_range = st.checkbox(
                "自动调整PnL Y轴范围（确保零线可见）",
                value=True,
                help="勾选后，Y轴范围会自动调整以确保零线可见，方便查看亏损区域。取消勾选后，Y轴范围将完全由数据决定。"
            )
            st.caption("💡 提示：您可以使用鼠标滚轮缩放图表，或拖拽图表进行平移。双击图表可重置缩放。")
        
        st.divider()
        
        # 标签页
        tab1, tab2, tab3 = st.tabs([
            "📈 组合Greeks vs 价格",
            "⏰ 时间衰减分析",
            "🌊 波动率敏感性"
        ])
        
        with tab1:
            st.write("**组合PnL和Greeks随标的价格变化**")
            
            # 重要：在计算图表前，重新从session_state获取analyzer，确保使用最新数据
            analyzer = st.session_state['portfolio_analyzer']
            
            # 调试信息：显示实际用于计算的持仓
            with st.expander("🔍 调试信息：用于计算的持仓", expanded=False):
                st.write(f"**当前持仓数量**: {len(analyzer.positions)}")
                if analyzer.positions:
                    debug_positions = []
                    for i, pos in enumerate(analyzer.positions):
                        debug_positions.append({
                            '索引': i,
                            '到期日': pos.expiration_date.strftime('%Y-%m-%d'),
                            '行权价': pos.strike,
                            '类型': pos.option_type,
                            '数量': pos.quantity,
                            '波动率': pos.volatility,
                            '建仓价格': pos.entry_price if pos.entry_price is not None else "未设置",
                            '剩余天数': pos.days_to_expiry()
                        })
                    debug_df = pd.DataFrame(debug_positions)
                    st.dataframe(debug_df, width='stretch')
                    
                    # 计算当前Greeks用于验证
                    current_debug_greeks = analyzer.calculate_portfolio_greeks()
                    st.write("**当前价格下的组合Greeks（用于验证）:**")
                    st.json({
                        'Delta': f"{current_debug_greeks['delta']:.6f}",
                        'Gamma': f"{current_debug_greeks['gamma']:.6f}",
                        'Theta(日)': f"{current_debug_greeks['theta_daily']:.6f}",
                        'Vega': f"{current_debug_greeks['vega']:.6f}",
                        '组合价值': f"{current_debug_greeks['position_value']:.2f}"
                    })
                else:
                    st.warning("⚠️ 当前没有持仓，图表将显示空数据")
            
            # 调用greeks_vs_spot_price，传入价格范围模式、波动率和时间调整
            if price_range_mode == "manual":
                greeks_price_df = analyzer.greeks_vs_spot_price(
                    spot_min, spot_max, num_points, 
                    use_log_scale=use_log_scale,
                    volatility_multiplier=volatility_multiplier,
                    time_days_offset=time_days_offset
                )
            else:
                greeks_price_df = analyzer.greeks_vs_spot_price(
                    spot_min=None, 
                    spot_max=None, 
                    num_points=num_points,
                    price_range_mode=price_range_mode,
                    use_log_scale=use_log_scale,
                    volatility_multiplier=volatility_multiplier,
                    time_days_offset=time_days_offset
                )
            
            # 计算PnL数据
            if not greeks_price_df.empty:
                # 使用标准的建仓成本计算方法
                # 建仓成本 = Σ(entry_price × quantity)
                cost_basis = analyzer.calculate_cost_basis(analyzer.current_spot_price)
                
                # 计算最小和最大价值（用于统计信息）
                min_value = greeks_price_df['position_value'].min()
                max_value = greeks_price_df['position_value'].max()
                
                # 计算当前价格下的组合价值
                current_greeks = analyzer.calculate_portfolio_greeks(
                    analyzer.current_spot_price,
                    volatility_multiplier=volatility_multiplier,
                    time_days_offset=time_days_offset
                )
                current_value = current_greeks['position_value']
                
                # PnL计算：使用标准方法
                # PnL = 当前组合价值 - 建仓成本
                # 建仓成本 = Σ(entry_price × quantity)，其中entry_price是建仓时的实际市场价格
                greeks_price_df['pnl'] = greeks_price_df['position_value'] - cost_basis
                
                # 调试信息：显示PnL计算详情
                with st.expander("🔍 调试信息：PnL计算详情", expanded=False):
                    st.write(f"**建仓成本**: {cost_basis:.2f}")
                    st.write(f"**当前组合价值**: {current_value:.2f}")
                    st.write(f"**价格范围内最小价值**: {min_value:.2f}")
                    st.write(f"**价格范围内最大价值**: {max_value:.2f}")
                    st.write(f"**PnL最小值**: {greeks_price_df['pnl'].min():.2f}")
                    st.write(f"**PnL最大值**: {greeks_price_df['pnl'].max():.2f}")
                    st.write(f"**position_value样本** (前5个):")
                    st.dataframe(greeks_price_df[['spot_price', 'position_value', 'pnl']].head())
                
                # 保存用于显示的值
                greeks_price_df['current_value'] = current_value  # 当前价值
                greeks_price_df['cost_basis'] = cost_basis  # 建仓成本
                greeks_price_df['min_value'] = min_value  # 最小价值（用于统计）
                greeks_price_df['max_value'] = max_value  # 最大价值（用于统计）
                
                # 绘制PnL和Greeks vs 价格子图（共7个子图：PnL + 6个Greeks）
                # PnL子图使用2倍高度，让收益曲线更清晰可见
                fig = make_subplots(
                    rows=7, cols=1,
                    subplot_titles=['PnL (损益)', 'Delta', 'Gamma', 'Theta (日)', 'Vega', 'Vanna', 'Rho'],
                    shared_xaxes=True,
                    vertical_spacing=0.04,
                    row_heights=[2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]  # PnL子图高度是其他子图的2倍
                )
                
                # PnL子图（row=1）
                # 根据PnL的正负值选择不同的填充颜色
                pnl_values = greeks_price_df['pnl'].values
                has_positive = (pnl_values > 0).any()
                has_negative = (pnl_values < 0).any()
                
                if has_positive and has_negative:
                    # 有正有负：使用双色填充
                    fig.add_trace(go.Scatter(
                        x=greeks_price_df['spot_price'],
                        y=greeks_price_df['pnl'],
                        mode='lines',
                        fill='tozeroy',
                        fillcolor='rgba(46, 134, 171, 0.3)',
                        line=dict(color='#2E86AB', width=2),
                        name='PnL',
                        showlegend=False
                    ), row=1, col=1)
                else:
                    # 只有正或只有负：使用单色填充
                    fill_color = 'rgba(76, 175, 80, 0.3)' if has_positive else 'rgba(244, 67, 54, 0.3)'
                    line_color = '#4CAF50' if has_positive else '#F44336'
                    fig.add_trace(go.Scatter(
                        x=greeks_price_df['spot_price'],
                        y=greeks_price_df['pnl'],
                        mode='lines',
                        fill='tozeroy',
                        fillcolor=fill_color,
                        line=dict(color=line_color, width=2),
                        name='PnL',
                        showlegend=False
                    ), row=1, col=1)
                
                # 计算PnL范围
                pnl_min = greeks_price_df['pnl'].min()
                pnl_max = greeks_price_df['pnl'].max()
                pnl_range = pnl_max - pnl_min
                
                # 根据用户选项设置Y轴范围
                if auto_y_range:
                    # 智能设置Y轴范围：确保零线可见
                    # 如果PnL都是正的，向下扩展显示零线；如果都是负的，向上扩展显示零线
                    if pnl_min >= 0:
                        # 都是正的，向下扩展20%显示零线附近
                        y_min = -pnl_range * 0.2 if pnl_range > 0 else -abs(pnl_max) * 0.2
                        y_max = pnl_max * 1.1
                    elif pnl_max <= 0:
                        # 都是负的，向上扩展20%显示零线附近
                        y_min = pnl_min * 1.1
                        y_max = -pnl_range * 0.2 if pnl_range > 0 else abs(pnl_min) * 0.2
                    else:
                        # 有正有负，添加10%的padding
                        padding = pnl_range * 0.1 if pnl_range > 0 else abs(pnl_max - pnl_min) * 0.1
                        y_min = pnl_min - padding
                        y_max = pnl_max + padding
                    
                    # 设置PnL子图的Y轴范围，但允许用户交互式缩放
                    fig.update_yaxes(
                        range=[y_min, y_max],
                        title_text='损益 (PnL)',
                        row=1, col=1,
                        # 允许用户缩放和拖拽
                        fixedrange=False
                    )
                else:
                    # 不设置范围，让Plotly自动决定，但仍允许用户缩放
                    fig.update_yaxes(
                        title_text='损益 (PnL)',
                        row=1, col=1,
                        fixedrange=False
                    )
                
                # 当前价格线（PnL子图）
                fig.add_vline(
                    x=analyzer.current_spot_price,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="当前",
                    row=1, col=1
                )
                
                # 零线（PnL子图）- 使用更明显的样式
                fig.add_hline(
                    y=0,
                    line_dash="dot",
                    line_color="red",
                    line_width=2,
                    annotation_text="零线",
                    annotation_position="right",
                    row=1, col=1
                )
                
                # Greeks子图（row=2到row=7）
                greeks_to_plot = [
                    ('delta', 'Delta', '#2E86AB'),
                    ('gamma', 'Gamma', '#A23B72'),
                    ('theta_daily', 'Theta (日)', '#F18F01'),
                    ('vega', 'Vega', '#C73E1D'),
                    ('vanna', 'Vanna', '#9B59B6'),  # 紫色表示Vanna
                    ('rho', 'Rho', '#6A994E')
                ]
                
                for idx, (col_name, title, color) in enumerate(greeks_to_plot, 1):
                    row_num = idx + 1  # row=2到row=7
                    fig.add_trace(go.Scatter(
                        x=greeks_price_df['spot_price'],
                        y=greeks_price_df[col_name],
                        mode='lines',
                        line=dict(color=color, width=2),
                        name=title,
                        showlegend=False
                    ), row=row_num, col=1)
                    
                    # 当前价格线
                    fig.add_vline(
                        x=analyzer.current_spot_price,
                        line_dash="dash",
                        line_color="gray",
                        annotation_text="当前",
                        row=row_num, col=1
                    )
                    
                    # 零线
                    fig.add_hline(
                        y=0,
                        line_dash="dot",
                        line_color="lightgray",
                        row=row_num, col=1
                    )
                    
                    fig.update_yaxes(title_text=title, row=row_num, col=1)
                
                fig.update_xaxes(title_text='标的价格', row=7, col=1)
                
                # 添加标题说明
                title_suffix = ""
                if volatility_change != 0 or time_days_offset != 0:
                    title_suffix = " ("
                    if volatility_change != 0:
                        title_suffix += f"波动率{volatility_change:+.0f}%"
                    if time_days_offset != 0:
                        if volatility_change != 0:
                            title_suffix += ", "
                        title_suffix += f"{time_days_offset}天后"
                    title_suffix += ")"
                
                fig.update_layout(
                    title=f'组合PnL和Greeks vs 标的价格{title_suffix}',
                    hovermode='x unified',
                    template='plotly_white',
                    height=2000,  # 增加高度以适应7个子图（PnL子图更高）
                    # 启用交互式缩放和拖拽
                    dragmode='zoom',
                    # 确保所有子图都支持缩放
                    xaxis=dict(fixedrange=False)
                )
                
                # 确保所有Y轴都支持缩放（除了已经设置的PnL子图）
                for row_num in range(2, 8):
                    fig.update_yaxes(fixedrange=False, row=row_num, col=1)
                
                # 使用持仓数量作为key的一部分，确保持仓变化时图表重新渲染
                chart_key = f"portfolio_chart_{st.session_state.get('portfolio_positions_count', 0)}"
                st.plotly_chart(fig, width='stretch', key=chart_key)
                
                # PnL统计信息
                st.write("**PnL统计**")
                cost_basis = greeks_price_df['cost_basis'].iloc[0]  # 建仓成本
                current_value = greeks_price_df['current_value'].iloc[0]  # 当前价值
                
                # 计算最大亏损：使用到期时的最大亏损（这是期权组合的真实最大亏损）
                # 对于买入期权组合，最大亏损就是建仓成本（当期权价值归零时）
                max_loss_pnl = analyzer.calculate_max_loss_at_expiration(cost_basis=cost_basis)
                
                # 最大损失金额（绝对值，用于显示）
                max_loss = abs(max_loss_pnl) if max_loss_pnl < 0 else 0.0
                
                # 最大收益：使用价格范围内的最大值
                max_profit = greeks_price_df['pnl'].max()
                
                # 计算损失和收益的百分比（相对于建仓成本）
                loss_pct = (max_loss_pnl / abs(cost_basis) * 100) if cost_basis != 0 else 0
                profit_pct = (max_profit / abs(cost_basis) * 100) if cost_basis != 0 else 0
                current_pnl = current_value - cost_basis
                current_pnl_pct = (current_pnl / abs(cost_basis) * 100) if cost_basis != 0 else 0
                
                pnl_col1, pnl_col2, pnl_col3, pnl_col4, pnl_col5 = st.columns(5)
                with pnl_col1:
                    st.metric("建仓成本", f"${cost_basis:.2f}", 
                             help="建仓时支付的净权利金（最小价值，PnL基准）")
                with pnl_col2:
                    st.metric("当前价值", f"${current_value:.2f}",
                             delta=f"{current_pnl_pct:.1f}%" if cost_basis != 0 else None,
                             delta_color="normal" if current_pnl >= 0 else "inverse",
                             help=f"当前价格(${analyzer.current_spot_price:.2f})下的组合价值")
                with pnl_col3:
                    st.metric("最大价值", f"${max_value:.2f}",
                             help="价格范围内的最大组合价值")
                with pnl_col4:
                    st.metric("最大损失", f"${max_loss:.2f}", 
                             delta=f"{loss_pct:.1f}%" if cost_basis != 0 else None,
                             delta_color="inverse",
                             help=f"相对于建仓成本(${cost_basis:.2f})的最大损失")
                with pnl_col5:
                    st.metric("最大收益", f"${max_profit:.2f}",
                             delta=f"{profit_pct:.1f}%" if cost_basis != 0 else None,
                             delta_color="normal",
                             help=f"相对于建仓成本(${cost_basis:.2f})的最大收益")
                
                # 添加详细说明
                st.caption(f"💡 **说明**: PnL是相对于建仓成本(${cost_basis:.2f})计算的。"
                          f" 最大亏损是基于到期时（T=0）的内在价值计算的，这是期权组合的真实最大亏损。"
                          f" 对于买入期权组合，最大亏损通常等于建仓成本（当所有期权到期时价值归零）。")
        
        with tab2:
            st.write("**组合价值和Greeks随时间衰减**")
            
            if not analyzer.get_positions_df().empty:
                # 使用调整后的波动率和时间参数
                time_df = analyzer.time_decay_analysis(
                    num_points=num_points, 
                    spot_price=analyzer.current_spot_price
                )
                
                # 如果time_df为空，说明没有持仓或计算失败
                if time_df.empty:
                    st.warning("无法计算时间衰减数据，请确保有有效的持仓")
                else:
                    # 绘制时间衰减图
                    fig = make_subplots(
                        rows=2, cols=1,
                        subplot_titles=['组合价值随时间变化', 'Theta (日)随时间变化'],
                        shared_xaxes=True,
                        vertical_spacing=0.1
                    )
                    
                    # 组合价值
                    fig.add_trace(go.Scatter(
                        x=time_df['days_to_expiry'],
                        y=time_df['position_value'],
                        mode='lines',
                        line=dict(color='#2E86AB', width=2),
                        name='组合价值'
                    ), row=1, col=1)
                    
                    # Theta
                    fig.add_trace(go.Scatter(
                        x=time_df['days_to_expiry'],
                        y=time_df['theta_daily'],
                        mode='lines',
                        line=dict(color='#F18F01', width=2),
                        name='Theta (日)'
                    ), row=2, col=1)
                    
                    fig.update_yaxes(title_text='组合价值', row=1, col=1)
                    fig.update_yaxes(title_text='Theta (日)', row=2, col=1)
                    fig.update_xaxes(title_text='剩余天数', row=2, col=1)
                    
                    fig.update_layout(
                        title='时间衰减分析',
                        hovermode='x unified',
                        template='plotly_white',
                        height=700
                    )
                    
                    # 使用持仓数量作为key的一部分，确保持仓变化时图表重新渲染
                    chart_key_time = f"portfolio_chart_time_{st.session_state.get('portfolio_positions_count', 0)}"
                    st.plotly_chart(fig, width='stretch', key=chart_key_time)
            else:
                st.info("暂无持仓，请添加持仓或加载策略模板")
        
        with tab3:
            st.write("**组合Greeks和价值随波动率变化**")
            
            vol_change_col1, vol_change_col2 = st.columns(2)
            with vol_change_col1:
                vol_min = st.slider(
                    "IV最小变化",
                    min_value=-80,
                    max_value=0,
                    value=-50,
                    step=10,
                    format="%d%%"
                )
            with vol_change_col2:
                vol_max = st.slider(
                    "IV最大变化",
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=10,
                    format="%d%%"
                )
            
            vol_df = analyzer.volatility_sensitivity_analysis(
                (vol_min/100, vol_max/100),
                num_points,
                analyzer.current_spot_price
            )
            
            if not vol_df.empty:
                # 绘制波动率敏感性图
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=['组合价值 vs IV变化', 'Vega vs IV变化'],
                    shared_xaxes=True,
                    vertical_spacing=0.1
                )
                
                # 组合价值
                fig.add_trace(go.Scatter(
                    x=vol_df['iv_change_percent'],
                    y=vol_df['position_value'],
                    mode='lines',
                    line=dict(color='#2E86AB', width=2),
                    name='组合价值'
                ), row=1, col=1)
                
                # Vega
                fig.add_trace(go.Scatter(
                    x=vol_df['iv_change_percent'],
                    y=vol_df['vega'],
                    mode='lines',
                    line=dict(color='#C73E1D', width=2),
                    name='Vega'
                ), row=2, col=1)
                
                # 当前IV线 (0%变化)
                fig.add_vline(
                    x=0,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="当前IV"
                )
                
                fig.update_yaxes(title_text='组合价值', row=1, col=1)
                fig.update_yaxes(title_text='Vega', row=2, col=1)
                fig.update_xaxes(title_text='IV变化 (%)', row=2, col=1)
                
                fig.update_layout(
                    title='波动率敏感性分析',
                    hovermode='x unified',
                    template='plotly_white',
                    height=700
                )
                
                # 使用持仓数量作为key的一部分，确保持仓变化时图表重新渲染
                chart_key_vol = f"portfolio_chart_vol_{st.session_state.get('portfolio_positions_count', 0)}"
                st.plotly_chart(fig, width='stretch', key=chart_key_vol)

