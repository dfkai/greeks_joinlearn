"""
数据完整性检查视图
检查数据库中是否完整下载了所有期权数据
"""

import streamlit as st
import pandas as pd
import logging
from src.core import OptionsDatabase
from src.collectors import DataCompletenessChecker

logger = logging.getLogger(__name__)


def render_data_check_view(db: OptionsDatabase, db_path: str):
    """
    数据完整性检查视图页面
    
    :param db: 数据库对象
    :param db_path: 数据库文件路径
    """
    st.header("🔍 数据完整性检查")
    st.caption("检查数据库中是否完整下载了Deribit上所有ETH期权数据")
    
    # 检查按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 开始检查", type="primary", width='stretch'):
            st.session_state['run_completeness_check'] = True
    
    # 执行检查
    if st.session_state.get('run_completeness_check', False):
        with st.spinner("正在检查数据完整性，请稍候..."):
            checker = None
            try:
                # 注意：这里创建新的数据库连接，因为app.py中的db连接是缓存的
                # 如果数据库文件被占用，会在这里抛出异常
                checker = DataCompletenessChecker(currency="ETH", db_path=db_path)
                report = checker.check_completeness()
                
                # 存储报告到session state
                st.session_state['completeness_report'] = report
                st.session_state['run_completeness_check'] = False
                
            except Exception as e:
                error_msg = str(e)
                if "另一个程序" in error_msg or "another process" in error_msg.lower() or "cannot open file" in error_msg.lower():
                    st.error("❌ 数据库文件被占用！请关闭其他正在使用该数据库的程序（如其他Streamlit实例），然后重试。")
                    st.info("💡 提示：如果之前有Streamlit应用在运行，请先停止它，然后刷新页面重试。")
                else:
                    st.error(f"检查失败: {e}")
                logger.error(f"数据完整性检查失败: {e}", exc_info=True)
                st.session_state['run_completeness_check'] = False
            finally:
                # 确保关闭数据库连接
                if checker:
                    try:
                        checker.close()
                    except:
                        pass
    
    # 显示报告
    if 'completeness_report' in st.session_state:
        report = st.session_state['completeness_report']
        
        if 'error' in report:
            st.error(f"检查出错: {report['error']}")
            return
        
        summary = report.get('summary', {})
        
        # 摘要卡片
        st.subheader("📊 检查摘要")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("API总数", summary.get('api_total', 0))
        with col2:
            st.metric("已存储", summary.get('stored_total', 0))
        with col3:
            st.metric("缺失数量", summary.get('missing_count', 0))
        with col4:
            coverage = summary.get('coverage_rate', 0)
            st.metric("覆盖率", f"{coverage:.2f}%")
        
        # 完整性状态
        st.divider()
        if summary.get('missing_count', 0) == 0:
            st.success("✅ 数据完整！所有ETH期权数据已下载")
        else:
            st.warning(f"⚠️ 发现 {summary.get('missing_count', 0)} 个缺失的期权")
        
        # 缺失的期权列表
        if summary.get('missing_count', 0) > 0:
            st.subheader("📋 缺失的期权列表")
            missing_list = report.get('missing_instruments', [])
            
            # 显示前100个
            if len(missing_list) > 100:
                st.info(f"显示前100个缺失的期权（共{summary.get('missing_count', 0)}个）")
            
            # 创建DataFrame显示
            missing_df = pd.DataFrame({
                'instrument_name': missing_list[:100]
            })
            st.dataframe(missing_df, width='stretch', height=400)
        
        # 过期的期权列表
        if summary.get('expired_count', 0) > 0:
            st.subheader("⏰ 过期的期权列表（数据库中存在但API中已不存在）")
            expired_list = report.get('expired_instruments', [])
            
            if len(expired_list) > 100:
                st.info(f"显示前100个过期的期权（共{summary.get('expired_count', 0)}个）")
            
            expired_df = pd.DataFrame({
                'instrument_name': expired_list[:100]
            })
            st.dataframe(expired_df, width='stretch', height=300)
        
        # 按维度统计
        dim_analysis = report.get('dimension_analysis', {})
        if any(dim_analysis.values()):
            st.subheader("📈 按维度统计缺失情况")
            
            # 按到期日统计
            if dim_analysis.get('by_expiration'):
                st.write("**按到期日统计：**")
                exp_df = pd.DataFrame(
                    list(dim_analysis['by_expiration'].items()),
                    columns=['到期日', '缺失数量']
                ).sort_values('缺失数量', ascending=False)
                st.dataframe(exp_df, width='stretch')
            
            # 按行权价范围统计
            if dim_analysis.get('by_strike_range'):
                st.write("**按行权价范围统计：**")
                strike_df = pd.DataFrame(
                    list(dim_analysis['by_strike_range'].items()),
                    columns=['行权价范围', '缺失数量']
                ).sort_values('行权价范围')
                st.dataframe(strike_df, width='stretch')
            
            # 按期权类型统计
            if dim_analysis.get('by_option_type'):
                st.write("**按期权类型统计：**")
                type_df = pd.DataFrame(
                    list(dim_analysis['by_option_type'].items()),
                    columns=['期权类型', '缺失数量']
                )
                st.dataframe(type_df, width='stretch')
        
        # 检查时间
        st.caption(f"检查时间: {report.get('check_time', 'N/A')}")

