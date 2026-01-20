"""
PostHog 分析工具模块
用于跟踪用户行为、功能使用和错误监控
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import wraps
import streamlit as st

logger = logging.getLogger(__name__)

# 全局 PostHog 客户端实例
_posthog_client = None
_posthog_enabled = False


def init_posthog():
    """
    初始化 PostHog 客户端
    仅在配置启用时才初始化
    """
    global _posthog_client, _posthog_enabled

    # 检查是否启用
    enabled = os.getenv('ENABLE_POSTHOG', 'false').lower() == 'true'

    if not enabled:
        logger.info("PostHog 分析已禁用（ENABLE_POSTHOG=false）")
        _posthog_enabled = False
        return

    # 获取配置
    api_key = os.getenv('POSTHOG_API_KEY')
    host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')

    if not api_key or api_key == 'your_posthog_api_key_here':
        logger.warning("PostHog API Key 未配置，分析功能已禁用")
        _posthog_enabled = False
        return

    try:
        import posthog

        # 初始化 PostHog（7.x 版本新 API）
        from posthog import Posthog

        _posthog_client = Posthog(
            project_api_key=api_key,
            host=host,
            enable_exception_autocapture=True
        )

        _posthog_enabled = True

        logger.info(f"PostHog 分析已启用 (Host: {host})")

    except ImportError:
        logger.error("PostHog 库未安装，请运行: pip install posthog")
        _posthog_enabled = False
    except Exception as e:
        logger.error(f"PostHog 初始化失败: {e}")
        _posthog_enabled = False


def get_user_id() -> str:
    """
    获取或生成用户唯一标识
    使用 Streamlit session_state 持久化用户 ID
    """
    if 'posthog_user_id' not in st.session_state:
        # 生成匿名用户 ID
        import uuid
        st.session_state.posthog_user_id = f"anonymous_{uuid.uuid4().hex[:12]}"

    return st.session_state.posthog_user_id


def track_event(
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
):
    """
    跟踪用户事件

    Args:
        event_name: 事件名称（如 "page_view", "data_collection_started"）
        properties: 事件属性字典（如 {"page": "cross_section", "currency": "ETH"}）
        user_id: 用户 ID（可选，默认使用 session 用户 ID）
    """
    if not _posthog_enabled or _posthog_client is None:
        return

    try:
        uid = user_id or get_user_id()
        props = properties or {}

        # 添加公共属性
        props['app_name'] = 'greeks-analytics'
        props['streamlit_version'] = st.__version__

        _posthog_client.capture(
            distinct_id=uid,
            event=event_name,
            properties=props
        )

        logger.debug(f"PostHog 事件已发送: {event_name}, 用户: {uid}")

    except Exception as e:
        logger.error(f"PostHog 事件发送失败: {e}")


def track_page_view(page_name: str, **kwargs):
    """
    跟踪页面浏览

    Args:
        page_name: 页面名称
        **kwargs: 额外属性
    """
    properties = {
        'page': page_name,
        **kwargs
    }
    track_event('page_view', properties)


def track_data_collection(
    mode: str,
    success: bool,
    duration_seconds: Optional[float] = None,
    record_count: Optional[int] = None,
    error_message: Optional[str] = None
):
    """
    跟踪数据采集事件

    Args:
        mode: 采集模式（"quick" 或 "full"）
        success: 是否成功
        duration_seconds: 耗时（秒）
        record_count: 采集记录数
        error_message: 错误信息（失败时）
    """
    properties = {
        'mode': mode,
        'success': success,
    }

    if duration_seconds is not None:
        properties['duration_seconds'] = duration_seconds
    if record_count is not None:
        properties['record_count'] = record_count
    if error_message:
        properties['error_message'] = error_message

    track_event('data_collection', properties)


def track_portfolio_action(
    action: str,
    position_count: Optional[int] = None,
    **kwargs
):
    """
    跟踪组合操作

    Args:
        action: 操作类型（"create", "modify", "delete", "analyze"）
        position_count: 持仓数量
        **kwargs: 额外属性
    """
    properties = {
        'action': action,
        **kwargs
    }

    if position_count is not None:
        properties['position_count'] = position_count

    track_event('portfolio_action', properties)


def track_error(
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None
):
    """
    跟踪错误事件

    Args:
        error_type: 错误类型
        error_message: 错误信息
        context: 上下文信息
    """
    properties = {
        'error_type': error_type,
        'error_message': error_message,
    }

    if context:
        properties.update(context)

    track_event('error_occurred', properties)


def identify_user(
    user_id: str,
    properties: Optional[Dict[str, Any]] = None
):
    """
    识别用户并设置用户属性

    Args:
        user_id: 用户唯一标识
        properties: 用户属性（如 {"plan": "pro", "signup_date": "2026-01-20"}）
    """
    if not _posthog_enabled or _posthog_client is None:
        return

    try:
        props = properties or {}
        _posthog_client.identify(
            distinct_id=user_id,
            properties=props
        )

        # 更新 session 中的用户 ID
        st.session_state.posthog_user_id = user_id

        logger.debug(f"PostHog 用户已识别: {user_id}")

    except Exception as e:
        logger.error(f"PostHog 用户识别失败: {e}")


def shutdown_posthog():
    """
    关闭 PostHog 客户端，确保所有事件已发送
    建议在应用退出时调用（Streamlit 会话结束时）
    """
    if _posthog_enabled and _posthog_client is not None:
        try:
            # PostHog 7.x 版本
            if hasattr(_posthog_client, 'shutdown'):
                _posthog_client.shutdown()
            logger.info("PostHog 客户端已关闭")
        except Exception as e:
            logger.error(f"PostHog 关闭失败: {e}")


def track_function_call(event_name: Optional[str] = None):
    """
    装饰器：自动跟踪函数调用

    用法:
        @track_function_call("custom_event_name")
        def my_function(arg1, arg2):
            ...

    Args:
        event_name: 自定义事件名称（可选，默认使用函数名）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()

            # 确定事件名称
            evt_name = event_name or f"function_call_{func.__name__}"

            try:
                result = func(*args, **kwargs)

                # 跟踪成功调用
                duration = time.time() - start_time
                track_event(evt_name, {
                    'success': True,
                    'duration_seconds': duration,
                    'function_name': func.__name__
                })

                return result

            except Exception as e:
                # 跟踪失败调用
                duration = time.time() - start_time
                track_event(evt_name, {
                    'success': False,
                    'duration_seconds': duration,
                    'function_name': func.__name__,
                    'error': str(e)
                })
                raise

        return wrapper
    return decorator
