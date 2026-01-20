# Streamlit Cloud 部署指南（含 PostHog 配置）

本指南说明如何将 greeks-analytics 项目部署到 Streamlit Cloud，并正确配置 PostHog 分析。

---

## 📋 部署步骤

### 1. 准备工作

确保您的代码已推送到 GitHub：

```bash
git add .
git commit -m "Update configuration for Streamlit Cloud"
git push origin main
```

### 2. 登录 Streamlit Cloud

访问 https://share.streamlit.io 并使用 GitHub 账号登录。

### 3. 创建新应用

1. 点击 **"New app"**
2. 选择您的 GitHub 仓库：`dfkai/greeks_joinlearn`
3. 选择分支：`main`
4. 主文件路径：`app.py`
5. 点击 **"Deploy!"**

---

## 🔐 配置 Secrets（重要）

部署后，您需要在 Streamlit Cloud 中配置敏感信息。

### 访问 Secrets 设置

1. 在 Streamlit Cloud 应用页面
2. 点击右下角 **"Settings"** (齿轮图标)
3. 选择 **"Secrets"** 标签页

### 配置选项

根据您的需求选择以下配置之一：

---

## 配置方案 A：只读 Demo 模式（推荐用于公开展示）

**适用场景**：公开演示，使用预加载的示例数据，禁用数据采集和 PostHog

```toml
# ==================== Demo 模式配置 ====================
ENABLE_DATA_COLLECTION = "false"

# ==================== PostHog 配置 ====================
ENABLE_POSTHOG = "false"

# ==================== 其他配置 ====================
RISK_FREE_RATE = "0.05"
```

**特点**：
- ✅ 无需 API 密钥
- ✅ 数据安全（无法修改数据库）
- ✅ 适合公开访问
- ❌ 无法实时采集数据
- ❌ 无法跟踪用户行为

---

## 配置方案 B：完整功能 + PostHog 分析（推荐用于生产环境）

**适用场景**：私人使用或受控访问，需要数据采集和用户行为分析

```toml
# ==================== 应用模式配置 ====================
ENABLE_DATA_COLLECTION = "true"

# ==================== Deribit API 凭证 ====================
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "your_actual_deribit_client_id"
DERIBIT_CLIENT_SECRET_TEST = "your_actual_deribit_client_secret"

# ==================== PostHog 分析配置 ====================
ENABLE_POSTHOG = "true"
POSTHOG_API_KEY = "phc_your_actual_posthog_api_key"
POSTHOG_HOST = "https://app.posthog.com"

# ==================== 其他配置 ====================
RISK_FREE_RATE = "0.05"
```

**特点**：
- ✅ 完整数据采集功能
- ✅ PostHog 用户行为分析
- ✅ 性能监控
- ⚠️ 需要 API 密钥
- ⚠️ 注意访问控制

---

## 配置方案 C：数据采集功能 + 禁用 PostHog

**适用场景**：需要数据采集但不需要分析的私人使用

```toml
# ==================== 应用模式配置 ====================
ENABLE_DATA_COLLECTION = "true"

# ==================== Deribit API 凭证 ====================
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "your_actual_deribit_client_id"
DERIBIT_CLIENT_SECRET_TEST = "your_actual_deribit_client_secret"

# ==================== PostHog 配置 ====================
ENABLE_POSTHOG = "false"

# ==================== 其他配置 ====================
RISK_FREE_RATE = "0.05"
```

---

## 🔑 获取所需的 API Keys

### Deribit API Key

1. 访问 https://test.deribit.com（测试环境）
2. 注册并登录
3. 进入 **Account** → **API**
4. 创建新的 API Key
5. **权限设置**：只需要 **Read** 权限（足够用于数据采集）
6. 复制 Client ID 和 Client Secret

### PostHog API Key

1. 访问 https://app.posthog.com
2. 注册/登录账号
3. 创建新项目（如果还没有）
4. 进入 **Project Settings**
5. 复制 **Project API Key**（以 `phc_` 开头）

---

## 📝 配置 Secrets 的步骤

### 方法 1：使用 Web 界面（推荐）

1. 在 Streamlit Cloud 应用的 **Settings** → **Secrets** 页面
2. 复制上述配置方案之一
3. 粘贴到 Secrets 文本框
4. 将占位符替换为真实的 API Keys：
   - `your_actual_deribit_client_id` → 真实的 Deribit Client ID
   - `your_actual_deribit_client_secret` → 真实的 Deribit Client Secret
   - `phc_your_actual_posthog_api_key` → 真实的 PostHog API Key
5. 点击 **"Save"**
6. 应用会自动重启

### 方法 2：使用 TOML 文件（本地测试）

创建 `.streamlit/secrets.toml`（本地测试用，不要提交到 Git）：

```bash
# 复制示例文件
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 编辑并填入真实的 API Keys
nano .streamlit/secrets.toml
```

**注意**：`.streamlit/secrets.toml` 已在 `.gitignore` 中，不会被提交。

---

## 🚀 验证部署

### 检查 Demo 模式

如果您配置了 `ENABLE_DATA_COLLECTION = "false"`：

