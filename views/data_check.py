"""
数据完整性检查视图
检查数据库中是否完整下载了所有期权数据
"""

import streamlit as st
import pandas as pd
import logging
import os
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

    # 检测 Demo 模式
    DEMO_MODE = os.getenv('ENABLE_DATA_COLLECTION', 'true').lower() != 'true'

    if DEMO_MODE:
        # Demo 模式：显示完整的本地部署教程
        st.warning("⚠️ **演示模式限制**：数据完整性检查需要调用 Deribit API，在演示模式下已禁用")

        st.divider()

        # 完整教程
        st.success("💡 **如何启用完整功能？** 本地部署只需 5 分钟！")

        with st.container():
            st.markdown("""
            ## 📦 本地部署步骤

            ### 步骤 1️⃣：克隆项目

            ```bash
            git clone https://github.com/dfkai/greeks_joinlearn.git
            cd greeks_joinlearn
            ```

            ### 步骤 2️⃣：安装依赖

            ```bash
            pip install -r requirements.txt
            ```

            ### 步骤 3️⃣：获取 Deribit API 凭证

            1. 访问 **[Deribit 测试环境](https://test.deribit.com/)** （推荐先用测试环境）
            2. 注册并登录账户
            3. 进入 **Account → API**
            4. 点击 **Create new API key**
            5. 权限选择：勾选 **Read** （只需读权限）
            6. 复制生成的 `Client ID` 和 `Client Secret`

            ### 步骤 4️⃣：配置 API 凭证（只需编辑一个文件！）

            ```bash
            # 复制示例文件
            cp .env.example .env

            # 编辑 .env 文件
            nano .env  # 或用任何文本编辑器
            ```

            在 `.env` 文件中，填入你的凭证（**只需改这两行**）：

            ```bash
            DERIBIT_CLIENT_ID_TEST=粘贴你的_Client_ID
            DERIBIT_CLIENT_SECRET_TEST=粘贴你的_Client_Secret
            ```

            ### 步骤 5️⃣：启动应用

            ```bash
            streamlit run app.py
            ```

            访问：http://localhost:8501

            ---

            ## 🎉 完成！现在你可以：

            - ✅ **实时数据采集** - 从 Deribit 抓取最新期权数据
            - ✅ **数据完整性检查** - 对比 API 和数据库，确保无遗漏
            - ✅ **历史数据积累** - 数据存储在本地，随时分析
            - ✅ **完全私有** - 所有数据和凭证仅在你的电脑上

            ---

            ## 🔒 安全提示

            - ✅ `.env` 文件已被 Git 忽略，**不会上传到 GitHub**
            - ✅ 你的 API 凭证仅存储在本地
            - ✅ 数据完全私有，不会发送到任何第三方服务器

            ---

            ## ❓ 常见问题

            **Q: 需要付费吗？**
            A: 不需要！Deribit 测试环境完全免费，数据和真实环境一致。

            **Q: 需要配置多个文件吗？**
            A: 不需要！只需要编辑 `.env` 文件，填入两行凭证即可。

            **Q: 数据会丢失吗？**
            A: 不会。数据存储在本地 DuckDB 数据库，关闭应用后仍然保留。
            """)

        return  # Demo 模式下直接返回，不执行后续检查逻辑

    # 完整功能模式：显示正常的检查界面
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

