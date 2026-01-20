# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Deribit derivatives analytics platform for ETH options, providing **snapshot-based static analysis** of option chains with Black-Scholes pricing and Greeks calculation.

**Key Features**:
1. **Snapshot Analysis System** - Streamlit-based interactive analysis of option chains
2. **Black-Scholes Greeks Engine** - Vectorized calculations for first and second-order Greeks
3. **Portfolio Builder** - Multi-leg strategy construction with aggregated risk metrics
4. **Educational Framework** - Code aligned with options Greeks course curriculum

**Key Technologies**: Python 3.8+, DuckDB (OLAP), Streamlit, NumPy/SciPy

## Common Commands

### Main Application
```bash
# Launch Streamlit analysis dashboard
streamlit run app.py
# Access: http://localhost:8501

# Test environment without API credentials
python tests/test_mock_api.py
```

### Testing
```bash
# Run individual test files (direct execution, no pytest framework)
python tests/test_bs_calculator.py
python tests/test_portfolio_analyzer.py
python tests/test_cross_section.py
python tests/test_time_series.py
```

### Utilities
```bash
# Check database snapshots
python scripts/check_data.py

# Manual data fetch (for debugging)
python scripts/manual_fetch_and_save.py

# Collect Greeks data
python scripts/collect_greeks_data.py

# Check data quality
python scripts/check_data_quality.py

# Backfill volume data
python scripts/backfill_volume_data.py
```

## Architecture

### Single Database System

**options_data.duckdb** - Analytical snapshots (DuckDB OLAP database)
- Tables:
  - `options_chain` - Option contracts and market data
  - `options_greeks` - Calculated Greeks values
  - `portfolios` - User-defined portfolios
  - `portfolio_positions` - Portfolio positions
- Managed by: `OptionsDatabase` (src/core/database.py)
- Refreshable: Clear and reload with new snapshots
- Access pattern: Read-only for analysis views, write during data collection
- Auto-creates tables on first run

### Data Flow Pattern

**Snapshot Analysis (HTTP → Database → UI)**:
```
Deribit REST API
  ↓ (HTTP batch requests)
DataCollector (src/collectors/)
  ↓ (bulk insert)
options_data.duckdb
  ↓ (read-only)
Streamlit Views (views/*.py)
  ↓ (interactive UI)
User Analysis
```

**Recommended Workflow**: Clear database → Collect snapshot → Analyze → Clear → Collect new snapshot
- Ensures all option data is from the same moment in time
- Provides accurate cross-sectional analysis
- Advanced: Keep multiple snapshots for time-series comparison

### Key Components

**Black-Scholes Greeks Engine** (`src/core/bs_calculator.py`):
- Vectorized NumPy calculations for performance
- **First-order Greeks**: Delta, Gamma, Theta, Vega, Rho
- **Second-order Greeks**: Vanna, Volga (volatility convexity)
- **Scenario analysis**: Price sweeps, time decay projections, IV shock simulations
- Used by: Streamlit views, PortfolioAnalyzer, data collectors

**PortfolioAnalyzer** (`src/core/portfolio_analyzer.py`):
- Multi-leg position aggregation
- Net Greeks calculation across positions
- Scenario analysis for portfolio-level risk
- Strategy templates: straddles, strangles, spreads, butterflies, iron condors

**OptionsDatabase** (`src/core/database.py`):
- DuckDB interface for option chain and Greeks storage
- Batch insertion for efficient data loading
- Query helpers for analysis views
- Schema management and table creation

**DataCollector** (`src/collectors/data_collector.py`):
- Orchestrates fetching from Deribit REST API
- Two modes:
  - **Quick mode**: Summary data only (1-2 minutes)
  - **Full mode**: Summary + Greeks calculation (5-10 minutes)
- Batch processing for API efficiency
- Data validation and completeness checks

**Streamlit Views** (`views/*.py`):
- **dashboard.py**: Overview and data collection controls
- **cross_section.py**: IV smile, Greeks by strike
- **time_series.py**: Term structure, IV evolution
- **portfolio.py**: Portfolio builder with risk metrics
- **portfolio_compare.py**: Position overlay comparisons
- **volga_analysis.py**: Second-order Greeks analysis
- **volga_holding.py**: Volga position tracking
- **data_check.py**: Data completeness validation

