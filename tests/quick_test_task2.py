"""快速测试任务二功能"""
from src.collectors import OptionsChainFetcher
import pandas as pd

print("="*60)
print("任务二：快速功能测试")
print("="*60)

fetcher = OptionsChainFetcher(currency="ETH", max_workers=5)

# 测试1: 解析工具名称
print("\n1. 测试解析工具名称...")
result = fetcher.parse_instrument_name("ETH-30NOV25-2600-C")
print(f"   ✓ 解析成功: {result.get('currency')}, 行权价={result.get('strike')}, 类型={result.get('option_type')}")

# 测试2: 获取工具列表
print("\n2. 测试获取工具列表...")
instruments = fetcher.get_all_instruments()
print(f"   ✓ 获取到 {len(instruments)} 个工具")

# 测试3: 获取摘要（快速）
print("\n3. 测试获取期权链摘要...")
df_summary = fetcher.get_options_chain_summary()
print(f"   ✓ 获取到 {len(df_summary)} 条摘要数据")
if not df_summary.empty:
    print(f"   列数: {len(df_summary.columns)}")
    if 'expiration_date' in df_summary.columns:
        unique_dates = df_summary['expiration_date'].dropna().nunique()
        print(f"   唯一到期日: {unique_dates} 个")

# 测试4: 批量获取Greeks（小批量）
print("\n4. 测试批量获取Greeks（前3个工具）...")
if instruments:
    test_names = [inst['instrument_name'] for inst in instruments[:3]]
    greeks = fetcher.fetch_greeks_batch(test_names)
    print(f"   ✓ 成功获取 {len(greeks)} 个Greeks数据")
    if greeks:
        df_greeks = pd.DataFrame(greeks)
        print(f"   ✓ 包含列: {', '.join(df_greeks.columns[:8].tolist())}...")

print("\n" + "="*60)
print("测试完成 ✓")
print("="*60)