1. 访问您的 Streamlit Cloud 应用 URL
2. 应该看到横幅提示：**"📊 在线演示模式 - 您正在查看预加载的示例数据快照"**
3. 数据采集按钮应该被禁用
4. 导航栏中的"数据完整性检查"页面会显示部署教程

### 检查完整功能模式

如果您配置了 `ENABLE_DATA_COLLECTION = "true"`：

1. 访问应用
2. 不应该看到 Demo 模式横幅
3. 侧边栏的"采集数据"按钮应该可用
4. 点击"采集数据"应该能够成功从 Deribit 获取数据

### 检查 PostHog

如果您配置了 `ENABLE_POSTHOG = "true"`：

1. 在应用中切换几个页面
2. 访问 https://app.posthog.com
3. 进入 **Events** 页面
4. 应该能看到 `page_view` 和 `data_collection` 事件

---

## 🔍 故障排查

### 问题 1：应用启动失败

**症状**：部署后应用显示错误

**解决**：
1. 检查 Streamlit Cloud 的日志（应用页面右下角 "Manage app" → "Logs"）
2. 确认所有依赖都在 `requirements.txt` 中
3. 确认 Secrets 格式正确（TOML 格式，无语法错误）

### 问题 2：数据采集失败

**症状**：点击"采集数据"报错

**可能原因**：
- Deribit API Key 无效或权限不足
- `ENABLE_DATA_COLLECTION` 设置为 `"false"`
- 网络问题

**解决**：
1. 检查 Secrets 中的 Deribit 凭证是否正确
2. 确认 API Key 有 **Read** 权限
3. 确认 `ENABLE_DATA_COLLECTION = "true"`

### 问题 3：PostHog 事件未显示

**症状**：PostHog 仪表板中看不到事件

**可能原因**：
- PostHog API Key 错误
- `ENABLE_POSTHOG` 设置为 `"false"`
- 事件发送有延迟（异步批量发送）

**解决**：
1. 检查 Secrets 中的 `POSTHOG_API_KEY` 是否正确
2. 确认 `ENABLE_POSTHOG = "true"`
3. 等待 1-2 分钟（PostHog 批量发送有延迟）
4. 检查 PostHog 项目是否选择正确

### 问题 4：Secrets 修改后不生效

**症状**：修改 Secrets 后应用行为没有变化

**解决**：
1. 保存 Secrets 后，应用应该自动重启
2. 如果没有，手动重启应用：**Settings** → **Reboot app**
3. 清除浏览器缓存并刷新页面

---

## 🔒 安全最佳实践

### 1. API Key 权限

- ✅ Deribit API Key 只授予 **Read** 权限（足够用于数据采集）
- ❌ 不要授予 **Trade** 或 **Withdraw** 权限

### 2. 访问控制

公开 Demo：
- 设置 `ENABLE_DATA_COLLECTION = "false"`
- 设置 `ENABLE_POSTHOG = "false"`（可选）
- 不在 Secrets 中添加任何 API Keys

私人使用：
- 在 Streamlit Cloud 应用设置中启用 **"Require viewers to log in"**
- 只邀请授权用户

### 3. 环境隔离

- 生产环境：使用生产 API Keys
- 测试/Demo 环境：使用测试 API Keys
- 永远不要在代码中硬编码 API Keys

---

## 📊 推荐配置

### 公开 Demo（推荐给大多数用户）

```toml
ENABLE_DATA_COLLECTION = "false"
ENABLE_POSTHOG = "false"
RISK_FREE_RATE = "0.05"
```

**优点**：
- 安全，无需 API Keys
- 快速部署
- 适合展示和教学

### 私人分析工具

```toml
ENABLE_DATA_COLLECTION = "true"
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "your_key"
DERIBIT_CLIENT_SECRET_TEST = "your_secret"
ENABLE_POSTHOG = "true"
POSTHOG_API_KEY = "phc_your_key"
POSTHOG_HOST = "https://app.posthog.com"
RISK_FREE_RATE = "0.05"
```

**优点**：
- 完整功能
- 用户行为分析
- 性能监控

---

## 🎯 下一步

部署成功后：

1. **测试应用功能**：访问所有页面，确认功能正常
2. **查看 PostHog 数据**（如果启用）：https://app.posthog.com
3. **分享应用**：复制 Streamlit Cloud 应用 URL 分享给他人
4. **监控日志**：定期检查应用日志，确保没有错误

---

## 📚 相关文档

- **PostHog 集成指南**：`docs/POSTHOG_INTEGRATION.md`
- **API 设置指南**：`docs/API_SETUP.md`
- **部署指南**：`docs/DEPLOYMENT.md`
- **Secrets 示例**：`.streamlit/secrets.toml.example`

---

## 💡 提示

1. **首次部署**：建议先使用 Demo 模式（`ENABLE_DATA_COLLECTION = "false"`）
2. **测试功能**：在本地使用 `.env` 文件测试完整功能
3. **渐进启用**：先部署基础功能，测试成功后再启用 PostHog
4. **定期更新**：定期检查并更新 API Keys 的权限

---

**祝您部署顺利！** 🚀

如有问题，请查看 Streamlit Cloud 文档：https://docs.streamlit.io/streamlit-community-cloud