## Project Structure

```
/
├── app.py                      # Streamlit entry point
├── config.py                   # UI configuration (colors, labels, risk-free rate)
├── credentials.py              # API credentials (git-ignored, generated from .env)
│
├── api/
│   ├── Deribit_HTTP.py        # REST API client
│   └── __init__.py
│
├── src/
│   ├── collectors/            # Data fetching orchestration
│   │   ├── data_collector.py
│   │   ├── data_fetcher.py
│   │   └── data_completeness_checker.py
│   │
│   ├── core/                  # Core algorithms
│   │   ├── bs_calculator.py   # Black-Scholes Greeks engine
│   │   ├── portfolio_analyzer.py  # Portfolio aggregation
│   │   └── database.py        # OptionsDatabase (DuckDB)
│   │
│   └── utils/                 # UI and data utilities
│       ├── ui_components.py   # Streamlit UI helpers
│       ├── chart_plotters.py  # Plotting functions
│       ├── data_preparers.py  # Data transformation
│       └── app_utils.py       # General utilities
│
├── views/                      # Streamlit pages (8 analysis views)
│   ├── dashboard.py           # Overview + data collection
│   ├── cross_section.py       # IV smile, Greeks by strike
│   ├── time_series.py         # Term structure, time decay
│   ├── portfolio.py           # Portfolio builder
│   ├── portfolio_compare.py   # Position comparison
│   ├── volga_analysis.py      # Second-order Greeks
│   ├── volga_holding.py       # Volga position tracking
│   └── data_check.py          # Data completeness
│
├── scripts/                    # Utility scripts
│   ├── check_data.py          # Database inspection
│   ├── manual_fetch_and_save.py
│   ├── collect_greeks_data.py
│   ├── check_data_quality.py
│   └── backfill_volume_data.py
│
├── tests/                      # Test files (direct execution)
│   ├── test_bs_calculator.py
│   ├── test_portfolio_analyzer.py
│   ├── test_cross_section.py
│   └── test_time_series.py
│
└── options_data.duckdb        # DuckDB database (created on first run)
```

## Important Patterns

### Risk-Free Rate Configuration
- Configurable via `.env` file: `RISK_FREE_RATE=0.05`
- Loaded into `config.py` at startup
- Used consistently across all Black-Scholes calculations
- Default: 5% (0.05)

### Data Collection Modes
1. **Quick Mode**:
   - Fetches summary data only
   - Fast (1-2 minutes)
   - Good for initial exploration

2. **Full Mode**:
   - Fetches summary + calculates Greeks for all contracts
   - Slower (5-10 minutes)
   - Complete dataset for analysis

### Snapshot-Based Analysis
- **Recommended**: Clear database before each collection
- Ensures temporal consistency (all data from same moment)
- Accurate cross-sectional analysis (IV smile, Greeks distribution)
- **Advanced**: Keep multiple snapshots for time-series comparison (not recommended for beginners)

### DuckDB Access Patterns
- **Read operations**: Multiple concurrent reads allowed
- **Write operations**: Data collection locks database briefly
- **Table creation**: Auto-creates schema on first run
- **Persistence**: Database file survives app restarts

## Configuration

### Environment Setup
```bash
# Copy template
cp .env.example .env

# Edit .env with Deribit credentials
# DERIBIT_ENV=test (or prod)
# DERIBIT_CLIENT_ID_TEST=your_client_id
# DERIBIT_CLIENT_SECRET_TEST=your_client_secret
# RISK_FREE_RATE=0.05
```

### Credentials File
- `.env` is git-ignored for security
- `credentials.py` is auto-generated from `.env` at runtime
- Never commit API keys to version control

## Development Workflow

### Starting the Application
```bash
# 1. Ensure .env is configured
cat .env  # verify credentials exist

# 2. Launch Streamlit
streamlit run app.py

# 3. In browser (http://localhost:8501):
#    - Select "数据概览" (Data Overview)
#    - Click "清空数据库" (Clear Database) - recommended
#    - Click "采集数据" (Collect Data)
#    - Choose mode (Quick/Full)
#    - Wait for collection to complete
#    - Navigate to analysis views
```

