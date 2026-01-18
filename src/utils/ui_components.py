"""
UI组件模块
包含可复用的Streamlit UI组件
"""

import streamlit as st


def render_tag_selector(label: str, options: list, selected: list, 
                        key_prefix: str, format_func=None, allow_multiple: bool = False, 
                        min_selected: int = 0) -> list:
    """
    渲染标签式选择器
    
    :param label: 标签文本
    :param options: 选项列表
    :param selected: 当前选中的选项列表
    :param key_prefix: session_state键前缀
    :param format_func: 格式化函数
    :param allow_multiple: 是否允许多选
    :param min_selected: 最少需要选中的数量（多选模式下，如果取消后少于这个数量，则不允许取消）
    :return: 选中的选项列表
    """
    st.write(f"**{label}**")
    
    # 初始化session_state（使用哈希值作为key的一部分，避免特殊字符问题）
    state_key = f"{key_prefix}_selected"
    if state_key not in st.session_state:
        if allow_multiple:
            # 多选模式：使用传入的selected列表
            st.session_state[state_key] = selected.copy() if selected else []
        else:
            # 单选模式：只保留第一个
            st.session_state[state_key] = ([selected[0]] if selected else [])
    
    # 渲染标签按钮
    # 根据选项数量决定每行显示的标签数（优化布局）
    if len(options) > 50:
        num_cols = 15  # 大量选项时使用15列
    elif len(options) > 20:
        num_cols = 12  # 中等数量使用12列
    else:
        num_cols = min(len(options), 10) if len(options) > 5 else len(options)
    
    cols = st.columns(num_cols)
    current_selected = st.session_state.get(state_key, [])
    
    for idx, option in enumerate(options):
        col_idx = idx % num_cols
        # 使用索引作为button key，避免特殊字符问题
        button_key = f"{key_prefix}_btn_{idx}"
        
        with cols[col_idx]:
            # 格式化显示文本
            display_text = format_func(option) if format_func else str(option)
            
            # 确定按钮样式
            is_selected = option in current_selected
            button_type = "primary" if is_selected else "secondary"
            
            # 创建按钮
            if st.button(
                display_text,
                key=button_key,
                type=button_type,
                width='stretch'
            ):
                # 切换选中状态
                if allow_multiple:
                    # 多选模式：切换当前选项
                    if option in current_selected:
                        # 检查是否允许取消（至少保留min_selected个）
                        if len(current_selected) > min_selected:
                            current_selected.remove(option)
                        elif min_selected == 0:
                            # 如果min_selected为0，允许完全取消
                            current_selected.remove(option)
                        else:
                            # 如果已经是最少数量，不允许取消，显示提示
                            st.warning(f"至少需要选择 {min_selected} 个选项")
                            # 不更新状态，直接返回
                            return current_selected
                    else:
                        current_selected.append(option)
                else:
                    # 单选模式：只选中当前选项
                    current_selected = [option]
                
                # 更新session_state
                st.session_state[state_key] = current_selected.copy()  # 使用copy避免引用问题
                st.rerun()
    
    # 如果是单选模式但没有选中任何选项，默认选择第一个
    if not allow_multiple and not current_selected and options:
        current_selected = [options[0]]
        st.session_state[state_key] = current_selected
    
    return current_selected.copy()  # 返回副本避免外部修改影响内部状态

