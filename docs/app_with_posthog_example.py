"""
PostHog 集成示例 - 展示如何在 app.py 中集成 PostHog 分析

使用方法：
1. 参考本文件中的集成模式
2. 将相关代码添加到实际的 app.py 中
3. 确保 .env 文件已配置 PostHog 凭证
"""

import streamlit as st
import time
from src.utils import (
    init_posthog,
    track_page_view,
    track_data_collection,
    track_error,
    shutdown_posthog
)

# ========================================
# 1. 初始化 PostHog (在应用启动时)
# ========================================

# 在 main() 函数开始处调用
def main():
    """主应用函数 - 集成 PostHog"""

    # 初始化 PostHog (仅在 ENABLE_POSTHOG=true 时生效)
    init_posthog()

    # ... 其他初始化代码 (页面配置等)

    # ========================================
    # 2. 跟踪页面浏览
    # ========================================

    page = st.sidebar.selectbox(
        "选择页面",
        ["数据概览", "截面分析视图", "时序分析视图", "持仓组合Greeks"],
        index=0
    )

    # 根据页面路由跟踪浏览
    if page == "截面分析视图":
        track_page_view("cross_section")
        # render_cross_section_view(db)

    elif page == "时序分析视图":
        track_page_view("time_series")
        # render_time_series_view(db)

    elif page == "持仓组合Greeks":
        track_page_view("portfolio")
        # render_portfolio_view(db)

    else:
        track_page_view("dashboard")
        # render_dashboard_view(db)

    # ========================================
    # 3. 跟踪数据采集操作
    # ========================================

    st.sidebar.header("📥 数据采集")

    collect_mode = st.sidebar.radio(
        "采集模式",
        ["快速采集（仅摘要）", "完整采集（摘要+Greeks）"],
        index=0
    )

    if st.sidebar.button("🚀 开始采集数据", type="primary"):
        start_time = time.time()

        try:
            # 模拟数据采集逻辑
            # collector = DataCollector(currency="ETH", db_path=db_path)

            if collect_mode == "快速采集（仅摘要）":
                # count = collector.collect_summary_data(clear_all=True)
                count = 1250  # 模拟返回值

                duration = time.time() - start_time

                # ✅ 跟踪成功的数据采集
                track_data_collection(
                    mode="quick",
                    success=True,
                    duration_seconds=duration,
                    record_count=count
                )

                if count > 0:
                    st.success(f"✅ 采集完成！成功采集 {count} 条摘要数据")
                else:
                    st.warning("⚠️ 摘要数据采集完成，但未获取到新数据")

            else:
                # 完整采集模式
                # summary_count = collector.collect_summary_data(clear_all=True)
                # greeks_count = collector.collect_greeks_data(limit=None)

                summary_count = 1250  # 模拟
                greeks_count = 850    # 模拟

                duration = time.time() - start_time

                # ✅ 跟踪完整采集
                track_data_collection(
                    mode="full",
                    success=True,
                    duration_seconds=duration,
                    record_count=summary_count + greeks_count
                )

                st.success(f"✅ 采集完成！摘要: {summary_count} 条, Greeks: {greeks_count} 条")

        except Exception as e:
            duration = time.time() - start_time

            # ❌ 跟踪失败的数据采集
            track_data_collection(
                mode="quick" if collect_mode == "快速采集" else "full",
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )

            # 同时跟踪错误详情
            track_error(
                error_type=type(e).__name__,
                error_message=str(e),
                context={
                    "operation": "data_collection",
                    "mode": collect_mode
                }
            )

            st.error(f"❌ 数据采集失败: {e}")

    # ========================================
    # 4. 跟踪数据库清空操作
    # ========================================

    st.sidebar.header("🧹 数据管理")

    if st.sidebar.button("🧼 清空数据库"):
        try:
            # db_manager.clear_all_data()

            # ✅ 跟踪数据库清空
            from src.utils import track_event
            track_event("database_cleared")

            st.success("✅ 数据库已清空。")

        except Exception as e:
            # ❌ 跟踪错误
            track_error(
                error_type=type(e).__name__,
                error_message=str(e),
                context={"operation": "clear_database"}
            )

            st.error(f"❌ 清空数据库失败: {e}")

    # ========================================
    # 5. 应用退出时清理 (可选)
    # ========================================

    # 注意：Streamlit 应用通常不需要手动调用 shutdown_posthog()
    # PostHog 客户端会自动在后台批量发送事件
    # 但如果你需要确保所有事件立即发送，可以使用：

    # import atexit
    # atexit.register(shutdown_posthog)


# ========================================
# 在视图函数中集成 PostHog
# ========================================

def example_portfolio_view():
    """示例：在组合视图中使用 PostHog"""

    from src.utils import track_portfolio_action, track_event

    st.header("持仓组合Greeks")

    # 模拟组合构建
    positions = []

    if st.button("添加持仓"):
        # add_position_logic()
        positions.append({"instrument": "ETH-28JAN26-3600-C", "size": 1})

        # ✅ 跟踪组合操作
        track_portfolio_action(
            action="add_position",
            position_count=len(positions),
            instrument_name="ETH-28JAN26-3600-C"
        )

    if st.button("计算组合Greeks"):
        # results = analyze_portfolio(positions)

        # 模拟结果
        net_delta = 0.15
        net_gamma = 0.05

        # ✅ 跟踪分析操作
        track_portfolio_action(
            action="analyze",
            position_count=len(positions),
            net_delta=net_delta,
            net_gamma=net_gamma
        )

        st.success("✅ 组合分析完成")

    # 跟踪自定义功能使用
    if st.checkbox("显示 Volga 分析"):
        track_event("feature_enabled", {
            "feature": "volga_analysis",
            "page": "portfolio"
        })


def example_error_tracking():
    """示例：错误跟踪的最佳实践"""

    from src.utils import track_error

    try:
        # 可能失败的操作
        risky_operation()

    except ValueError as e:
        # ✅ 跟踪验证错误
        track_error(
            error_type="ValueError",
            error_message=str(e),
            context={
                "operation": "risky_operation",
                "user_input": "invalid_data"
            }
        )
        st.error(f"输入数据无效: {e}")

    except ConnectionError as e:
        # ✅ 跟踪网络错误
        track_error(
            error_type="ConnectionError",
            error_message=str(e),
            context={
                "operation": "api_call",
                "endpoint": "/public/get_instruments"
            }
        )
        st.error(f"网络连接失败: {e}")

    except Exception as e:
        # ✅ 跟踪未知错误
        track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            context={"operation": "unknown"}
        )
        st.error(f"发生未知错误: {e}")
        raise  # 重新抛出异常以便调试


# 模拟函数
def risky_operation():
    raise ValueError("Invalid input data")


# ========================================
# 高级用法：使用装饰器
# ========================================

from src.utils import track_function_call


@track_function_call("greeks_calculation")
def calculate_greeks_advanced(spot, strike, r, sigma, tau):
    """
    使用装饰器自动跟踪函数调用

    PostHog 会自动记录:
    - 函数名
    - 执行时间
    - 成功/失败状态
    - 错误信息 (如果失败)
    """
    import time
    time.sleep(0.1)  # 模拟计算

    # 计算 Greeks
    delta = 0.6
    gamma = 0.05

    return {"delta": delta, "gamma": gamma}


# 调用时会自动跟踪
# greeks = calculate_greeks_advanced(3500, 3600, 0.05, 0.65, 0.25)


if __name__ == "__main__":
    # 运行示例 (实际应用中使用 streamlit run app.py)
    print("这是 PostHog 集成示例文件")
    print("请参考本文件中的代码模式，集成到实际的 app.py 中")
