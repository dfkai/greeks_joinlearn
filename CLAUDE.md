# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A dual-function Deribit derivatives analytics platform for ETH options combining:
1. **Snapshot Analysis System** - Streamlit-based static analysis of option chains with Black-Scholes pricing and Greeks calculation
2. **HyperMonitor** - Real-time position monitoring with React frontend, FastAPI backend, and WebSocket push architecture
3. **Educational Framework** - Code aligned with options Greeks course curriculum

**Key Technologies**: Python 3.8+, DuckDB (OLAP), Streamlit, React/TypeScript/Vite, FastAPI, WebSocket, NumPy/SciPy

## Common Commands

### Snapshot Analysis System
```bash
# Launch Streamlit analysis dashboard
streamlit run app.py

# Test environment without API credentials
python tests/test_mock_api.py
```

### HyperMonitor Real-time System
```bash
# Start backend (data collection + WebSocket server on port 8000)
python scripts/run_monitor.py

# Skip preflight network checks if needed
python scripts/run_monitor.py --skip-preflight

# Start frontend (in separate terminal)
cd hypermonitor/frontend
npm install  # first time only
npm run dev  # http://localhost:5173

# Frontend development
npm run build    # production build
npm run lint     # ESLint
```

### Testing
```bash
# Run individual test files (no pytest framework, direct execution)
python tests/test_bs_calculator.py
python tests/test_portfolio_analyzer.py
python hypermonitor/backend/tests/test_services.py  # pytest used here
```

### Utilities
```bash
# Check database snapshots
python scripts/check_data.py

# Monitor service status
python scripts/check_monitor_status.py

# Manual data fetch (for debugging)
python scripts/manual_fetch_and_save.py

# Cleanup old snapshots
python scripts/cleanup_old_snapshots.py
```

## Architecture

### Two-Database System

**options_data.duckdb** - Analytical snapshots
- Tables: `options_chain`, `options_greeks`, `portfolios`, `portfolio_positions`
- Managed by: `OptionsDatabase` (src/core/database.py)
- Refreshable: Clear and reload with new snapshots
- Used by: Streamlit views for static analysis

**monitor.duckdb** - Real-time monitoring (56MB typical)
- Tables: `position_snapshots`, `system_events`
- Managed by: `MonitorDatabase` (src/core/monitor_database.py)
- Archival: Historical position data for playback
- Short-connection pattern: Open → Execute → Close (prevents file lock conflicts)
- Write mutex + retry with exponential backoff for concurrency safety

### Data Flow Patterns

**Snapshot Analysis (HTTP → Database → UI)**:
```
Deribit REST API
  ↓ (HTTP batch requests)
DataCollector (src/collectors/)
  ↓ (bulk insert)
options_data.duckdb
  ↓ (read)
Streamlit Views (views/*.py)
```

**Real-time Monitoring (WebSocket → Push → UI)**:
```
Deribit WebSocket
  ↓ (ticker/portfolio subscriptions)
MonitorService (src/services/monitor_service.py)
  ├→ BSCalculator → Greeks per position
  ├→ PortfolioAnalyzer → Aggregate Greeks
  └→ realtime_push_service.push_snapshot()
      ↓ (singleton broadcast)
FastAPI WebSocketManager (hypermonitor/backend/websocket/)
  ↓ (msgpack + gzip, batched)
React Frontend (realtimeClient.ts)
  ↓ (Zustand store)
Dashboard Components
```

**Critical Design**: Push architecture eliminates frontend polling. MonitorService drives all updates via `realtime_push_service` singleton.

### Key Components

**Black-Scholes Greeks Engine** (`src/core/bs_calculator.py`):
- Vectorized NumPy calculations
- First-order Greeks: Delta, Gamma, Theta, Vega, Rho
- Second-order Greeks: Vanna, Volga (volatility convexity)
- Scenario analysis: price sweeps, time decay, IV shocks
- Used by: MonitorService, CalcService, Streamlit views

**MonitorService** (`src/services/monitor_service.py`):
- WebSocket subscriptions to Deribit (tickers + portfolio)
- Real-time Greeks calculation per position
- Snapshot interval: 60s default (configurable via `SNAPSHOT_INTERVAL_SECONDS`)
- Pushes updates immediately via `realtime_push_service`

**WebSocket Architecture** (`hypermonitor/backend/websocket/`):
- Manager: Connection pool (max 100 clients)
- Protocol: msgpack encoding + optional gzip compression
- Message batching: 32 messages or 10ms flush interval
- Heartbeat: 30s keep-alive
- Auto-reconnect: Frontend retries up to 10 times with exponential backoff

**Frontend State** (`hypermonitor/frontend/src/store/realtimeStore.ts`):
- Three modes: `realtime`, `playback`, `trend`
- History buffer: 60 recent snapshots in memory
- Older data: Fetched from REST `/api/snapshots` endpoint

## Project Structure