### Common Issues
- **ImportError**: Check `pip install -r requirements.txt` completed
- **API authentication failed**: Verify `.env` credentials
- **Database locked**: Close other processes accessing `options_data.duckdb`
- **No data in views**: Run data collection first (see above)

## Code Architecture Insights

### Greeks Calculation Flow
1. **Data Collection**: Fetch market data (spot, strikes, IVs, expiries)
2. **BS Calculation**: Vectorized computation across all contracts
3. **Database Storage**: Bulk insert into `options_greeks` table
4. **View Queries**: Read from database, apply filters, generate charts

### Educational Alignment
Code structure maps to options Greeks course modules:
- `src/core/bs_calculator.py` → Pricing fundamentals, Greeks formulas
- `views/cross_section.py` → Volatility smile analysis
- `views/time_series.py` → IV term structure
- `views/portfolio.py` → Greeks aggregation, multi-leg strategies
- `views/volga_analysis.py` → Second-order Greeks, convexity trading

### Streamlit Reactive Pattern
- Views react to user inputs (date sliders, strike filters, portfolio selections)
- Data fetched from database on each interaction
- Charts regenerated dynamically
- State managed via Streamlit session state

## API Client Notes

**Deribit HTTP** (`api/Deribit_HTTP.py`):
- **Purpose**: One-time batch queries (instrument lists, order books)
- **Authentication**: Client ID + Secret (Basic Auth)
- **Retry strategy**: 3 attempts with exponential backoff
- **Endpoints used**:
  - `/public/get_instruments` - List all options
  - `/public/get_book_summary_by_instrument` - Market data per contract
  - `/public/ticker` - Real-time ticker data
- **Rate limiting**: Respects Deribit API limits (automatic backoff)

## Testing Strategy

- **No pytest framework**: Tests are standalone Python scripts
- **Execution**: `python tests/test_*.py` (direct execution)
- **Coverage**:
  - `test_bs_calculator.py`: Greeks calculation accuracy
  - `test_portfolio_analyzer.py`: Portfolio aggregation logic
  - `test_cross_section.py`: IV smile view functionality
  - `test_time_series.py`: Term structure view functionality
- **Mock data**: `test_mock_api.py` demonstrates no-API-credentials mode

## Performance Notes

- **Vectorization**: NumPy operations across entire option chain (fast)
- **Database**: DuckDB OLAP engine optimized for analytical queries
- **Data loading**: Batch inserts minimize disk I/O
- **Streamlit caching**: Use `@st.cache_data` for expensive queries (already implemented)

## Security Notes

⚠️ **Important**:
- Never commit `.env` or `credentials.py` to version control
- Use read-only API keys for analysis tasks
- Recommended: Test environment credentials for development
- Production credentials: Only for live trading analysis
- `.env` is git-ignored by default (verified in `.gitignore`)

## Common Tasks

### Adding a New Analysis View
1. Create `views/new_view.py`
2. Import necessary utilities from `src/utils/`
3. Add page to `app.py` sidebar navigation
4. Query data from `OptionsDatabase`
5. Use `chart_plotters.py` for visualizations

### Modifying Greeks Calculations
1. Edit `src/core/bs_calculator.py`
2. Update formulas (preserve vectorization)
3. Run `python tests/test_bs_calculator.py`
4. Verify results match theoretical values

### Changing Database Schema
1. Modify table definitions in `src/core/database.py`
2. Delete `options_data.duckdb` (forces recreation)
3. Restart app (tables auto-created)
4. Re-collect data

## Documentation

- **CLAUDE.md** (this file) - Architecture and development guide
- **README.md** - User-facing documentation (Chinese)
- **README_EN.md** - User-facing documentation (English)
- **CHANGELOG.md** - Version history and changes

## Tips for Contributors

- **Recommended workflow**: Clear DB → Collect snapshot → Analyze (ensures data consistency)
- **Quick mode**: Use for rapid iteration during development
- **Full mode**: Use for complete analysis (includes all Greeks)
- **Database persistence**: Data survives app restarts (clear manually if needed)
- **Portfolio builder**: Supports complex multi-leg strategies (test with real data)
- **Volga analysis**: Second-order Greeks useful for volatility trading research
