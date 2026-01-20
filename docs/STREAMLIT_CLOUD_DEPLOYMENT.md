# Streamlit Cloud 部署指南

将 greeks-analytics 项目部署到 Streamlit Cloud 的配置说明。

---

## 快速部署

### 1. 创建应用

访问 https://share.streamlit.io，使用 GitHub 账号登录：

- Repository: `dfkai/greeks_joinlearn`
- Branch: `main`
- Main file: `app.py`

### 2. 配置 Secrets

点击应用的 **Settings** → **Secrets**，根据需求选择配置：

---

## 配置方案

### 方案 A：公开 Demo（只读，推荐）

适合公开展示，使用预加载数据，无需 API Keys。

```toml
ENABLE_DATA_COLLECTION = "false"
ENABLE_POSTHOG = "false"
RISK_FREE_RATE = "0.05"
```

---

### 方案 B：Demo + PostHog 分析

适合公开 Demo，跟踪用户行为，了解功能使用情况。

```toml
ENABLE_DATA_COLLECTION = "false"
ENABLE_POSTHOG = "true"
POSTHOG_API_KEY = "phc_your_api_key_here"
POSTHOG_HOST = "https://app.posthog.com"
RISK_FREE_RATE = "0.05"
```

**PostHog API Key 获取**：
1. 访问 https://app.posthog.com 并注册/登录
2. 进入 Project Settings
3. 复制 Project API Key（以 `phc_` 开头）

---

### 方案 C：完整功能 + PostHog

适合私人使用，完整数据采集和分析功能。

```toml
ENABLE_DATA_COLLECTION = "true"
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "your_deribit_client_id"
DERIBIT_CLIENT_SECRET_TEST = "your_deribit_secret"
ENABLE_POSTHOG = "true"
POSTHOG_API_KEY = "phc_your_api_key_here"
POSTHOG_HOST = "https://app.posthog.com"
RISK_FREE_RATE = "0.05"
```

**Deribit API Key 获取**：
1. 访问 https://test.deribit.com 并注册
2. 进入 Account → API
3. 创建 API Key，权限设置为 **Read only**

⚠️ **私人使用建议**：在 Streamlit Cloud 设置中启用 "Require viewers to log in"

---

## PostHog 功能说明

启用 PostHog 后，应用会自动跟踪：

- **页面浏览**：用户访问了哪些页面
- **数据采集**：采集模式、耗时、成功率
- **使用模式**：功能使用频率、用户导航路径

**查看数据**：https://app.posthog.com → Events

**隐私保护**：使用匿名用户 ID，不收集个人信息。

---

## 验证部署

### Demo 模式

访问应用应该看到：
- ✅ 横幅提示："📊 在线演示模式"
- ✅ 数据采集按钮禁用
- ✅ 示例数据可正常查看

### PostHog 验证

启用后：
- 在应用中切换几个页面
- 访问 PostHog 仪表板
- 1-2 分钟后应看到 `page_view` 事件

---

## 常见问题

**Q: 修改 Secrets 后不生效？**
A: 保存后应用会自动重启，如未重启请手动 Reboot app。

**Q: 数据采集失败？**
A: 检查 Deribit API Key 是否正确，确认权限为 Read。

**Q: PostHog 看不到事件？**
A: 确认 API Key 正确，等待 1-2 分钟（异步批量发送）。

**Q: 如何禁用 PostHog？**
A: 在 Secrets 中设置 `ENABLE_POSTHOG = "false"`。

---

## 安全建议

✅ **公开 Demo**：使用方案 A 或 B，不暴露 Deribit API
✅ **API Key 权限**：Deribit 只授予 Read 权限
✅ **访问控制**：私人使用时启用登录要求
❌ **不要**：在代码中硬编码 API Keys

---

## 相关文档

- Streamlit Cloud 文档: https://docs.streamlit.io/streamlit-community-cloud
- PostHog 文档: https://posthog.com/docs/libraries/python
- Deribit API: https://docs.deribit.com
