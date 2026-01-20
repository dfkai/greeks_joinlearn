"""
PostHog 集成测试脚本
用于验证 PostHog 是否正确配置和工作
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 60)
print("PostHog 集成测试")
print("=" * 60)

# 检查配置
print("\n1. 检查环境变量配置:")
print(f"   ENABLE_POSTHOG: {os.getenv('ENABLE_POSTHOG')}")
print(f"   POSTHOG_HOST: {os.getenv('POSTHOG_HOST')}")
api_key = os.getenv('POSTHOG_API_KEY', '')
if api_key:
    print(f"   POSTHOG_API_KEY: {api_key[:15]}... (已配置)")
else:
    print(f"   POSTHOG_API_KEY: 未配置")

# 测试导入
print("\n2. 测试导入 PostHog 工具模块:")
try:
    from src.utils import (
        init_posthog,
        track_event,
        track_page_view,
        track_data_collection
    )
    print("   ✅ 导入成功")
except ImportError as e:
    print(f"   ❌ 导入失败: {e}")
    exit(1)

# 测试初始化
print("\n3. 测试 PostHog 初始化:")
try:
    init_posthog()
    print("   ✅ 初始化成功")
except Exception as e:
    print(f"   ❌ 初始化失败: {e}")
    exit(1)

# 测试发送事件
print("\n4. 测试发送事件:")
try:
    # 发送测试事件
    track_event("test_event", {
        "test": True,
        "source": "test_script"
    })
    print("   ✅ 事件发送成功 (异步发送，请稍后在 PostHog 仪表板查看)")

    # 发送页面浏览事件
    track_page_view("test_page", test=True)
    print("   ✅ 页面浏览事件发送成功")

    # 发送数据采集事件
    track_data_collection(
        mode="test",
        success=True,
        duration_seconds=1.5,
        record_count=100
    )
    print("   ✅ 数据采集事件发送成功")

except Exception as e:
    print(f"   ❌ 事件发送失败: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)
print("\n💡 下一步:")
print("   1. 访问 PostHog 仪表板: https://app.posthog.com")
print("   2. 查看 'Events' 页面，应该能看到以下测试事件:")
print("      - test_event")
print("      - page_view")
print("      - data_collection")
print("\n   注意: PostHog 使用异步批量发送，事件可能需要")
print("         几秒到几分钟才会在仪表板中显示。")
print("=" * 60)
