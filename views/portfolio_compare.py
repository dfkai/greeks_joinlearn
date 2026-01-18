"""
持仓组合叠加对比分析视图
从数据库期权链中选择多个期权，叠加展示其风险指标随时间的变化
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.core import PortfolioAnalyzer, BSCalculator


def render_portfolio_compare_view(db):
    """
    持仓组合叠加对比分析视图
    
    :param db: 数据库对象
    """
    st.header("📊 持仓叠加对比分析")
    st.caption("从数据库期权链中选择多个期权，叠加展示其风险指标随时间的变化，适合精细化分析和教学演示")
    
    # 侧边栏：基础参数设置
    with st.sidebar:
        st.header("⚙️ 参数设置")
        
        spot_price = st.number_input(
            "当前标的价格",
            value=3000.0,
            step=10.0,
            help="ETH当前价格"
        )
        
        risk_free_rate = st.number_input(
            "无风险利率",
            value=0.05,
            step=0.01,
            format="%.2f",
            help="年化无风险利率"
        )
        
        st.divider()
    
    # 初始化BS计算器
    bs_calculator = BSCalculator(risk_free_rate=risk_free_rate)
    
    # 获取所有可用到期日
    exp_dates = db.get_all_expiration_dates()
    
    if not exp_dates:
        st.warning("⚠️ 数据库中没有期权链数据，请先采集数据")
        return
    
    # 到期日选择（支持多选）
    st.subheader("📅 选择到期日")
    
    from src.utils.ui_components import render_tag_selector
    
    # 初始化session_state
    if 'compare_selected_exp_dates' not in st.session_state:
        st.session_state['compare_selected_exp_dates'] = [exp_dates[0]] if exp_dates else []
    
    selected_exp_dates = render_tag_selector(
        label="选择到期日（可多选）",
        options=exp_dates,
        selected=st.session_state.get('compare_selected_exp_dates', [exp_dates[0]] if exp_dates else []),
        key_prefix="compare_exp_date",
        format_func=lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else str(x),
        allow_multiple=True  # 改为多选
    )
    
    if selected_exp_dates:
        st.session_state['compare_selected_exp_dates'] = selected_exp_dates
    
    if not selected_exp_dates:
        st.info("请选择至少一个到期日")
        return
    
    # 加载所有选中到期日的期权数据
    all_options_dfs = []
    for exp_date in selected_exp_dates:
        df = db.get_options_by_expiration(exp_date)
        if not df.empty:
            all_options_dfs.append(df)
    
    if not all_options_dfs:
        st.warning("⚠️ 选中的到期日没有期权数据")
        return
    
    options_df = pd.concat(all_options_dfs, ignore_index=True)
    
    st.caption(f"已选择 {len(selected_exp_dates)} 个到期日，共 {len(options_df)} 个期权")
    
    st.divider()
    
    # 显示期权链表格
    st.subheader("📋 期权链数据")
    
    # 准备显示数据
    display_options = []
    for idx, row in options_df.iterrows():
        # 计算当前Greeks（如果数据库中有则使用，否则用BS模型计算）
        if pd.notna(row.get('vega')) and pd.notna(row.get('gamma')):
            current_vega = row['vega']
            current_gamma = row['gamma']
        else:
            # 使用BS模型计算
            T = (pd.to_datetime(row['expiration_date']) - datetime.now()).days / 365.0
            if T > 0 and pd.notna(row.get('mark_iv')):
                try:
                    greeks = bs_calculator.calculate_all_greeks(
                        S=spot_price,
                        K=row['strike'],
                        T=T,
                        sigma=row['mark_iv'] / 100.0,  # mark_iv是百分比，需要转换为小数
                        option_type=row['option_type']
                    )
                    current_vega = greeks['vega']
                    current_gamma = greeks['gamma']
                except:
                    current_vega = 0.0
                    current_gamma = 0.0
            else:
                current_vega = 0.0
                current_gamma = 0.0
        
        # 计算剩余天数
        days_to_expiry = max((pd.to_datetime(row['expiration_date']) - datetime.now()).days, 0)
        
        display_options.append({
            'option_id': idx,
            'expiration_date': row['expiration_date'].strftime('%Y-%m-%d') if pd.notna(row['expiration_date']) else '',
            'strike': row['strike'],
            'option_type': row['option_type'],
            'mark_price': row.get('mark_price', 0.0),
            'mark_iv': row.get('mark_iv', 0.0),
            'open_interest': row.get('open_interest', 0.0),
            'volume': row.get('volume', 0.0),
            'days_to_expiry': days_to_expiry,
            'current_vega': current_vega,
            'current_gamma': current_gamma
        })
    
    display_df = pd.DataFrame(display_options)
    
    # 格式化显示
    display_df_formatted = display_df.copy()
    display_df_formatted['mark_price'] = display_df_formatted['mark_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "N/A")
    display_df_formatted['mark_iv'] = display_df_formatted['mark_iv'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) and x > 0 else "N/A")
    display_df_formatted['current_vega'] = display_df_formatted['current_vega'].apply(lambda x: f"{x:.2f}")
    display_df_formatted['current_gamma'] = display_df_formatted['current_gamma'].apply(lambda x: f"{x:.6f}")
    
    # 显示期权链表格（可展开查看）
    with st.expander("📊 查看期权链数据", expanded=True):
        st.dataframe(
            display_df_formatted[['strike', 'option_type', 'mark_price', 'mark_iv', 
                                 'days_to_expiry', 'current_vega', 'current_gamma', 'open_interest', 'volume']],
            width='stretch',
            column_config={
                'strike': st.column_config.NumberColumn('行权价', format="%.0f"),
                'option_type': '类型',
                'mark_price': '市场价格',
                'mark_iv': 'IV',
                'days_to_expiry': '剩余天数',
                'current_vega': 'Vega',
                'current_gamma': 'Gamma',
                'open_interest': st.column_config.NumberColumn('持仓量', format="%.0f"),
                'volume': st.column_config.NumberColumn('成交量', format="%.0f")
            }
        )
    
    st.divider()
    
    # 期权选择模块
    st.subheader("🔍 选择要对比的期权")
    
    # 构建期权数据
    option_data_map = {}
    calls_data = []
    puts_data = []
    
    for idx, row in display_df.iterrows():
        # 使用 option_id 确保唯一性
        option_id = row['option_id']
        # 期权标识格式：C 3000 (12-02) 或 P 2800 (12-27)
        exp_date_short = row['expiration_date'][-5:].replace('-', '/') if len(row['expiration_date']) >= 5 else row['expiration_date']
        option_label = f"{row['option_type']} {row['strike']:.0f} ({exp_date_short})"
        
        # 如果已存在相同标签，跳过（去重）
        if option_label in option_data_map:
            continue
            
        option_data_map[option_label] = {
            'option_id': option_id,
            'strike': row['strike'],
            'option_type': row['option_type'],
            'expiration_date': row['expiration_date'],
            'mark_iv': row['mark_iv'],
            'mark_price': row.get('mark_price', 0.0),  # 用于默认建仓价格
            'days_to_expiry': row['days_to_expiry'],
            'current_vega': row['current_vega'],
            'current_gamma': row['current_gamma']
        }
        
        if row['option_type'] == 'C':
            calls_data.append({
                'label': option_label,
                'strike': row['strike'],
                'iv': row['mark_iv'],
                'vega': row['current_vega'],
                'option_id': option_id,
                'expiration_date': row['expiration_date']  # 保存到期日用于排序
            })
        else:
            puts_data.append({
                'label': option_label,
                'strike': row['strike'],
                'iv': row['mark_iv'],
                'vega': row['current_vega'],
                'option_id': option_id,
                'expiration_date': row['expiration_date']  # 保存到期日用于排序
            })
    
    # 按行权价排序，同行权价按到期日排序
    calls_data.sort(key=lambda x: (x['strike'], x['expiration_date']))
    puts_data.sort(key=lambda x: (x['strike'], x['expiration_date']))
    
    # 初始化session_state
    if 'portfolio_compare_selected_options' not in st.session_state:
        st.session_state['portfolio_compare_selected_options'] = []
    
    # 快速筛选
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        strike_min = st.number_input(
            "最低行权价",
            value=float(spot_price * 0.8),
            step=50.0,
            key="compare_strike_min"
        )
    with filter_col2:
        strike_max = st.number_input(
            "最高行权价", 
            value=float(spot_price * 1.2),
            step=50.0,
            key="compare_strike_max"
        )
    
    # 过滤后的期权
    filtered_calls = [c for c in calls_data if strike_min <= c['strike'] <= strike_max]
    filtered_puts = [p for p in puts_data if strike_min <= p['strike'] <= strike_max]
    
    # 使用两列布局：Call和Put分开
    st.write("**选择期权（最多10个）**")
    
    col_call, col_put = st.columns(2)
    
    selected_labels = []
    
    with col_call:
        st.markdown("**📈 Call期权**")
        for call in filtered_calls:
            label = call['label']
            is_selected = label in st.session_state.get('portfolio_compare_selected_options', [])
            # 从label中提取到期日信息显示在复选框标签中
            # label格式: "C 3000 (12/02)"
            exp_part = label.split('(')[-1].rstrip(')')  # 提取 "12/02"
            if st.checkbox(
                f"{call['strike']:.0f} ({exp_part}) IV:{call['iv']:.1f}%",
                value=is_selected,
                key=f"call_{call['option_id']}"
            ):
                selected_labels.append(label)
    
    with col_put:
        st.markdown("**📉 Put期权**")
        for put in filtered_puts:
            label = put['label']
            is_selected = label in st.session_state.get('portfolio_compare_selected_options', [])
            # 从label中提取到期日信息显示在复选框标签中
            exp_part = label.split('(')[-1].rstrip(')')  # 提取 "12/02"
            if st.checkbox(
                f"{put['strike']:.0f} ({exp_part}) IV:{put['iv']:.1f}%",
                value=is_selected,
                key=f"put_{put['option_id']}"
            ):
                selected_labels.append(label)
    
    # 过滤掉不存在的标签
    selected_labels = [label for label in selected_labels if label in option_data_map]
    
    # 限制选择数量
    if len(selected_labels) > 10:
        st.error("⚠️ 最多只能选择10个期权，请取消部分选择")
        selected_labels = selected_labels[:10]
    
    st.session_state['portfolio_compare_selected_options'] = selected_labels
    
    # 显示已选数量
    st.caption(f"已选择 {len(selected_labels)}/10 个期权")
    
    if not selected_labels:
        st.info("💡 请至少选择一个期权进行对比分析")
        return
    
    # 显示已选期权信息（可编辑方向、数量和建仓价格）
    st.subheader("📝 配置持仓方向与数量")
    
    # 初始化视角状态（用于新添加的期权）
    if 'portfolio_compare_view_mode' not in st.session_state:
        st.session_state['portfolio_compare_view_mode'] = 'Buy'  # 默认买方视角
    
    # 初始化用户自定义方向映射（保存每个期权的用户设置）
    if 'portfolio_compare_custom_directions' not in st.session_state:
        st.session_state['portfolio_compare_custom_directions'] = {}
    
    # 视角切换按钮区域
    st.write("**🎯 视角设置**")
    view_col1, view_col2, view_col3, view_col4 = st.columns([1, 1, 1, 1])
    
    current_view_mode = st.session_state['portfolio_compare_view_mode']
    
    with view_col1:
        if st.button("📈 买方视角（默认）", 
                     use_container_width=True, 
                     help="新添加的期权默认方向为买入，已手动设置的期权不受影响",
                     type="primary" if current_view_mode == 'Buy' else "secondary"):
            st.session_state['portfolio_compare_view_mode'] = 'Buy'
            st.rerun()
    
    with view_col2:
        if st.button("📉 卖方视角（默认）", 
                     use_container_width=True, 
                     help="新添加的期权默认方向为卖出，已手动设置的期权不受影响",
                     type="primary" if current_view_mode == 'Sell' else "secondary"):
            st.session_state['portfolio_compare_view_mode'] = 'Sell'
            st.rerun()
    
    with view_col3:
        # 检查是否有已自定义的期权
        has_custom = any(label in st.session_state['portfolio_compare_custom_directions'] 
                        for label in selected_labels)
        if st.button("🔄 重置所有为当前视角", 
                     use_container_width=True,
                     disabled=not has_custom,
                     help="将所有期权方向重置为当前默认视角（买方/卖方）"):
            # 清除所有自定义方向
            for label in selected_labels:
                if label in st.session_state['portfolio_compare_custom_directions']:
                    del st.session_state['portfolio_compare_custom_directions'][label]
            # 清除编辑器状态，强制重新渲染
            if 'portfolio_compare_editor' in st.session_state:
                del st.session_state['portfolio_compare_editor']
            st.rerun()
    
    with view_col4:
        view_label = "买方" if current_view_mode == 'Buy' else "卖方"
        custom_count = sum(1 for label in selected_labels 
                          if label in st.session_state['portfolio_compare_custom_directions'])
        if custom_count > 0:
            st.caption(f"💡 默认：**{view_label}视角**<br>已自定义：{custom_count}个", unsafe_allow_html=True)
        else:
            st.caption(f"💡 默认：**{view_label}视角**")
    
    # 添加详细的使用提示
    with st.expander("💡 使用说明：如何设置期权方向", expanded=False):
        st.markdown("""
        **功能说明：**
        
        1. **默认视角设置**（上方按钮）
           - 📈 **买方视角**：新添加的期权默认方向为"买入"
           - 📉 **卖方视角**：新添加的期权默认方向为"卖出"
           - ⚠️ **重要**：切换默认视角只影响**新添加的期权**，已手动设置的期权不受影响
        
        2. **单独调整**（下方表格）
           - 在表格的"方向"列中，可以单独设置每个期权的方向（买入/卖出）
           - 一旦手动调整，该期权会被标记为"已自定义"
           - 已自定义的期权不会因为切换默认视角而改变
        
        3. **批量重置**（重置按钮）
           - 点击"🔄 重置所有为当前视角"可以将所有期权统一重置为当前默认视角
           - 仅在存在已自定义的期权时可用
        
        **使用场景示例：**
        - 场景1：大部分买入，少数卖出
          → 设置默认视角为"买方"，然后在表格中将需要卖出的期权改为"Sell"
        - 场景2：想全部重置
          → 点击"重置所有为当前视角"，所有期权统一为当前默认视角
        """)
    
    st.info("💡 **快速提示**：视角切换只影响**新添加的期权**。已手动设置方向的期权保持不变，可在下方表格中单独调整。")
    
    # 准备编辑器数据
    editor_data = []
    
    for label in selected_labels:
        data = option_data_map[label]
        # 获取市场价格作为默认建仓价格
        default_entry_price = data.get('mark_price', 0.0)
        if pd.isna(default_entry_price) or default_entry_price <= 0:
            default_entry_price = 0.0
        
        # 确定方向：优先使用用户自定义的方向，否则使用默认视角
        if label in st.session_state['portfolio_compare_custom_directions']:
            # 使用用户自定义的方向
            default_direction = st.session_state['portfolio_compare_custom_directions'][label]
        else:
            # 使用当前默认视角
            default_direction = current_view_mode
        
        # 如果编辑器已有数据，优先使用编辑器中的值（用户刚刚修改的）
        if 'portfolio_compare_editor' in st.session_state:
            editor_state = st.session_state['portfolio_compare_editor']
            if 'edited_rows' in editor_state:
                for row_idx, row_data in editor_state['edited_rows'].items():
                    if row_data.get('期权标识') == label and '方向' in row_data:
                        # 使用编辑器中的最新值
                        default_direction = row_data['方向']
                        # 保存到自定义方向映射中
                        st.session_state['portfolio_compare_custom_directions'][label] = default_direction
                        break
        
        editor_data.append({
            '期权标识': label,
            '行权价': data['strike'],
            '类型': data['option_type'],
            '到期日': data['expiration_date'],
            '方向': default_direction,
            '数量': 1.0,    # 默认数量1
            '建仓价格': float(default_entry_price)  # 用于PnL计算
        })
    
    editor_df = pd.DataFrame(editor_data)
    
    # 使用data_editor允许用户修改
    edited_df = st.data_editor(
        editor_df,
        column_config={
            "期权标识": st.column_config.TextColumn("期权合约", disabled=True, width="medium"),
            "行权价": st.column_config.NumberColumn("行权价", disabled=True, format="%.0f"),
            "类型": st.column_config.TextColumn("类型", disabled=True),
            "到期日": st.column_config.TextColumn("到期日", disabled=True),
            "方向": st.column_config.SelectboxColumn(
                "方向",
                options=["Buy", "Sell"],
                required=True,
                help="买入(Long)或卖出(Short)"
            ),
            "数量": st.column_config.NumberColumn(
                "数量",
                min_value=0.1,
                max_value=10000.0,
                step=1.0,
                format="%.1f",
                required=True
            ),
            "建仓价格": st.column_config.NumberColumn(
                "建仓价格",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                help="用于计算PnL的建仓价格"
            )
        },
        hide_index=True,
        width='stretch',
        key="portfolio_compare_editor"
    )
    
    # 创建配置映射，方便后续查找
    config_map = {}
    for _, row in edited_df.iterrows():
        label = row['期权标识']
        direction = row['方向']
        
        # 保存用户自定义的方向（如果与默认视角不同，或者之前已经自定义过）
        if label in st.session_state['portfolio_compare_custom_directions']:
            # 如果之前已经自定义过，更新自定义值
            st.session_state['portfolio_compare_custom_directions'][label] = direction
        elif direction != current_view_mode:
            # 如果用户修改的方向与默认视角不同，保存为自定义
            st.session_state['portfolio_compare_custom_directions'][label] = direction
        
        config_map[label] = {
            'direction': direction,
            'quantity': row['数量'],
            'entry_price': row['建仓价格']
        }
    
    # 清理已删除的期权的自定义方向（如果某个期权不再被选中，清除其自定义设置）
    if 'portfolio_compare_custom_directions' in st.session_state:
        keys_to_remove = [key for key in st.session_state['portfolio_compare_custom_directions'].keys() 
                          if key not in selected_labels]
        for key in keys_to_remove:
            del st.session_state['portfolio_compare_custom_directions'][key]
    
    st.divider()
    
    # 情景分析参数设置
    st.subheader("⚙️ 情景分析参数")
    
    # 价格范围设置
    param_col1, param_col2, param_col3 = st.columns(3)
    with param_col1:
        spot_min = st.number_input(
            "最低价格",
            value=float(spot_price * 0.7),
            step=100.0,
            min_value=0.0
        )
    with param_col2:
        spot_max = st.number_input(
            "最高价格",
            value=float(spot_price * 1.3),
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
    
    st.info(f"📊 价格范围：{spot_min:.2f} - {spot_max:.2f} （当前价格：{spot_price:.2f}）")
    
    st.divider()
    
    # 情景调整滑杆
    st.subheader("🎛️ 情景调整")
    
    # 计算最大剩余天数
    selected_option_ids = [option_data_map[label]['option_id'] for label in selected_labels]
    max_days_selected = int(display_df[display_df['option_id'].isin(selected_option_ids)]['days_to_expiry'].max())
    max_days_selected = min(max_days_selected, 90) if max_days_selected > 0 else 30  # 上限90天，默认30天
    
    slider_col1, slider_col2 = st.columns(2)
    
    with slider_col1:
        time_days_offset = st.slider(
            "从当前起已过天数",
            min_value=0,
            max_value=max_days_selected,
            value=0,
            step=1,
            format="%d天",
            help="模拟时间向前推进（0=当前，1=1天后，30=30天后）"
        )
    
    with slider_col2:
        volatility_change = st.slider(
            "波动率变化",
            min_value=-50,
            max_value=100,
            value=0,
            step=5,
            format="%d%%",
            help="调整所有期权的波动率（+10%表示波动率增加10%）"
        )
    
    # 计算波动率倍数
    volatility_multiplier = 1.0 + volatility_change / 100.0
    
    # 显示当前调整状态
    adjustment_info = []
    if time_days_offset > 0:
        adjustment_info.append(f"时间+{time_days_offset}天")
    if volatility_change != 0:
        adjustment_info.append(f"波动率{volatility_change:+d}%")
    
    if adjustment_info:
        st.caption(f"当前调整：{', '.join(adjustment_info)}")
    
    st.divider()
    
    # 指标选择与图表展示
    st.subheader("📈 指标选择与图表展示")
    
    # 定义要显示的指标（PnL在最上面，然后是Greeks）
    metric_configs = [
        ('pnl', 'PnL (损益)', '#2E86AB'),
        ('delta', 'Delta', '#1B998B'),
        ('gamma', 'Gamma', '#A23B72'),
        ('theta_daily', 'Theta (日)', '#F18F01'),
        ('vega', 'Vega', '#C73E1D'),
        ('volga', 'Volga', '#9B59B6')
    ]
    
    # 生成价格序列
    spot_range = np.linspace(spot_min, spot_max, num_points)
    
    # 收集所有期权的行权价（用于图表参考线）
    all_strikes = set()
    
    # 为每个选中的期权计算价格曲线数据
    curves_data = []
    for label in selected_labels:
        option_info = option_data_map[label]
        
        # 获取用户配置的方向、数量和建仓价格
        user_config = config_map.get(label, {'direction': 'Buy', 'quantity': 1.0, 'entry_price': 0.0})
        direction = user_config['direction']
        quantity = user_config['quantity']
        entry_price = user_config.get('entry_price', 0.0)
        # 根据方向确定符号：Buy为正，Sell为负
        sign = 1.0 if direction == 'Buy' else -1.0
        signed_quantity = quantity * sign
        
        strike = option_info['strike']
        all_strikes.add(strike)  # 收集行权价
        option_type = option_info['option_type']
        expiration_date = pd.to_datetime(option_info['expiration_date'])
        base_iv = option_info['mark_iv'] / 100.0 if option_info['mark_iv'] > 0 else 1.0
        # 应用波动率调整
        adjusted_iv = base_iv * volatility_multiplier
        
        # 计算调整后的日期
        adjusted_date = datetime.now() + timedelta(days=time_days_offset)
        remaining_days = max((expiration_date - adjusted_date).days, 0)
        T = remaining_days / 365.0
        
        # 构建期权标识（包含方向信息和到期日）
        direction_label = "买" if direction == 'Buy' else "卖"
        exp_short = option_info['expiration_date'][-5:].replace('-', '/') if len(option_info['expiration_date']) >= 5 else ''
        option_label = f"{direction_label}{quantity:.0f} {option_type} {strike:.0f} ({exp_short})"
        
        # 计算建仓成本（用于PnL计算）
        entry_cost = entry_price * signed_quantity
        
        # 计算该期权在不同价格下的Greeks和PnL
        price_points = []
        for spot in spot_range:
            if T <= 0.001:
                # 已到期，使用内在价值
                if option_type.upper() == 'C':
                    intrinsic_value = max(spot - strike, 0.0)
                    delta = 1.0 if spot > strike else 0.0
                else:
                    intrinsic_value = max(strike - spot, 0.0)
                    delta = -1.0 if spot < strike else 0.0
                
                option_price = intrinsic_value
                greeks = {
                    'delta': delta * signed_quantity,
                    'gamma': 0.0,
                    'theta_daily': 0.0,
                    'vega': 0.0,
                    'volga': 0.0
                }
            else:
                # 使用BS模型计算Greeks（应用调整后的波动率）
                try:
                    raw_greeks = bs_calculator.calculate_all_greeks(
                        S=spot,
                        K=strike,
                        T=T,
                        sigma=adjusted_iv,  # 使用调整后的波动率
                        option_type=option_type
                    )
                    option_price = raw_greeks['price']
                    # 应用方向和数量调整
                    greeks = {
                        'delta': raw_greeks['delta'] * signed_quantity,
                        'gamma': raw_greeks['gamma'] * signed_quantity,
                        'theta_daily': raw_greeks['theta'] / 365.0 * signed_quantity,
                        'vega': raw_greeks['vega'] * signed_quantity,
                        'volga': raw_greeks.get('volga', 0.0) * signed_quantity
                    }
                except:
                    option_price = 0.0
                    greeks = {
                        'delta': 0.0,
                        'gamma': 0.0,
                        'theta_daily': 0.0,
                        'vega': 0.0,
                        'volga': 0.0
                    }
            
            # 计算PnL：当前价值 - 建仓成本
            current_value = option_price * signed_quantity
            pnl = current_value - entry_cost
            
            price_points.append({
                'spot_price': spot,
                'pnl': pnl,
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta_daily': greeks['theta_daily'],
                'vega': greeks['vega'],
                'volga': greeks.get('volga', 0.0)
            })
        
        curves_data.append({
            'option_label': option_label,
            'option_type': option_type,
            'strike': strike,
            'direction': direction,
            'data': pd.DataFrame(price_points)
        })
    
    # 创建多个子图（垂直排列）
    fig = make_subplots(
        rows=len(metric_configs), cols=1,
        subplot_titles=[config[1] for config in metric_configs],
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[1.0] * len(metric_configs)
    )
    
    # 颜色方案：Call用蓝色系，Put用红色系
    # Buy用实线，Sell用虚线
    call_colors = ['#2E86AB', '#1B998B', '#2D9CDB', '#56CCF2', '#6FCF97']
    put_colors = ['#C73E1D', '#E63946', '#F18F01', '#FF6B6B', '#FF8C42']
    
    # 为每个指标创建子图
    for metric_idx, (metric_key, metric_name, metric_color) in enumerate(metric_configs):
        row_num = metric_idx + 1
        
        # 为每个期权添加曲线
        for curve_idx, curve_info in enumerate(curves_data):
            df = curve_info['data']
            option_label = curve_info['option_label']
            option_type = curve_info['option_type']
            direction = curve_info.get('direction', 'Buy')
            
            # 选择颜色：Call用蓝色系，Put用红色系
            if option_type.upper() == 'C':
                color = call_colors[curve_idx % len(call_colors)]
            else:
                color = put_colors[curve_idx % len(put_colors)]
            
            # 选择线型：Buy用实线，Sell用虚线
            line_style = 'solid' if direction == 'Buy' else 'dash'
            
            # 添加曲线到对应的子图
            fig.add_trace(go.Scatter(
                x=df['spot_price'],
                y=df[metric_key],
                mode='lines',
                name=option_label,
                line=dict(color=color, width=2, dash=line_style),
                showlegend=(metric_idx == 0),  # 只在第一个子图显示图例
                legendgroup=option_label,
                hovertemplate=f'<b>{option_label}</b><br>' +
                             '标的价格: %{x:.2f}<br>' +
                             f'{metric_name}: %{{y:.4f}}<br>' +
                             '<extra></extra>'
            ), row=row_num, col=1)
        
        # 添加零线（每个子图只添加一次）
        fig.add_hline(
            y=0,
            line_dash="dot",
            line_color="lightgray",
            row=row_num, col=1
        )
        
        # 添加当前价格参考线（只在第一个子图添加标注）
        if metric_idx == 0:
            fig.add_vline(
                x=spot_price,
                line_dash="dash",
                line_color="gray",
                annotation_text="当前",
                annotation_position="top",
                row=row_num, col=1
            )
        else:
            fig.add_vline(
                x=spot_price,
                line_dash="dash",
                line_color="gray",
                row=row_num, col=1
            )
        
        # 添加行权价参考线（只在第一个子图添加标注）
        for strike_idx, strike in enumerate(sorted(all_strikes)):
            if spot_min <= strike <= spot_max:  # 只显示在价格范围内的行权价
                if metric_idx == 0:
                    fig.add_vline(
                        x=strike,
                        line_dash="dot",
                        line_color="rgba(150, 150, 150, 0.5)",
                        annotation_text=f"K={strike:.0f}",
                        annotation_position="top" if strike_idx % 2 == 0 else "bottom",
                        row=row_num, col=1
                    )
                else:
                    fig.add_vline(
                        x=strike,
                        line_dash="dot",
                        line_color="rgba(150, 150, 150, 0.5)",
                        row=row_num, col=1
                    )
        
        # 更新Y轴标签
        fig.update_yaxes(title_text=metric_name, row=row_num, col=1)
    
    # 更新X轴标签（只在最后一个子图）
    fig.update_xaxes(title_text='标的价格', row=len(metric_configs), col=1)
    
    # 添加标题说明
    title_parts = []
    if time_days_offset != 0:
        title_parts.append(f"已过{time_days_offset}天")
    if volatility_change != 0:
        title_parts.append(f"波动率{volatility_change:+d}%")
    title_suffix = f"（{', '.join(title_parts)}）" if title_parts else ""
    
    fig.update_layout(
        title=f'所选期权PnL和Greeks vs 标的价格对比{title_suffix}',
        hovermode='x unified',
        template='plotly_white',
        height=300 * len(metric_configs),  # 调整高度，使图表更紧凑
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        # 启用交互式缩放和拖拽
        dragmode='zoom',
        xaxis=dict(fixedrange=False)
    )
    
    # 确保所有Y轴都支持缩放
    for row_num in range(1, len(metric_configs) + 1):
        fig.update_yaxes(fixedrange=False, row=row_num, col=1)
    
    st.plotly_chart(fig, width='stretch')
    
    # 显示当前价格点的详细数据
    st.subheader("📊 当前价格点详细数据")
    
    current_data = []
    total_pnl = 0.0
    total_delta = 0.0
    total_gamma = 0.0
    total_vega = 0.0
    
    for label in selected_labels:
        option_info = option_data_map[label]
        
        # 获取用户配置的方向、数量和建仓价格
        user_config = config_map.get(label, {'direction': 'Buy', 'quantity': 1.0, 'entry_price': 0.0})
        direction = user_config['direction']
        quantity = user_config['quantity']
        entry_price = user_config.get('entry_price', 0.0)
        sign = 1.0 if direction == 'Buy' else -1.0
        signed_quantity = quantity * sign
        
        strike = option_info['strike']
        option_type = option_info['option_type']
        expiration_date = pd.to_datetime(option_info['expiration_date'])
        base_iv = option_info['mark_iv'] / 100.0 if option_info['mark_iv'] > 0 else 1.0
        adjusted_iv = base_iv * volatility_multiplier  # 应用波动率调整
        
        # 计算调整后的日期
        adjusted_date = datetime.now() + timedelta(days=time_days_offset)
        remaining_days = max((expiration_date - adjusted_date).days, 0)
        T = remaining_days / 365.0
        
        # 计算建仓成本
        entry_cost = entry_price * signed_quantity
        
        if T <= 0.001:
            if option_type.upper() == 'C':
                intrinsic_value = max(spot_price - strike, 0.0)
                delta = 1.0 if spot_price > strike else 0.0
            else:
                intrinsic_value = max(strike - spot_price, 0.0)
                delta = -1.0 if spot_price < strike else 0.0
            option_price = intrinsic_value
            greeks = {
                'vega': 0.0,
                'gamma': 0.0,
                'volga': 0.0,
                'delta': delta * signed_quantity,
                'theta_daily': 0.0
            }
        else:
            try:
                raw_greeks = bs_calculator.calculate_all_greeks(
                    S=spot_price,
                    K=strike,
                    T=T,
                    sigma=adjusted_iv,  # 使用调整后的波动率
                    option_type=option_type
                )
                option_price = raw_greeks['price']
                greeks = {
                    'delta': raw_greeks['delta'] * signed_quantity,
                    'gamma': raw_greeks['gamma'] * signed_quantity,
                    'theta_daily': raw_greeks['theta'] / 365.0 * signed_quantity,
                    'vega': raw_greeks['vega'] * signed_quantity,
                    'volga': raw_greeks.get('volga', 0.0) * signed_quantity
                }
            except:
                option_price = 0.0
                greeks = {
                    'vega': 0.0,
                    'gamma': 0.0,
                    'volga': 0.0,
                    'delta': 0.0,
                    'theta_daily': 0.0
                }
        
        # 计算PnL
        current_value = option_price * signed_quantity
        pnl = current_value - entry_cost
        
        # 累加汇总值
        total_pnl += pnl
        total_delta += greeks['delta']
        total_gamma += greeks['gamma']
        total_vega += greeks['vega']
        
        direction_label = "买" if direction == 'Buy' else "卖"
        exp_short = option_info['expiration_date'][-5:].replace('-', '/') if len(option_info['expiration_date']) >= 5 else ''
        current_data.append({
            '期权标识': f"{direction_label}{quantity:.0f} {option_type} {strike:.0f} ({exp_short})",
            '方向': direction_label,
            '数量': quantity,
            '建仓价': f"{entry_price:.2f}",
            '已过天数': time_days_offset,
            '剩余天数': remaining_days,
            'PnL': f"{pnl:.2f}",
            'Delta': f"{greeks['delta']:.4f}",
            'Gamma': f"{greeks['gamma']:.6f}",
            'Vega': f"{greeks['vega']:.2f}"
        })
    
    current_df = pd.DataFrame(current_data)
    st.dataframe(current_df, width='stretch', hide_index=True)
    
    # 显示汇总数据
    st.subheader("📊 组合汇总")
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    with summary_col1:
        pnl_color = "green" if total_pnl >= 0 else "red"
        st.metric("组合PnL", f"${total_pnl:.2f}", delta_color="normal")
    with summary_col2:
        st.metric("组合Delta", f"{total_delta:.4f}")
    with summary_col3:
        st.metric("组合Gamma", f"{total_gamma:.6f}")
    with summary_col4:
        st.metric("组合Vega", f"{total_vega:.2f}")
