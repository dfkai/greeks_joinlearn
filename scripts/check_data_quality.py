"""
数据质量检查脚本
检查成交量数据的完整性和质量
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors import DataCollector
import pandas as pd

def main():
    print("="*60)
    print("数据质量检查")
    print("="*60)
    
    collector = DataCollector(currency="ETH", db_path="options_data.duckdb")
    
    try:
        # 1. 检查成交量数据质量
        print("\n1. 成交量数据质量统计:")
        print("-" * 60)
        quality_stats = collector.check_data_quality()
        
        print(f"总记录数: {quality_stats['total_count']}")
        print(f"非空记录数: {quality_stats['non_null_count']} ({quality_stats['completeness_pct']:.2f}%)")
        print(f"非零记录数: {quality_stats['non_zero_count']} ({quality_stats['non_zero_pct']:.2f}%)")
        print(f"空值记录数: {quality_stats['null_count']}")
        print(f"零值记录数: {quality_stats['zero_count']}")
        print(f"总成交量: {quality_stats['total_volume']:.2f}")
        print(f"平均成交量: {quality_stats['avg_volume']:.2f}")
        print(f"最大成交量: {quality_stats['max_volume']:.2f}")
        
        # 2. 获取缺失成交量数据的期权列表
        print("\n2. 缺失成交量数据的期权列表:")
        print("-" * 60)
        missing_df = collector.get_missing_volume_data()
        
        if not missing_df.empty:
            print(f"找到 {len(missing_df)} 个缺失成交量数据的期权")
            print("\n前10条记录:")
            print(missing_df.head(10).to_string())
            
            # 按到期日统计
            if 'expiration_date' in missing_df.columns:
                print("\n按到期日统计缺失数据:")
                exp_stats = missing_df.groupby('expiration_date').size().sort_values(ascending=False)
                print(exp_stats.head(10).to_string())
        else:
            print("✓ 所有期权都有成交量数据（可能为零，但非空）")
        
        # 3. 数据质量评估
        print("\n3. 数据质量评估:")
        print("-" * 60)
        if quality_stats['completeness_pct'] >= 90:
            print("✓ 数据质量优秀：成交量数据完整性 >= 90%")
        elif quality_stats['completeness_pct'] >= 50:
            print("⚠ 数据质量一般：成交量数据完整性 >= 50%")
        else:
            print("✗ 数据质量较差：成交量数据完整性 < 50%")
            print("  建议重新采集数据")
        
        if quality_stats['non_zero_pct'] > 0:
            print(f"✓ 有 {quality_stats['non_zero_count']} 个期权存在实际成交量")
        else:
            print("⚠ 所有期权的成交量都为零（可能是市场不活跃）")
        
    finally:
        collector.close()
    
    print("\n" + "="*60)
    print("检查完成")
    print("="*60)

if __name__ == "__main__":
    main()


