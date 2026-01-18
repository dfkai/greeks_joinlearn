# Deribit Options Analytics
# Deribit 期权分析系统

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![DuckDB](https://img.shields.io/badge/DuckDB-0.9%2B-yellow)

A comprehensive Deribit options analytics platform for static analysis of option chains with Black-Scholes pricing and Greeks calculation.

基于 Deribit 交易所的期权链静态分析系统，提供完整的 Black-Scholes 定价和 Greeks 风险计算。

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API credentials
cp .env.example .env
# Edit .env and add your Deribit API credentials

# 3. Launch Streamlit dashboard
streamlit run app.py
# Visit: http://localhost:8501
```

---

## 🚀 Deployment

### Deploy to Streamlit Cloud (Recommended - 5 minutes)

[![Deploy](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

1. Push this repo to your GitHub
2. Go to [Streamlit Cloud](https://share.streamlit.io)
3. Create new app → Select this repo
4. Add Deribit API credentials in Secrets (see [API Setup Guide](docs/API_SETUP.md))
5. Deploy!

**Live in minutes at:** `https://[username]-greeks-analytics.streamlit.app`

📘 **Full deployment guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
🔑 **API credentials setup**: [docs/API_SETUP.md](docs/API_SETUP.md)

### Other Deployment Options

| Platform | Setup Time | Cost | Best For |
|----------|-----------|------|----------|
| **Streamlit Cloud** | 5 min | Free | Quick demos, education |
| **Hugging Face Spaces** | 10 min | Free | Research, collaboration |
| **Railway** | 15 min | $5/mo credit | Professional deployments |
| **Docker** | 30 min | Varies | Self-hosting, enterprise |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

### Quick Docker Run

```bash
# Build image
docker build -t greeks-analytics .

# Run container
docker run -p 8501:8501 --env-file .env greeks-analytics

# Access at http://localhost:8501
```

### ❌ Why Vercel Won't Work

Vercel cannot deploy Streamlit applications because:
- Streamlit requires **persistent Python processes** (Vercel is serverless)
- Streamlit needs **WebSocket support** (limited on Vercel)
- Python on Vercel is for **short-lived functions only** (max 10s)

Use platforms designed for persistent web apps instead (see options above).

---

## 📊 Core Features

### 1. IV Analysis
- **Volatility Smile**: IV skew across strikes
- **Term Structure**: IV evolution over time
- **Skew Analysis**: Put/Call IV differential

### 2. Portfolio Builder
- **Multi-leg Strategies**: Straddle, Strangle, Iron Condor, Butterfly, etc.
- **Greeks Aggregation**: Net Delta, Gamma, Theta, Vega, Rho
- **Risk Scenarios**: Price sweeps, time decay, IV shock simulations

### 3. Advanced Greeks
- **Volga (Convexity)**: Second-order volatility risk ∂²V/∂σ²
- **Vanna (Correlation)**: Cross-greek ∂Δ/∂σ
- **Volga-Vega Clustering**: Identify optimal contracts

### 4. Data Quality Tools
- **Completeness Check**: Volume data validation
- **Database Inspection**: Snapshot history analysis
- **Backfill Utilities**: Missing data recovery

---

## 🏗️ Project Structure

```
/
├── app.py                      # Streamlit entry point
├── config.py                   # UI configuration (colors, labels)
├── views/                      # 8 analysis views
│   ├── cross_section.py       # IV smile, Greeks by strike
│   ├── time_series.py         # Term structure, IV trends
│   ├── portfolio.py           # Portfolio builder
│   ├── volga_analysis.py      # Second-order Greeks
│   └── ...
├── src/
│   ├── core/                  # Core algorithms
│   │   ├── bs_calculator.py   # Black-Scholes Greeks engine
│   │   ├── portfolio_analyzer.py  # Portfolio aggregation
│   │   └── database.py        # OptionsDatabase (DuckDB)
│   └── collectors/            # Data fetching
│       ├── data_collector.py
│       └── data_completeness_checker.py
├── api/
│   └── Deribit_HTTP.py        # REST API client
├── scripts/                    # Utilities
│   ├── check_data.py          # Database inspection
│   ├── collect_greeks_data.py # Greeks data collection
│   └── ...
└── tests/                      # Test files
```

---

## 🛠️ Installation

### System Requirements
- Python 3.8+
- DuckDB (auto-installed via pip)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configuration

1. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```

2. **Add Deribit API credentials**:
   ```env
   # Environment: test or prod
   DERIBIT_ENV=test

   # Test environment credentials (recommended)
   DERIBIT_CLIENT_ID_TEST=your_client_id
   DERIBIT_CLIENT_SECRET_TEST=your_client_secret

   # Optional: Risk-free rate (default: 0.05)
   RISK_FREE_RATE=0.05
   ```

3. **Get API credentials**:
   - Test net: [test.deribit.com](https://test.deribit.com) → Settings → API
   - Production: [www.deribit.com](https://www.deribit.com) → Settings → API
   - Recommended permissions: Read-only

---

## 📖 Usage

### Launch Application

```bash
streamlit run app.py
```

The application will open in your browser at http://localhost:8501

### Available Views

1. **Data Overview** - Quick summary and data collection
2. **Cross Section** - IV smile and Greeks by strike
3. **Time Series** - Term structure and IV evolution
4. **Portfolio** - Multi-leg strategy builder
5. **Portfolio Compare** - Position overlay comparison
6. **Volga Analysis** - Second-order Greeks analysis
7. **Volga Holding** - Volga position tracking
8. **Data Check** - Data completeness verification

### Data Collection

In the Streamlit interface:
1. Select "Data Overview" from the sidebar
2. Click "Collect Data" button
3. Choose collection mode:
   - **Quick Mode**: Summary data only (1-2 minutes)
   - **Full Mode**: Summary + Greeks data (5-10 minutes)

---

## 🔧 Common Commands

```bash
# Launch Streamlit application
streamlit run app.py

# Check database snapshots
python scripts/check_data.py

# Collect Greeks data
python scripts/collect_greeks_data.py

# Check data quality
python scripts/check_data_quality.py

# Backfill volume data
python scripts/backfill_volume_data.py
```

---

## 📊 Database

### Storage
- **Database**: `options_data.duckdb` (DuckDB OLAP database)
- **Tables**:
  - `options_chain` - Option contracts with market data
  - `options_greeks` - Calculated Greeks
  - `portfolios` - User-defined portfolios
  - `portfolio_positions` - Portfolio positions

### Access Pattern
- Read-only access for analysis views
- Write access during data collection
- Automatic table creation on first run

---

## 🧪 Testing

```bash
# Run specific test files
python tests/test_bs_calculator.py
python tests/test_portfolio_analyzer.py
python tests/test_cross_section.py
```

---

## 🔒 Security Notes

⚠️ **IMPORTANT**:
- Never commit files containing API credentials to public repositories
- Use Read-Only API keys for analysis tasks
- Test environment credentials are recommended for development
- `.env` file is git-ignored for security

---

## 📚 Documentation

- **CLAUDE.md** - Detailed architecture and development guide
- **CHANGELOG.md** - Version history and changes

---

## 💡 Tips

- Use **Quick Mode** for initial data exploration
- **Full Mode** includes Greeks calculation for all contracts
- The database is persistent - data remains after closing the application
- Refresh data periodically to get the latest market conditions
- Use portfolio builder to simulate complex multi-leg strategies

---

## 🎓 Educational Use

This project is designed as a learning tool for:
- Black-Scholes pricing model implementation
- Greeks calculation and risk management
- Option portfolio construction and analysis
- Volatility surface analysis

---

> **Disclaimer**: This project is for educational and research purposes only. It does not constitute investment advice. Use at your own risk.
