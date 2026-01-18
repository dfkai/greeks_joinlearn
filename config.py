"""
配置文件
统一管理应用配置
"""

# 数据库配置
DEFAULT_DB_PATH = "options_data.duckdb"
TEST_DB_PATH = "test_options.duckdb"

# 默认货币类型
DEFAULT_CURRENCY = "ETH"

# 数据获取配置
DEFAULT_MAX_WORKERS = 10
DEFAULT_DATA_LIMIT = 10000

# 图表配置
CHART_HEIGHT = 500
CHART_TEMPLATE = "plotly_white"

# Greeks参数标签
GREEKS_LABELS = {
    'delta': 'Delta',
    'gamma': 'Gamma',
    'theta': 'Theta',
    'vega': 'Vega',
    'rho': 'Rho'
}

# 图表颜色配置
CHART_COLORS = {
    'call': '#2E86AB',
    'put': '#A23B72'
}

