"""
任务五：Streamlit基础页面搭建
主应用文件 - 路由控制器
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import os
from src.collectors import DataCollector
from src.core import OptionsDatabase

# 导入工具模块
from src.utils import load_database, apply_custom_css, init_posthog, track_page_view, track_data_collection

# 导入视图模块
from views.dashboard import render_dashboard_view
from views.cross_section import render_cross_section_view
from views.time_series import render_time_series_view
from views.portfolio import render_portfolio_view
from views.portfolio_compare import render_portfolio_compare_view
from views.data_check import render_data_check_view
from views.volga_analysis import render_volga_analysis_view
from views.volga_holding import render_volga_holding_view

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="Deribit期权链数据分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用自定义CSS样式
apply_custom_css()


def main():
    """主应用函数 - 路由控制器"""

    # 初始化 PostHog 分析（仅在启用时生效）
    init_posthog()

    # 检测是否为 Demo 模式
    DEMO_MODE = os.getenv('ENABLE_DATA_COLLECTION', 'true').lower() != 'true'

    # 页面标题
    st.markdown("""
        <div class="brand-container">
            <div class="brand-icon">📊</div>
            <div class="header-text-group">
                <div class="main-header">
                    期权希腊值的多维学习（以 Deribit ETH 期权为例）
                </div>
                <div class="sub-header">
                    <a href="https://joinlearn.com" target="_blank" class="author-link" title="Visit joinlearn.com" style="text-decoration: none; color: inherit;">
                        <span class="author-tag">就学｜joinlearn.com 出品</span>
                    </a>
                    <span style="margin: 0 10px; opacity: 0.5;">|</span>
                    <a href="https://github.com/dfkai" target="_blank" class="author-link" title="Visit dfkai's GitHub">
                        <span class="author-tag">by dfkai@github</span>
                    </a>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Demo 模式横幅提示
    if DEMO_MODE:
        st.info("""
        📊 **在线演示模式** - 您正在查看预加载的示例数据快照

        💡 **如需完整功能**（实时数据采集、自定义分析）：

        👉 **请在左侧导航栏选择 "数据完整性检查" 查看完整部署教程**
        """)
        st.divider()
    
    # 页面导航
    page = st.sidebar.selectbox(
        "选择页面",
        ["数据概览", "截面分析视图", "时序分析视图", "持仓组合Greeks", "持仓叠加对比", "Volga分析", "Volga持仓跟踪", "数据完整性检查"],
        index=0
    )
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")
        
        # 数据库文件路径
        db_path = st.text_input(
            "数据库文件路径",
            value="options_data.duckdb",
            help="输入DuckDB数据库文件的路径"
        )
        
        # 货币类型选择（仅在数据概览页面显示）
        if page == "数据概览":
            currency = st.selectbox(
                "货币类型",
                options=["全部", "ETH", "BTC"],
                index=0
            )
        else:
            currency = "全部"
        
        # 数据刷新按钮
        if st.button("🔄 刷新数据", width='stretch'):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()

        # 数据管理
        st.header("🧹 数据管理")

        # Demo 模式下禁用数据管理功能
        if DEMO_MODE:
            st.warning("⚠️ **演示模式限制**：数据管理功能已禁用")
            st.caption("演示模式下无法清空或修改数据库，仅供浏览示例数据。")
            st.info('👉 **查看完整部署教程**：请在左侧导航栏选择 **"数据完整性检查"** 页面')
        else:
            st.caption("清空数据库后再采集，可确保仅保留最新快照。操作不可撤销，请谨慎执行。")
            confirm_clear = st.checkbox("我已确认要清空数据库", key="confirm_clear_db")
            if st.button("🧼 清空数据库", width='stretch'):
                if not confirm_clear:
                    st.warning("请先勾选确认复选框，再执行清空操作。")
                else:
                    try:
                        db_manager = OptionsDatabase(db_path=db_path)
                        db_manager.clear_all_data()
                        db_manager.close()
                        st.success("✅ 数据库已清空。")
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 清空数据库失败: {e}")
                        logger.error(f"清空数据库失败: {e}", exc_info=True)

        st.divider()
        
        # 数据采集按钮
        st.header("📥 数据采集")

        # Demo 模式检测与提示
        if DEMO_MODE:
            st.warning("⚠️ **演示模式限制**：数据采集功能已禁用")
            st.info('👉 **查看完整部署教程**：请在左侧导航栏选择 **"数据完整性检查"** 页面')
            st.divider()

        else:
            # 本地模式：显示完整的数据采集功能
            collect_mode = st.radio(
                "采集模式",
                ["快速采集（仅摘要）", "完整采集（摘要+Greeks）"],
                index=0,
                help="快速采集：只采集期权链摘要数据，速度快但不包含Greeks值\n完整采集：采集摘要和Greeks数据，速度慢但数据完整"
            )

            greeks_limit = None
            if collect_mode == "完整采集（摘要+Greeks）":
                # 添加复选框让用户选择是否采集全部
                collect_all = st.checkbox(
                    "采集全部Greeks数据（不限制数量）",
                    value=False,
                    help="勾选后将采集所有可用的Greeks数据，可能需要较长时间"
                )
            
                if not collect_all:
                    greeks_limit = st.number_input(
                        "Greeks数据限制数量",
                        min_value=1,
                        value=200,
                        step=100,
                        help="限制采集的Greeks数据数量（建议先采集少量测试）"
                    )
                else:
                    st.info("⚠️ 将采集全部Greeks数据，可能需要较长时间，请耐心等待...")
                    greeks_limit = None
        
            if st.button("🚀 开始采集数据", type="primary", width='stretch'):
                import time
                start_time = time.time()

                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    collector = DataCollector(currency="ETH", db_path=db_path, max_workers=10)
                
                    if collect_mode == "快速采集（仅摘要）":
                        status_text.text("正在采集期权链摘要数据...")
                        progress_bar.progress(30)

                        # 使用clear_all=True完全清空旧数据，确保每次都是最新快照
                        count = collector.collect_summary_data(clear_all=True)
                        duration = time.time() - start_time

                        # 跟踪数据采集成功
                        track_data_collection(
                            mode="quick",
                            success=True,
                            duration_seconds=duration,
                            record_count=count
                        )

                        if count > 0:
                            progress_bar.progress(100)
                            status_text.empty()
                            st.success(f"✅ 采集完成！成功采集 {count} 条摘要数据")
                        else:
                            progress_bar.progress(100)
                            status_text.empty()
                            st.warning("⚠️ 摘要数据采集完成，但未获取到新数据（可能网络问题或数据已是最新）")
                    
                    else:
                        # 完整采集模式
                        status_text.text("步骤 1/2: 正在采集期权链摘要数据...")
                        progress_bar.progress(20)

                        # 使用clear_all=True完全清空旧数据，确保每次都是最新快照
                        summary_count = collector.collect_summary_data(clear_all=True)

                        if summary_count == 0:
                            st.warning("⚠️ 摘要数据采集失败或未获取到新数据，将继续采集Greeks数据...")

                        status_text.text(f"步骤 2/2: 正在采集Greeks数据{'（全部）' if greeks_limit is None else f'（限制{greeks_limit}条）'}...")
                        progress_bar.progress(50)

                        # 第二次调用时不再清空（因为已经在第一次清空了）
                        greeks_count = collector.collect_greeks_data(limit=greeks_limit, clear_all=False)
                        duration = time.time() - start_time

                        # 跟踪完整采集成功
                        track_data_collection(
                            mode="full",
                            success=True,
                            duration_seconds=duration,
                            record_count=summary_count + greeks_count
                        )

                        progress_bar.progress(100)
                        status_text.empty()

                        # 显示详细结果
                        result_msg = f"✅ 采集完成！\n"
                        result_msg += f"- 摘要数据: {summary_count} 条\n"
                        if greeks_limit is None:
                            result_msg += f"- Greeks数据: {greeks_count} 条（全部采集）"
                        else:
                            result_msg += f"- Greeks数据: {greeks_count} 条（限制{greeks_limit}条）"

                        st.success(result_msg)
                    
                        # 显示统计信息
                        if summary_count > 0 or greeks_count > 0:
                            stats = collector.db.get_statistics()
                            with st.expander("📊 数据库统计信息"):
                                st.write(f"- 期权链记录数: {stats.get('options_chain_count', 0)}")
                                st.write(f"- Greeks记录数: {stats.get('greeks_count', 0)}")
                                st.write(f"- 唯一到期日: {stats.get('unique_expiration_dates', 0)}")
                
                    collector.close()
                
                    # 清除缓存并刷新
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.rerun()
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = str(e)

                    # 跟踪数据采集失败
                    track_data_collection(
                        mode="quick" if collect_mode == "快速采集（仅摘要）" else "full",
                        success=False,
                        duration_seconds=duration,
                        error_message=error_msg
                    )

                    st.error(f"❌ 数据采集失败: {error_msg}")

                    # 提供更详细的错误信息
                    if "proxy" in error_msg.lower() or "连接" in error_msg:
                        st.info("💡 提示：可能是网络代理问题，请检查网络连接或代理设置")
                    elif "timeout" in error_msg.lower():
                        st.info("💡 提示：请求超时，请稍后重试或减少采集数量")

                    logger.error(f"数据采集失败: {e}", exc_info=True)
        
            st.divider()
        
            # 数据统计信息
        st.header("📈 数据统计")
        db = load_database(db_path)
        if db:
            db_stats = db.get_statistics()
            st.metric("期权链记录数", db_stats.get('options_chain_count', 0))
            st.metric("Greeks记录数", db_stats.get('greeks_count', 0))
            st.metric("唯一到期日", db_stats.get('unique_expiration_dates', 0))
            if db_stats.get('latest_update'):
                st.caption(f"最新更新: {db_stats['latest_update']}")
    
    # 主内容区 - 路由分发
    if db_path:
        db = load_database(db_path)

        if db:
            # 根据选择的页面调用对应的视图函数
            if page == "截面分析视图":
                track_page_view("cross_section")
                render_cross_section_view(db)
            elif page == "时序分析视图":
                track_page_view("time_series")
                render_time_series_view(db)
            elif page == "持仓组合Greeks":
                track_page_view("portfolio")
                render_portfolio_view(db)
            elif page == "持仓叠加对比":
                track_page_view("portfolio_compare")
                render_portfolio_compare_view(db)
            elif page == "Volga分析":
                track_page_view("volga_analysis")
                render_volga_analysis_view(db)
            elif page == "Volga持仓跟踪":
                track_page_view("volga_holding")
                render_volga_holding_view(db)
            elif page == "数据完整性检查":
                track_page_view("data_check")
                render_data_check_view(db, db_path)
            else:
                # 默认显示数据概览页面
                track_page_view("dashboard", currency=currency)
                render_dashboard_view(db, currency)
        else:
            st.error("无法连接数据库，请检查数据库文件路径")
    else:
        st.info("请在侧边栏输入数据库文件路径")


if __name__ == "__main__":
    main()