```
/
├── app.py                      # Streamlit entry point
├── config.py                   # Global configuration
├── credentials.py              # API credentials (git-ignored)
│
├── api/
│   ├── Deribit_HTTP.py        # REST client
│   └── Deribit_WSS_2.py       # WebSocket client
│
├── src/
│   ├── collectors/            # Data fetching orchestration
│   ├── core/                  # BS calculator, databases, portfolio analyzer
│   ├── services/              # MonitorService (real-time collection)
│   └── utils/
│
├── views/                      # Streamlit pages (9 analysis views)
│   ├── cross_section.py       # IV smile, Greeks by strike
│   ├── time_series.py         # Term structure, time decay
│   ├── portfolio.py           # Portfolio builder
│   └── volga_analysis.py      # Second-order Greeks
│
├── hypermonitor/
│   ├── backend/               # FastAPI + WebSocket server
│   │   ├── app.py            # FastAPI setup
│   │   ├── api/              # REST endpoints (/snapshots, /health)
│   │   ├── services/         # realtime_push_service (singleton)
│   │   └── websocket/        # Manager, handlers, protocol
│   │
│   └── frontend/             # React + TypeScript + Vite
│       └── src/
│           ├── features/dashboard/  # Main dashboard components
│           ├── services/realtimeClient.ts  # WebSocket client
│           └── store/realtimeStore.ts      # Zustand state
│
├── scripts/
│   ├── run_monitor.py        # Main launcher (MonitorService + FastAPI)
│   ├── check_data.py         # Database inspection
│   └── cleanup_old_snapshots.py
│
└── tests/                     # Direct Python execution (no pytest at root)
```

## Important Patterns

### DuckDB File Locking Mitigation
MonitorDatabase uses short-connection pattern to avoid lock conflicts:
- Each operation: `connect() → execute() → close()`
- Write operations protected by `threading.Lock`
- Retry logic with exponential backoff (max 3 attempts)
- Read operations use `read_only=True` flag

### Singleton Services
- `realtime_push_service`: Single instance coordinates all WebSocket broadcasts
- Initialized in `hypermonitor/backend/app.py` before MonitorService starts
- MonitorService retrieves singleton via `get_realtime_push_service()`

### WebSocket Message Types
1. **realtime_snapshot**: Position data with diff (changed fields only)
2. **service_heartbeat**: Service status, reconnect count, error messages

### Risk-Free Rate
Configurable via `.env` (`RISK_FREE_RATE=0.05`), used consistently across all BS calculations.

## Configuration

### Environment Setup
```bash
# Copy template
cp .env.example .env

# Edit .env with Deribit credentials
# DERIBIT_ENV=test (or prod)
# DERIBIT_CLIENT_ID_TEST=...
# DERIBIT_CLIENT_SECRET_TEST=...
# SNAPSHOT_INTERVAL_SECONDS=60
# RISK_FREE_RATE=0.05
```

### Frontend Configuration
Create `hypermonitor/frontend/.env`:
```env
VITE_REALTIME_WS=ws://localhost:8000/ws/realtime
VITE_AUTO_CONNECT_REALTIME=true
VITE_ENABLE_MOCK_DATA=false  # fallback demo data when disconnected
```

## Development Workflow

### Starting Full System
1. **Backend**: `python scripts/run_monitor.py` (terminal 1)
   - Starts MonitorService (Deribit WebSocket collector)
   - Starts FastAPI server (port 8000)
   - DO NOT run `uvicorn` separately (causes port conflict)

2. **Frontend**: `cd hypermonitor/frontend && npm run dev` (terminal 2)
   - Dev server on port 5173
   - Auto-connects to backend WebSocket

### Common Issues
- **Port 8000 in use**: Check for duplicate `run_monitor.py` or `uvicorn` processes
- **WebSocket connection failed**: Verify backend started successfully, check firewall
- **No real-time data**: Check Deribit credentials, review terminal logs for connection errors
- **Database locked**: Restart services (short-connection pattern should prevent this)

## Code Architecture Insights

### Separation of Concerns
- **Analytical system** (options_data.duckdb): Refreshable snapshots, batch HTTP queries
- **Monitoring system** (monitor.duckdb): Archival time-series, WebSocket streams
- Two databases prevent interference: portfolio analysis won't block real-time monitoring

### Greeks Calculation Distribution
- **Backend**: Pre-calculates Greeks per position during snapshot saves
- **Frontend**: Can recalculate Greeks curves locally (lower latency for UI interactions)
- **Streamlit**: Interactive portfolio builder with on-demand Greeks computation

### Async/Sync Hybrid
- FastAPI backend: Async handlers coordinate with thread pools for CPU-intensive tasks
- CalcService: Offloads BS calculations to `ThreadPoolExecutor`
- MonitorService: Sync class runs in dedicated thread, pushes to async WebSocket layer

### Course Alignment
Code structure maps to educational modules (see `docs/course/README.md`):
- `src/core/bs_calculator.py` → Variables, pricing fundamentals
- `views/cross_section.py` → Volatility smile analysis
- `views/time_series.py` → IV term structure
- `views/portfolio.py` → Greeks aggregation
- `views/volga_analysis.py` → Second-order Greeks trading

## API Client Notes

**Deribit HTTP** (`api/Deribit_HTTP.py`):
- Used for: One-time queries (instrument lists, book summaries)
- Auth: Basic auth with client_id/secret
- Retry strategy: 3 attempts with exponential backoff

**Deribit WebSocket** (`api/Deribit_WSS_2.py`):
- Used for: Continuous monitoring (portfolio, tickers)
- Auth: Token-based (auto-refresh)
- JSON-RPC format with ID-based request matching
- Channels: `ticker.{instrument}.raw`, `user.portfolio.{currency}`

## Frontend Architecture

**State Management**: Zustand (lightweight, no Redux boilerplate)
- `realtimeStore.ts`: Real-time/playback mode switching, snapshot history
- React components subscribe to store slices

**UI Components** (`src/features/dashboard/`):
- RealtimeDashboard: Main container
- PositionsPanel: Position details with virtualized scrolling
- PortfolioAnalysisChart: Greeks curves (Recharts)
- HistoryPanel: Time-series playback with slider

**Styling**: Tailwind CSS with custom glassmorphism theme, Ant Design components

**Performance**:
- Virtual scrolling for large position lists (`@tanstack/react-virtual`)
- Message batching to prevent UI freezes
- Diff-based updates (only changed fields transmitted)
