"""
回补成交量数据脚本
重新采集数据以更新缺失的成交量信息
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors import DataCollector
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("="*60)
    print("回补成交量数据")
    print("="*60)
    
    collector = DataCollector(currency="ETH", db_path="options_data.duckdb")
    
    try:
        # 1. 检查当前数据质量
        print("\n1. 检查当前数据质量...")
        quality_stats_before = collector.check_data_quality()
        print(f"采集前: 非空={quality_stats_before['non_null_count']} "
              f"({quality_stats_before['completeness_pct']:.2f}%), "
              f"非零={quality_stats_before['non_zero_count']} "
              f"({quality_stats_before['non_zero_pct']:.2f}%)")
        
        # 2. 重新采集摘要数据（包含成交量）
        print("\n2. 重新采集期权链摘要数据（包含成交量）...")
        count = collector.collect_summary_data(replace=True)
        print(f"成功采集 {count} 条数据")
        
        # 3. 检查采集后的数据质量
        print("\n3. 检查采集后的数据质量...")
        quality_stats_after = collector.check_data_quality()
        print(f"采集后: 非空={quality_stats_after['non_null_count']} "
              f"({quality_stats_after['completeness_pct']:.2f}%), "
              f"非零={quality_stats_after['non_zero_count']} "
              f"({quality_stats_after['non_zero_pct']:.2f}%)")
        
        # 4. 对比改进情况
        print("\n4. 数据质量改进情况:")
        print("-" * 60)
        completeness_improvement = quality_stats_after['completeness_pct'] - quality_stats_before['completeness_pct']
        non_zero_improvement = quality_stats_after['non_zero_count'] - quality_stats_before['non_zero_count']
        
        print(f"数据完整性提升: {completeness_improvement:+.2f}%")
        print(f"非零记录增加: {non_zero_improvement:+d}")
        
        if completeness_improvement > 0:
            print("✓ 数据质量已改善")
        else:
            print("⚠ 数据质量未改善，可能需要检查API返回的数据")
        
    finally:
        collector.close()
    
    print("\n" + "="*60)
    print("回补完成")
    print("="*60)

if __name__ == "__main__":
    main()


