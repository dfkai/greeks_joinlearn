"""采集Greeks数据脚本"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors import DataCollector
import time

print("="*60)
print("开始采集Greeks数据")
print("="*60)

collector = DataCollector(currency='ETH', db_path='options_data.duckdb', max_workers=10)

try:
    print("\n开始采集Greeks数据（前200个期权）...")
    start = time.time()
    
    count = collector.collect_greeks_data(limit=200, replace=True)
    
    elapsed = time.time() - start
    
    print(f"\n采集完成！")
    print(f"  成功采集: {count} 条Greeks数据")
    print(f"  耗时: {elapsed:.1f}秒")
    
    # 显示统计信息
    stats = collector.db.get_statistics()
    print(f"\n数据库统计:")
    print(f"  期权链记录数: {stats.get('options_chain_count', 0)}")
    print(f"  Greeks记录数: {stats.get('greeks_count', 0)}")
    print(f"  唯一到期日: {stats.get('unique_expiration_dates', 0)}")
    
finally:
    collector.close()

print("\n完成！现在可以在Streamlit应用中查看Greeks数据了。")

