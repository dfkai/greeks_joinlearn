# PostHog 分析集成指南

本文档说明如何在 greeks-analytics 项目中使用 PostHog 进行用户行为分析和错误跟踪。

## 📋 目录
- [安装配置](#安装配置)
- [基础用法](#基础用法)
- [集成示例](#集成示例)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 安装配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```env
# PostHog 分析配置
POSTHOG_API_KEY=phc_your_actual_api_key_here
POSTHOG_HOST=https://app.posthog.com
ENABLE_POSTHOG=true  # 开发环境建议设为 false
```

**获取 API Key**：
1. 访问 [PostHog Cloud](https://app.posthog.com) 或自托管实例
2. 进入项目设置 (Project Settings)
3. 复制 "Project API Key"

### 3. 初始化 PostHog

在 `app.py` 中添加初始化代码：

```python
from src.utils import init_posthog

# 在 main() 函数开始处初始化
def main():
    # 初始化 PostHog（仅在启用时才会真正初始化）
    init_posthog()

    # ... 其他代码
```

---

## 基础用法

### 跟踪页面浏览

```python
from src.utils import track_page_view

# 在每个视图函数中跟踪页面访问
def render_cross_section_view(db):
    track_page_view("cross_section", currency="ETH")

    # ... 视图代码
```

### 跟踪数据采集事件

```python
from src.utils import track_data_collection
import time

# 在数据采集前后记录
start_time = time.time()

try:
    count = collector.collect_summary_data()
    duration = time.time() - start_time

    # 成功跟踪
    track_data_collection(
        mode="quick",
        success=True,
        duration_seconds=duration,
        record_count=count
    )
except Exception as e:
    duration = time.time() - start_time

    # 失败跟踪
    track_data_collection(
        mode="quick",
        success=False,
        duration_seconds=duration,
        error_message=str(e)
    )
```

### 跟踪组合操作

```python
from src.utils import track_portfolio_action

# 创建组合时
track_portfolio_action(
    action="create",
    position_count=3,
    strategy="straddle"
)

# 分析组合时
track_portfolio_action(
    action="analyze",
    position_count=3,
    net_delta=0.05
)
```

### 跟踪错误

```python
from src.utils import track_error

try:
    # 执行某个操作
    result = risky_operation()
except ValueError as e:
    track_error(
        error_type="ValueError",
        error_message=str(e),
        context={"operation": "risky_operation", "user_input": data}
    )
    raise
```

### 自定义事件跟踪

```python
from src.utils import track_event

# 跟踪任意自定义事件
track_event(
    "feature_used",
    properties={
        "feature": "volga_analysis",
        "chart_type": "scatter",
        "data_points": 150
    }
)
```

---

## 集成示例

### 示例 1: 在 app.py 中集成

```python
# app.py
import streamlit as st
from src.utils import init_posthog, track_page_view, track_error

# 页面配置
st.set_page_config(...)

# 初始化 PostHog（全局只需一次）
init_posthog()

def main():
    # ... 页面路由逻辑

    page = st.sidebar.selectbox(...)

    # 根据页面路由跟踪浏览
    if page == "截面分析视图":
        track_page_view("cross_section")
        render_cross_section_view(db)
    elif page == "时序分析视图":
        track_page_view("time_series")
        render_time_series_view(db)
    # ... 其他页面
```

### 示例 2: 在数据采集中集成

```python
# app.py - 数据采集按钮逻辑
import time
from src.utils import track_data_collection

if st.button("🚀 开始采集数据"):
    start_time = time.time()

    try:
        collector = DataCollector(...)

        if collect_mode == "快速采集（仅摘要）":
            count = collector.collect_summary_data(clear_all=True)
            duration = time.time() - start_time

            # 跟踪成功
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
            summary_count = collector.collect_summary_data(clear_all=True)
            greeks_count = collector.collect_greeks_data(limit=greeks_limit)
            duration = time.time() - start_time

            # 跟踪成功
            track_data_collection(
                mode="full",
                success=True,
                duration_seconds=duration,
                record_count=summary_count + greeks_count
            )

            st.success(f"✅ 采集完成！摘要: {summary_count} 条, Greeks: {greeks_count} 条")

    except Exception as e:
        duration = time.time() - start_time

        # 跟踪失败
        track_data_collection(
            mode="quick" if collect_mode == "快速采集" else "full",
            success=False,
            duration_seconds=duration,
            error_message=str(e)
        )

        st.error(f"❌ 数据采集失败: {e}")
        logger.error(f"数据采集失败: {e}", exc_info=True)
```

### 示例 3: 在组合视图中集成

```python
# views/portfolio.py
from src.utils import track_portfolio_action, track_page_view

def render_portfolio_view(db):
    # 跟踪页面浏览
    track_page_view("portfolio")

    # ... 组合构建 UI

    if st.button("添加到组合"):
        # 添加持仓逻辑
        add_position_to_portfolio(...)

        # 跟踪操作
        track_portfolio_action(
            action="add_position",
            position_count=len(current_positions),
            instrument_name=selected_instrument
        )

    if st.button("计算组合Greeks"):
        # 计算逻辑
        results = analyze_portfolio(...)

        # 跟踪分析
        track_portfolio_action(
            action="analyze",
            position_count=len(current_positions),
            net_delta=results.get('delta'),
            net_gamma=results.get('gamma')
        )
```

### 示例 4: 使用装饰器自动跟踪

```python
from src.utils import track_function_call

# 自动跟踪函数调用和性能
@track_function_call("bs_calculation")
def calculate_greeks(spot, strike, r, sigma, tau, option_type):
    # Black-Scholes 计算
    ...
    return greeks

# 调用时会自动发送事件，包含执行时间和成功/失败状态
greeks = calculate_greeks(3500, 3600, 0.05, 0.65, 0.25, "call")
```

---

## 最佳实践

### 1. 环境分离

```env
# 开发环境 (.env.development)
ENABLE_POSTHOG=false

# 生产环境 (.env.production)
ENABLE_POSTHOG=true
POSTHOG_API_KEY=phc_production_key_here
```

### 2. 隐私保护

```python
# ❌ 不要跟踪敏感数据
track_event("api_call", {
    "api_key": "secret_key_123",  # 错误！
    "user_email": "user@example.com"  # 错误！
})

# ✅ 只跟踪聚合数据和匿名指标
track_event("api_call", {
    "endpoint": "/public/get_instruments",
    "success": True,
    "duration_ms": 245
})
```

### 3. 事件命名规范

使用 `snake_case` 和清晰的动词-名词结构：

```python
# ✅ 好的命名
track_event("page_view")
track_event("data_collection_started")
track_event("portfolio_created")
track_event("greeks_calculated")

# ❌ 不好的命名
track_event("PageView")  # 不符合规范
track_event("data")  # 太模糊
track_event("click")  # 缺少上下文
```

### 4. 性能优化

PostHog 客户端使用异步批量发送，不会阻塞应用：

```python
# ✅ 事件发送是异步的，不影响用户体验
track_event("button_click")  # 立即返回
expensive_operation()  # 不会被阻塞
```

但在应用退出时要确保事件发送完成：

```python
import atexit
from src.utils import shutdown_posthog

# 注册退出时的清理函数
atexit.register(shutdown_posthog)
```

### 5. 条件跟踪

只在需要时跟踪：

```python
# 只跟踪重要操作
if record_count > 100:  # 大量数据采集
    track_data_collection(...)

# 不要跟踪每次鼠标移动或键盘输入
```

---

## 常见问题

### Q1: PostHog 会影响应用性能吗？

**A**: 不会。PostHog Python SDK 使用异步批量发送机制，事件会在后台线程中发送，不会阻塞主应用。

### Q2: 如何在开发环境禁用 PostHog？

**A**: 在 `.env` 文件中设置：

```env
ENABLE_POSTHOG=false
```

### Q3: 可以自托管 PostHog 吗？

**A**: 可以。PostHog 提供开源自托管版本。修改 `.env` 中的 `POSTHOG_HOST`：

```env
POSTHOG_HOST=https://your-posthog-instance.com
```

### Q4: 如何查看收集的数据？

**A**: 登录 PostHog 仪表板：
1. 访问 `https://app.posthog.com`（或你的自托管实例）
2. 查看 "Insights" → "Events" 查看所有事件
3. 创建自定义仪表板和漏斗分析

### Q5: 跟踪的数据会存储多久？

**A**:
- PostHog Cloud 免费版：90 天
- PostHog Cloud 付费版：可配置（最长 7 年）
- 自托管版本：取决于你的配置

### Q6: 是否会跟踪个人身份信息（PII）？

**A**: 不会。代码中使用匿名用户 ID（`anonymous_<uuid>`），不收集任何个人身份信息。如果你的应用有登录功能，可以使用 `identify_user()` 关联用户，但请遵守隐私法规。

---

## 可跟踪的事件示例

### 系统级事件
```python
track_event("app_started")
track_event("app_error", {"error_type": "DatabaseError"})
track_event("cache_cleared")
```

### 数据操作事件
```python
track_event("data_collection_started", {"mode": "full"})
track_event("data_collection_completed", {"record_count": 1250})
track_event("database_cleared")
```

### 用户交互事件
```python
track_event("page_view", {"page": "cross_section"})
track_event("filter_applied", {"filter_type": "expiration_date"})
track_event("chart_type_changed", {"from": "line", "to": "scatter"})
```

### 分析事件
```python
track_event("greeks_calculated", {"option_count": 150})
track_event("portfolio_analyzed", {"position_count": 5, "net_delta": 0.12})
track_event("scenario_analysis_run", {"scenario": "price_sweep"})
```

---

## 参考资源

- [PostHog Python SDK 文档](https://posthog.com/docs/libraries/python)
- [PostHog Python GitHub](https://github.com/PostHog/posthog-python)
- [PostHog 产品分析文档](https://posthog.com/docs/product-analytics/installation/python)
- [PostHog PyPI 页面](https://pypi.org/project/posthog/)

---

## 支持

如有问题或建议，请访问：
- PostHog 社区: https://posthog.com/questions
- GitHub Issues: https://github.com/PostHog/posthog-python/issues
