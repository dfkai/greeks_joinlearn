"""
工具函数模块
- app_utils: 应用工具
- ui_components: UI组件
- data_preparers: 数据预处理
- chart_plotters: 图表绑定
"""

from .app_utils import load_database, load_data, apply_custom_css, apply_filters, get_statistics
from .ui_components import render_tag_selector
from .analytics import (
    init_posthog,
    track_event,
    track_page_view,
    track_data_collection,
    track_portfolio_action,
    track_error,
    identify_user,
    shutdown_posthog,
    track_function_call
)
from .data_preparers import (
    prepare_cross_section_data,
    prepare_cross_section_data_multi_greeks,
    prepare_time_series_data,
    prepare_time_series_data_multi_greeks,
    prepare_general_cross_section_data,
    prepare_breakeven_data,
    prepare_delta_skew_data
)
from .chart_plotters import (
    plot_cross_section_chart,
    plot_time_series_chart,
    plot_all_greeks_cross_section,
    plot_all_greeks_time_series,
    plot_breakeven_scatter,
    plot_delta_skew_chart
)

__all__ = [
    'load_database', 'load_data', 'apply_custom_css', 'apply_filters', 'get_statistics',
    'render_tag_selector',
    'prepare_cross_section_data', 'prepare_cross_section_data_multi_greeks',
    'prepare_time_series_data', 'prepare_time_series_data_multi_greeks',
    'prepare_general_cross_section_data', 'prepare_breakeven_data', 'prepare_delta_skew_data',
    'plot_cross_section_chart', 'plot_time_series_chart',
    'plot_all_greeks_cross_section', 'plot_all_greeks_time_series',
    'plot_breakeven_scatter', 'plot_delta_skew_chart',
    'init_posthog', 'track_event', 'track_page_view', 'track_data_collection',
    'track_portfolio_action', 'track_error', 'identify_user', 'shutdown_posthog',
    'track_function_call'
]

