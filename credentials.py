"""
API 凭证配置
从环境变量读取，支持 .env 文件
支持测试和实盘环境切换
"""
import os
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except ImportError:
    # 如果没有安装 python-dotenv，直接从环境变量读取
    pass

# 获取环境类型（test 或 prod）
# 如果没有明确指定，检查是否有专用的测试/实盘凭证
# 如果都没有，默认使用实盘（保持向后兼容，因为之前HTTP API默认是实盘）
env_type = os.getenv('DERIBIT_ENV', '').lower()

# 智能检测环境类型
if not env_type:
    # 如果用户配置了专用的测试凭证，默认使用测试环境
    if os.getenv('DERIBIT_CLIENT_ID_TEST') or os.getenv('DERIBIT_CLIENT_SECRET_TEST'):
        env_type = 'test'
    # 如果用户配置了专用的实盘凭证，使用实盘环境
    elif os.getenv('DERIBIT_CLIENT_ID_PROD') or os.getenv('DERIBIT_CLIENT_SECRET_PROD'):
        env_type = 'prod'
    # 如果只配置了通用凭证，默认使用实盘（向后兼容）
    else:
        env_type = 'prod'

# 根据环境类型选择凭证
if env_type == 'prod':
    # 实盘环境
    client_id = os.getenv('DERIBIT_CLIENT_ID_PROD', os.getenv('DERIBIT_CLIENT_ID', ''))
    client_secret = os.getenv('DERIBIT_CLIENT_SECRET_PROD', os.getenv('DERIBIT_CLIENT_SECRET', ''))
    http_base_url = os.getenv('DERIBIT_HTTP_URL', 'https://www.deribit.com/api/v2')
    client_url = os.getenv('DERIBIT_WS_URL', 'wss://www.deribit.com/ws/api/v2')
else:
    # 测试环境
    client_id = os.getenv('DERIBIT_CLIENT_ID_TEST', os.getenv('DERIBIT_CLIENT_ID', ''))
    client_secret = os.getenv('DERIBIT_CLIENT_SECRET_TEST', os.getenv('DERIBIT_CLIENT_SECRET', ''))
    http_base_url = os.getenv('DERIBIT_HTTP_URL', 'https://test.deribit.com/api/v2')
    client_url = os.getenv('DERIBIT_WS_URL', 'wss://test.deribit.com/ws/api/v2')

# 验证凭证是否存在
if not client_id or not client_secret:
    import warnings
    warnings.warn(
        f"Deribit API 凭证未配置（当前环境: {env_type}）！请创建 .env 文件或设置环境变量。\n"
        f"测试环境变量: DERIBIT_CLIENT_ID_TEST, DERIBIT_CLIENT_SECRET_TEST\n"
        f"实盘环境变量: DERIBIT_CLIENT_ID_PROD, DERIBIT_CLIENT_SECRET_PROD\n"
        f"或使用通用变量: DERIBIT_CLIENT_ID, DERIBIT_CLIENT_SECRET\n"
        f"切换环境: 设置 DERIBIT_ENV=test 或 DERIBIT_ENV=prod"
    )
