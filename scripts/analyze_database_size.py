"""
分析数据库文件大小问题
检查各表的数据量、每条记录大小、存储频率等
"""

import sys
from pathlib import Path
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.monitor_database import MonitorDatabase
import pandas as pd
from datetime import datetime, timedelta


def analyze_database_size():
    """分析数据库大小问题"""
    print("=" * 60)
    print("数据库大小分析")
    print("=" * 60)
    
    db = MonitorDatabase("monitor.duckdb")
    
    with db._get_connection(read_only=True) as conn:
        # 1. 检查各表的记录数
        print("\n1. 各表记录数:")
        print("-" * 60)
        
        tables = ['position_snapshots', 'market_data_log', 'system_events']
        for table in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table}: {count:,} 条")
            except Exception as e:
                print(f"  {table}: 查询失败 - {e}")
        
        # 2. 检查position_snapshots表的详细信息
        print("\n2. position_snapshots表分析:")
        print("-" * 60)
        
        try:
            # 获取最近10条记录
            recent_snapshots = conn.execute("""
                SELECT snapshot_id, timestamp, LENGTH(positions_json) as json_size
                FROM position_snapshots
                ORDER BY timestamp DESC
                LIMIT 10
            """).df()
            
            if not recent_snapshots.empty:
                print(f"  最近10条记录:")
                print(f"  - 平均JSON大小: {recent_snapshots['json_size'].mean():.0f} 字节")
                print(f"  - 最大JSON大小: {recent_snapshots['json_size'].max():.0f} 字节")
                print(f"  - 最小JSON大小: {recent_snapshots['json_size'].min():.0f} 字节")
                
                # 分析一条记录的JSON内容
                sample_json = conn.execute("""
                    SELECT positions_json
                    FROM position_snapshots
                    ORDER BY timestamp DESC
                    LIMIT 1
                """).fetchone()[0]
                
                if sample_json:
                    positions = json.loads(sample_json)
                    print(f"\n  示例记录分析:")
                    print(f"  - 持仓数量: {len(positions)}")
                    print(f"  - JSON大小: {len(sample_json)} 字节")
                    print(f"  - 平均每个持仓: {len(sample_json) / max(len(positions), 1):.0f} 字节")
                    
                    # 显示持仓字段
                    if positions:
                        first_pos = list(positions.values())[0]
                        print(f"  - 持仓字段: {list(first_pos.keys())}")
                        print(f"  - 示例持仓数据: {json.dumps(first_pos, indent=2)}")
            
        except Exception as e:
            print(f"  分析失败: {e}")
        
        # 3. 检查存储频率
        print("\n3. 存储频率分析:")
        print("-" * 60)
        
        try:
            # 获取时间范围
            time_range = conn.execute("""
                SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time, COUNT(*) as count
                FROM position_snapshots
            """).fetchone()
            
            if time_range[0] and time_range[1]:
                min_time = pd.to_datetime(time_range[0])
                max_time = pd.to_datetime(time_range[1])
                count = time_range[2]
                total_days = (max_time - min_time).total_seconds() / 86400
                
                print(f"  时间范围: {min_time} 至 {max_time}")
                print(f"  总天数: {total_days:.1f} 天")
                print(f"  总记录数: {count:,} 条")
                if total_days > 0:
                    print(f"  平均每天: {count / total_days:.1f} 条")
                    print(f"  平均间隔: {86400 / (count / total_days):.1f} 秒/条")
        
        except Exception as e:
            print(f"  分析失败: {e}")
        
        # 4. 检查是否有重复数据
        print("\n4. 数据重复性分析:")
        print("-" * 60)
        
        try:
            # 检查是否有相同时间戳的记录
            duplicate_times = conn.execute("""
                SELECT timestamp, COUNT(*) as count
                FROM position_snapshots
                GROUP BY timestamp
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """).df()
            
            if not duplicate_times.empty:
                print(f"  发现 {len(duplicate_times)} 个重复时间戳")
                print(f"  最多重复次数: {duplicate_times['count'].max()}")
            else:
                print("  未发现重复时间戳")
            
            # 检查是否有相同JSON内容的记录
            # 这个查询可能很慢，只检查最近100条
            recent_jsons = conn.execute("""
                SELECT positions_json, COUNT(*) as count
                FROM (
                    SELECT positions_json
                    FROM position_snapshots
                    ORDER BY timestamp DESC
                    LIMIT 100
                )
                GROUP BY positions_json
                HAVING COUNT(*) > 1
            """).df()
            
            if not recent_jsons.empty:
                print(f"  最近100条中，发现 {len(recent_jsons)} 个重复的JSON内容")
                print(f"  最多重复次数: {recent_jsons['count'].max()}")
            else:
                print("  最近100条中，未发现重复JSON内容")
        
        except Exception as e:
            print(f"  分析失败: {e}")
        
        # 5. 估算数据库大小
        print("\n5. 数据库大小估算:")
        print("-" * 60)
        
        try:
            # 获取各表的总大小（估算）
            total_size = 0
            for table in tables:
                try:
                    # 估算：每条记录的平均大小
                    if table == 'position_snapshots':
                        # 获取平均JSON大小
                        avg_json_size = conn.execute("""
                            SELECT AVG(LENGTH(positions_json)) as avg_size
                            FROM position_snapshots
                        """).fetchone()[0] or 0
                        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        # 估算：固定字段约200字节 + JSON
                        estimated_size = count * (200 + avg_json_size)
                        print(f"  {table}: 约 {estimated_size / 1024 / 1024:.2f} MB ({count:,} 条)")
                        total_size += estimated_size
                    else:
                        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        # 估算：每条记录约500字节
                        estimated_size = count * 500
                        print(f"  {table}: 约 {estimated_size / 1024 / 1024:.2f} MB ({count:,} 条)")
                        total_size += estimated_size
                except Exception as e:
                    print(f"  {table}: 估算失败 - {e}")
            
            print(f"\n  总估算大小: {total_size / 1024 / 1024:.2f} MB")
        
        except Exception as e:
            print(f"  估算失败: {e}")
    
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        analyze_database_size()
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
