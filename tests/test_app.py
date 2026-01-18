"""
任务五：测试阶段
测试Streamlit应用的功能
"""

import sys
import subprocess
from pathlib import Path
from src.core import OptionsDatabase
import pandas as pd


def test_database_connection():
    """测试用例1：数据库连接测试"""
    print("="*60)
    print("测试用例1：数据库连接测试")
    print("="*60)
    
    # 测试1.1：正常数据库文件连接
    print("\n1.1 测试正常数据库文件连接...")
    db_path = "test_options.duckdb"
    
    # 如果数据库不存在，创建一个测试数据库
    if not Path(db_path).exists():
        print(f"  创建测试数据库: {db_path}")
        db = OptionsDatabase(db_path=db_path)
        # 插入一些测试数据
        test_data = pd.DataFrame({
            'instrument_name': ['ETH-30NOV25-2600-C', 'ETH-30NOV25-2700-P'],
            'currency': ['ETH', 'ETH'],
            'expiration_date': pd.to_datetime(['2025-11-30', '2025-11-30']),
            'strike': [2600, 2700],
            'option_type': ['C', 'P'],
            'mark_price': [0.1356, 0.1234],
            'mark_iv': [103.0, 105.0],
            'underlying_price': [3007.89, 3007.89]
        })
        db.insert_options_chain(test_data)
        db.close()
    
    try:
        db = OptionsDatabase(db_path=db_path)
        stats = db.get_statistics()
        print(f"  ✓ 数据库连接成功")
        print(f"  记录数: {stats.get('options_chain_count', 0)}")
        db.close()
        return True
    except Exception as e:
        print(f"  ✗ 数据库连接失败: {e}")
        return False
    
    # 测试1.2：不存在的数据库文件（在app.py中测试）
    print("\n1.2 不存在的数据库文件测试（需在app中验证）")
    
    # 测试1.3：空数据库
    print("\n1.3 空数据库测试...")
    empty_db_path = "empty_test.duckdb"
    if Path(empty_db_path).exists():
        Path(empty_db_path).unlink()
    
    try:
        db = OptionsDatabase(db_path=empty_db_path)
        stats = db.get_statistics()
        print(f"  ✓ 空数据库连接成功")
        print(f"  记录数: {stats.get('options_chain_count', 0)}")
        db.close()
        Path(empty_db_path).unlink()  # 清理
        return True
    except Exception as e:
        print(f"  ✗ 空数据库连接失败: {e}")
        return False


def test_data_loading():
    """测试用例2：数据加载测试"""
    print("\n" + "="*60)
    print("测试用例2：数据加载测试")
    print("="*60)
    
    db_path = "test_options.duckdb"
    if not Path(db_path).exists():
        print("  ⚠ 测试数据库不存在，跳过此测试")
        return False
    
    try:
        db = OptionsDatabase(db_path=db_path)
        
        # 测试2.1：加载所有数据
        print("\n2.1 测试加载所有数据...")
        df_all = db.get_latest_options_chain(limit=1000)
        print(f"  ✓ 加载成功，记录数: {len(df_all)}")
        
        # 测试2.2：按到期日加载
        print("\n2.2 测试按到期日加载...")
        exp_dates = db.get_all_expiration_dates()
        if exp_dates:
            df_exp = db.get_options_by_expiration(exp_dates[0])
            print(f"  ✓ 加载成功，记录数: {len(df_exp)}")
        
        # 测试2.3：按行权价范围加载
        print("\n2.3 测试按行权价范围加载...")
        df_strike = db.get_options_by_strike_range(2500, 2800)
        print(f"  ✓ 加载成功，记录数: {len(df_strike)}")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ✗ 数据加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_functionality():
    """测试用例3：筛选功能测试"""
    print("\n" + "="*60)
    print("测试用例3：筛选功能测试")
    print("="*60)
    
    # 创建测试数据
    test_df = pd.DataFrame({
        'instrument_name': ['ETH-30NOV25-2600-C', 'ETH-30NOV25-2700-P', 'ETH-27DEC25-2800-C'],
        'expiration_date': pd.to_datetime(['2025-11-30', '2025-11-30', '2025-12-27']),
        'strike': [2600, 2700, 2800],
        'option_type': ['C', 'P', 'C'],
        'mark_price': [0.1356, 0.1234, 0.1456],
        'delta': [0.5, -0.3, 0.6]
    })
    
    # 导入app.py中的筛选函数
    try:
        from app import apply_filters
        
        # 测试3.1：到期日筛选
        print("\n3.1 测试到期日筛选...")
        filters = {'expiration_date': pd.Timestamp('2025-11-30')}
        filtered = apply_filters(test_df, filters)
        print(f"  ✓ 筛选成功，记录数: {len(filtered)} (期望: 2)")
        assert len(filtered) == 2, "到期日筛选结果不正确"
        
        # 测试3.2：行权价范围筛选
        print("\n3.2 测试行权价范围筛选...")
        filters = {'min_strike': 2650, 'max_strike': 2750}
        filtered = apply_filters(test_df, filters)
        print(f"  ✓ 筛选成功，记录数: {len(filtered)} (期望: 1)")
        assert len(filtered) == 1, "行权价范围筛选结果不正确"
        
        # 测试3.3：期权类型筛选
        print("\n3.3 测试期权类型筛选...")
        filters = {'option_type': 'C'}
        filtered = apply_filters(test_df, filters)
        print(f"  ✓ 筛选成功，记录数: {len(filtered)} (期望: 2)")
        assert len(filtered) == 2, "期权类型筛选结果不正确"
        
        # 测试3.4：组合筛选
        print("\n3.4 测试组合筛选...")
        filters = {
            'expiration_date': pd.Timestamp('2025-11-30'),
            'option_type': 'C',
            'min_strike': 2500,
            'max_strike': 2700
        }
        filtered = apply_filters(test_df, filters)
        print(f"  ✓ 筛选成功，记录数: {len(filtered)} (期望: 1)")
        assert len(filtered) == 1, "组合筛选结果不正确"
        
        return True
    except Exception as e:
        print(f"  ✗ 筛选功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics_function():
    """测试用例4：统计信息功能测试"""
    print("\n" + "="*60)
    print("测试用例4：统计信息功能测试")
    print("="*60)
    
    test_df = pd.DataFrame({
        'expiration_date': pd.to_datetime(['2025-11-30', '2025-11-30', '2025-12-27']),
        'strike': [2600, 2700, 2800],
        'option_type': ['C', 'P', 'C']
    })
    
    try:
        from app import get_statistics
        
        stats = get_statistics(test_df)
        print(f"  ✓ 统计信息获取成功")
        print(f"  总记录数: {stats['total_count']} (期望: 3)")
        print(f"  唯一到期日: {stats['unique_expirations']} (期望: 2)")
        print(f"  行权价范围: {stats['strike_range']}")
        print(f"  期权类型: {stats['option_types']}")
        
        assert stats['total_count'] == 3, "总记录数不正确"
        assert stats['unique_expirations'] == 2, "唯一到期日数不正确"
        
        return True
    except Exception as e:
        print(f"  ✗ 统计信息功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("="*60)
    print("任务五：Streamlit应用功能测试")
    print("="*60)
    
    results = []
    
    # 运行所有测试用例
    results.append(("数据库连接", test_database_connection()))
    results.append(("数据加载", test_data_loading()))
    results.append(("筛选功能", test_filter_functionality()))
    results.append(("统计信息", test_statistics_function()))
    
    # 测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())

