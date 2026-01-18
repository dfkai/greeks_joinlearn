# Deribit 期权分析系统

**中文** | [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![DuckDB](https://img.shields.io/badge/DuckDB-0.9%2B-yellow)
![Local-First](https://img.shields.io/badge/Local--First-Tool-green)

基于 Deribit 交易所的期权链静态分析系统，提供完整的 Black-Scholes 定价和 Greeks 风险计算。

---

## 🎯 两种使用方式

### 🌐 在线演示版（只读模式）
👉 **[在线演示](https://greeks-joinlearn.streamlit.app)** - 浏览示例数据

- ✅ 体验所有分析功能
- ✅ 查看期权链和希腊值示例
- ⚠️ 数据采集功能已禁用（演示模式）
- 💡 如需实时数据，请使用本地版本

### 💻 本地版本（完整功能）
**推荐用于实际交易分析**

- ✅ 从 Deribit 实时采集数据
- ✅ 使用你自己的 API 凭证
- ✅ 历史数据积累
- ✅ 完全私密（数据保存在本地）

**这是一个本地优先工具** - 设计为在你的电脑上运行，使用你自己的 API 访问权限。

---

## 🚀 快速开始（本地部署）

```bash
# 1. 克隆仓库
git clone https://github.com/dfkai/greeks_joinlearn.git
cd greeks_joinlearn

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 凭证（只需编辑一个文件！）
cp .env.example .env
nano .env  # 或使用任何文本编辑器

# 在 .env 文件中填入以下两行：
#   DERIBIT_CLIENT_ID_TEST=你的实际_client_id
#   DERIBIT_CLIENT_SECRET_TEST=你的实际_client_secret

# 4. 启动 Streamlit 仪表板
streamlit run app.py
# 访问：http://localhost:8501
```

**就这么简单！** 所有配置都在 `.env` 文件中。无需配置其他任何内容。

---

## 🔑 API 凭证配置

### 步骤 1：获取 Deribit API 密钥

1. 访问 [Deribit 测试环境](https://test.deribit.com/)（推荐）或 [生产环境](https://www.deribit.com/)
2. 登录 → 账户 → API
3. 创建新的 API 密钥，权限选择 **Read**（只读）
4. 复制 `Client ID` 和 `Client Secret`

### 步骤 2：配置 `.env` 文件（仅本地使用！）

```bash
# 这是你唯一需要编辑的文件
nano .env
```

填入你的凭证：
```bash
DERIBIT_CLIENT_ID_TEST=粘贴你的_client_id
DERIBIT_CLIENT_SECRET_TEST=粘贴你的_client_secret
```

### ✅ 你的凭证是安全的

- `.env` 文件已被 Git 自动忽略
- 你的 API 密钥**永远不会**上传到 GitHub
- 数据完全私密地保存在你的机器上

### ❓ `.streamlit/secrets.toml.example` 是什么？

**本地使用可以忽略这个文件！**

**用途**：这是 Streamlit Cloud 部署的参考模板（类似于 `.env`，但用于云端）。

- **本地部署**：只需修改 `.env` 文件（如上所述）
- **Streamlit Cloud 部署**：参考 `secrets.toml.example` 的内容，在 Streamlit Cloud 网页的 Secrets 管理界面手动填写

**简单理解**：
- `.env` = 本地运行的配置文件
- Streamlit Cloud Secrets = 云端运行的配置文件
- `secrets.toml.example` = 教你云端应该填什么的参考文档

---

## 🚀 部署

### 部署演示版到 Streamlit Cloud（可选）

[![Deploy](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

**仅用于演示目的** - 展示预加载的示例数据，不进行实时采集。

1. 将此仓库推送到你的 GitHub
2. 访问 [Streamlit Cloud](https://share.streamlit.io)
3. 创建新应用 → 选择你的仓库
4. 主文件：`app.py`
5. **配置 Secrets**（Settings → Secrets）：
   ```toml
   # 参考 .streamlit/secrets.toml.example 文件
   # 只需要填这一行即可启用 Demo 模式
   ENABLE_DATA_COLLECTION = "false"
   ```
6. 部署！

**配置说明**：
- **不要**填写 Deribit API 凭证（保持只读 Demo）
- `.streamlit/secrets.toml.example` 是参考模板，不需要修改它
- 在 Streamlit Cloud 网页界面手动填写 Secrets（如上所示）

**结果**：用户可以使用示例数据探索功能，但无法采集新数据。

**生产使用**：克隆到本地并使用你自己的 API 凭证（见上面的快速开始）。

---

### ⚠️ 为什么不适合多用户生产部署？

本工具设计为**单用户本地运行**，因为：

- **API 速率限制**：多用户 = API 配额耗尽
- **数据隐私**：交易数据应该保存在你的机器上
- **成本**：每个用户都会消耗你的 API 额度
- **架构**：DuckDB 基于文件的存储不适合并发用户

**推荐**：每个交易者运行自己的本地实例，使用自己的 Deribit API。

### Docker 运行（可选）

本地容器化部署：

```bash
# 构建镜像
docker build -t greeks-analytics .

# 运行容器
docker run -p 8501:8501 --env-file .env greeks-analytics

# 访问 http://localhost:8501
```

---

## 📊 核心功能

### 1. IV 分析
- **波动率微笑**：跨行权价的 IV 倾斜
- **期限结构**：IV 随时间的演变
- **偏度分析**：看跌/看涨 IV 差异

### 2. 投资组合构建器
- **多腿策略**：跨式、宽跨式、铁鹰、蝶式等
- **Greeks 聚合**：净 Delta、Gamma、Theta、Vega、Rho
- **风险场景**：价格扫描、时间衰减、IV 冲击模拟

### 3. 高级 Greeks
- **Volga（凸性）**：二阶波动率风险 ∂²V/∂σ²
- **Vanna（相关性）**：交叉希腊值 ∂Δ/∂σ
- **Volga-Vega 聚类**：识别最优合约

### 4. 数据质量工具
- **完整性检查**：交易量数据验证
- **数据库检查**：快照历史分析
- **回填工具**：缺失数据恢复

---

## 🏗️ 项目结构

```
/
├── app.py                      # Streamlit 入口
├── config.py                   # UI 配置（颜色、标签）
├── views/                      # 8 个分析视图
│   ├── cross_section.py       # IV 微笑、按行权价的 Greeks
│   ├── time_series.py         # 期限结构、IV 趋势
│   ├── portfolio.py           # 投资组合构建器
│   ├── volga_analysis.py      # 二阶 Greeks
│   └── ...
├── src/
│   ├── core/                  # 核心算法
│   │   ├── bs_calculator.py   # Black-Scholes Greeks 引擎
│   │   ├── portfolio_analyzer.py  # 投资组合聚合
│   │   └── database.py        # OptionsDatabase（DuckDB）
│   └── collectors/            # 数据获取
│       ├── data_collector.py
│       └── data_completeness_checker.py
├── api/
│   └── Deribit_HTTP.py        # REST API 客户端
├── scripts/                    # 实用工具
│   ├── check_data.py          # 数据库检查
│   ├── collect_greeks_data.py # Greeks 数据采集
│   └── ...
└── tests/                      # 测试文件
```

---

## 🛠️ 安装

### 系统要求
- Python 3.8+
- DuckDB（通过 pip 自动安装）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. **创建 `.env` 文件**：
   ```bash
   cp .env.example .env
   ```

2. **添加 Deribit API 凭证**：
   ```env
   # 环境：test 或 prod
   DERIBIT_ENV=test

   # 测试环境凭证（推荐）
   DERIBIT_CLIENT_ID_TEST=你的_client_id
   DERIBIT_CLIENT_SECRET_TEST=你的_client_secret

   # 可选：无风险利率（默认：0.05）
   RISK_FREE_RATE=0.05
   ```

3. **获取 API 凭证**：
   - 测试网：[test.deribit.com](https://test.deribit.com) → 设置 → API
   - 生产环境：[www.deribit.com](https://www.deribit.com) → 设置 → API
   - 推荐权限：只读

---

## 📖 使用

### 启动应用

```bash
streamlit run app.py
```

应用将在浏览器中打开：http://localhost:8501

### 可用视图

1. **数据概览** - 快速摘要和数据采集
2. **截面分析** - IV 微笑和按行权价的 Greeks
3. **时序分析** - 期限结构和 IV 演变
4. **持仓组合** - 多腿策略构建器
5. **持仓对比** - 头寸叠加对比
6. **Volga 分析** - 二阶 Greeks 分析
7. **Volga 持仓** - Volga 头寸跟踪
8. **数据检查** - 数据完整性验证

### 数据采集

> **💡 推荐用法**：先清空数据库，然后采集一次数据，获取某个时刻的完整快照进行分析。这样可以确保所有期权数据都是同一时刻的状态，分析结果更准确。
>
> **🔬 高级用法**：如果不清空数据库，同一品种会保留多个时刻的希腊值，可以用于时序对比分析。一个工具，多种用法，期待你的发现！

在 Streamlit 界面中：
1. 从侧边栏选择"数据概览"
2. **建议先点击"清空数据库"**（侧边栏 → 数据管理）
3. 点击"采集数据"按钮
4. 选择采集模式：
   - **快速模式**：仅摘要数据（1-2 分钟）
   - **完整模式**：摘要 + Greeks 数据（5-10 分钟）

---

## 🔧 常用命令

```bash
# 启动 Streamlit 应用
streamlit run app.py

# 检查数据库快照
python scripts/check_data.py

# 采集 Greeks 数据
python scripts/collect_greeks_data.py

# 检查数据质量
python scripts/check_data_quality.py

# 回填交易量数据
python scripts/backfill_volume_data.py
```

---

## 📊 数据库

### 存储
- **数据库**：`options_data.duckdb`（DuckDB OLAP 数据库）
- **表**：
  - `options_chain` - 期权合约及市场数据
  - `options_greeks` - 计算的 Greeks
  - `portfolios` - 用户定义的投资组合
  - `portfolio_positions` - 投资组合头寸

### 访问模式
- 分析视图只读访问
- 数据采集时写入访问
- 首次运行时自动创建表

---

## 🧪 测试

```bash
# 运行特定测试文件
python tests/test_bs_calculator.py
python tests/test_portfolio_analyzer.py
python tests/test_cross_section.py
```

---

## 🔒 安全注意事项

⚠️ **重要**：
- 永远不要将包含 API 凭证的文件提交到公共仓库
- 分析任务使用只读 API 密钥
- 推荐使用测试环境凭证进行开发
- `.env` 文件已被 git 忽略以确保安全

---

## 📚 文档

- **CLAUDE.md** - 详细架构和开发指南
- **CHANGELOG.md** - 版本历史和变更

---

## 💡 提示

- **推荐工作流**：清空数据库 → 采集数据 → 分析快照 → 清空 → 再次采集（获取新快照）
- 这样可以保证每次分析的都是同一时刻的完整市场状态
- 使用**快速模式**进行初始数据探索
- **完整模式**包括所有合约的 Greeks 计算
- 数据库是持久的 - 关闭应用后数据仍然保留
- 如果不清空数据库，可以保留多个时刻的数据进行时序对比（高级用法）
- 使用投资组合构建器模拟复杂的多腿策略

---

## 🎓 教育用途

本项目设计为学习工具，用于：
- Black-Scholes 定价模型实现
- Greeks 计算和风险管理
- 期权投资组合构建和分析
- 波动率曲面分析

---

> **免责声明**：本项目仅用于教育和研究目的。不构成投资建议。使用风险自负。
