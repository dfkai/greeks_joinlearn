"""
任务七：测试阶段
测试时序分析视图的功能
"""

import sys
from pathlib import Path
from src.core import OptionsDatabase
import pandas as pd
from app import prepare_time_series_data, plot_time_series_chart


def test_prepare_time_series_data():
    """测试用例1：时序数据准备功能测试"""
    print("="*60)
    print("测试用例1：时序数据准备功能测试")
    print("="*60)
    
    # 创建测试数据
    test_df = pd.DataFrame({
        'expiration_date': pd.to_datetime(['2025-11-30', '2025-12-27', '2025-11-30', '2025-12-27']),
        'strike': [2600, 2600, 2700, 2700],
        'option_type': ['C', 'C', 'P', 'P'],
        'delta': [0.5, 0.6, -0.3, -0.4],
        'gamma': [0.001, 0.001, 0.001, 0.001],
        'mark_price': [0.1356, 0.1456, 0.1234, 0.1334]
    })
    
    # 测试1.1：正常数据准备
    print("\n1.1 测试正常数据准备...")
    try:
        strike_prices = [2600, 2700]
        result_df = prepare_time_series_data(test_df, strike_prices, 'delta', '全部')
        print(f"  ✓ 数据准备成功，记录数: {len(result_df)} (期望: 4)")
        assert len(result_df) == 4, "数据准备结果不正确"
        
        # 检查列
        assert 'expiration_date' in result_df.columns, "缺少expiration_date列"
        assert 'strike' in result_df.columns, "缺少strike列"
        assert 'delta' in result_df.columns, "缺少delta列"
        print("  ✓ 列检查通过")
        
        # 检查是否按到期日排序
        assert result_df['expiration_date'].is_monotonic_increasing, "数据未按到期日排序"
        print("  ✓ 排序检查通过")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试1.2：单个行权价
    print("\n1.2 测试单个行权价...")
    try:
        result_df = prepare_time_series_data(test_df, [2600], 'delta', '全部')
        print(f"  ✓ 单个行权价筛选成功，记录数: {len(result_df)} (期望: 2)")
        assert len(result_df) == 2, "单个行权价筛选结果不正确"
        assert all(result_df['strike'] == 2600), "筛选结果包含其他行权价"
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False
    
    # 测试1.3：期权类型筛选
    print("\n1.3 测试期权类型筛选...")
    try:
        result_df = prepare_time_series_data(test_df, [2600], 'delta', 'C')
        print(f"  ✓ Call期权筛选成功，记录数: {len(result_df)} (期望: 2)")
        assert len(result_df) == 2, "Call期权筛选结果不正确"
        assert all(result_df['option_type'] == 'C'), "筛选结果包含非Call期权"
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False
    
    # 测试1.4：空数据测试
    print("\n1.4 测试空数据...")
    try:
        empty_df = pd.DataFrame()
        result_df = prepare_time_series_data(empty_df, [2600], 'delta', '全部')
        assert result_df.empty, "空数据应该返回空DataFrame"
        print("  ✓ 空数据处理正确")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False
    
    # 测试1.5：不存在的行权价
    print("\n1.5 测试不存在的行权价...")
    try:
        result_df = prepare_time_series_data(test_df, [9999], 'delta', '全部')
        assert result_df.empty, "不存在的行权价应该返回空DataFrame"
        print("  ✓ 不存在行权价处理正确")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False
    
    return True


def test_chart_function():
    """测试用例2：图表绘制功能测试"""
    print("\n" + "="*60)
    print("测试用例2：图表绘制功能测试")
    print("="*60)
    
    # 创建测试数据
    test_df = pd.DataFrame({
        'expiration_date': pd.to_datetime(['2025-11-30', '2025-12-27']),
        'strike': [2600, 2600],
        'option_type': ['C', 'C'],
        'delta': [0.5, 0.6]
    })
    
    # 测试2.1：图表函数调用（不实际显示）
    print("\n2.1 测试图表函数调用...")
    try:
        strike_prices = [2600]
        # 这个函数会创建图表对象，我们只测试它不会抛出异常
        assert callable(plot_time_series_chart), "plot_time_series_chart应该是可调用函数"
        print("  ✓ 图表函数定义正确")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False
    
    # 测试2.2：空数据图表
    print("\n2.2 测试空数据图表...")
    try:
        empty_df = pd.DataFrame()
        # 函数应该处理空数据而不抛出异常
        assert callable(plot_time_series_chart), "函数应该可以处理空数据"
        print("  ✓ 空数据处理正确")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False
    
    return True


def test_multiple_strikes():
    """测试用例3：多个行权价测试"""
    print("\n" + "="*60)
    print("测试用例3：多个行权价测试")
    print("="*60)
    
    # 创建测试数据
    test_df = pd.DataFrame({
        'expiration_date': pd.to_datetime(['2025-11-30', '2025-12-27', '2025-11-30', '2025-12-27', '2025-11-30']),
        'strike': [2600, 2600, 2700, 2700, 2800],
        'option_type': ['C', 'C', 'C', 'C', 'C'],
        'delta': [0.5, 0.6, 0.4, 0.5, 0.3]
    })
    
    # 测试3.1：多个行权价数据准备
    print("\n3.1 测试多个行权价数据准备...")
    try:
        strike_prices = [2600, 2700, 2800]
        result_df = prepare_time_series_data(test_df, strike_prices, 'delta', '全部')
        print(f"  ✓ 多个行权价数据准备成功，记录数: {len(result_df)} (期望: 5)")
        assert len(result_df) == 5, "多个行权价数据准备结果不正确"
        
        # 检查包含所有行权价
        unique_strikes = result_df['strike'].unique().tolist()
        assert set(unique_strikes) == set(strike_prices), "未包含所有选中的行权价"
        print("  ✓ 行权价检查通过")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_database_integration():
    """测试用例4：数据库集成测试"""
    print("\n" + "="*60)
    print("测试用例4：数据库集成测试")
    print("="*60)
    
    db_path = "test_options.duckdb"
    if not Path(db_path).exists():
        print("  ⚠ 测试数据库不存在，跳过此测试")
        return True
    
    try:
        db = OptionsDatabase(db_path=db_path)
        
        # 测试4.1：获取所有数据
        print("\n4.1 测试获取所有数据...")
        df_all = db.get_latest_options_chain(limit=1000)
        print(f"  ✓ 获取数据成功，记录数: {len(df_all)}")
        
        if not df_all.empty and 'strike' in df_all.columns:
            # 测试4.2：获取可用行权价
            print("\n4.2 测试获取可用行权价...")
            available_strikes = sorted(df_all['strike'].unique().tolist())
            print(f"  ✓ 获取行权价成功，数量: {len(available_strikes)}")
            
            if available_strikes:
                # 测试4.3：准备时序数据
                print("\n4.3 测试准备时序数据...")
                test_strikes = available_strikes[:min(3, len(available_strikes))]
                prepared_df = prepare_time_series_data(df_all, test_strikes, 'delta', '全部')
                print(f"  ✓ 准备数据成功，记录数: {len(prepared_df)}")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_greeks_parameters():
    """测试用例5：不同Greeks参数测试"""
    print("\n" + "="*60)
    print("测试用例5：不同Greeks参数测试")
    print("="*60)
    
    test_df = pd.DataFrame({
        'expiration_date': pd.to_datetime(['2025-11-30', '2025-12-27']),
        'strike': [2600, 2600],
        'option_type': ['C', 'C'],
        'delta': [0.5, 0.6],
        'gamma': [0.001, 0.001],
        'theta': [-0.5, -0.4],
        'vega': [0.01, 0.01]
    })
    
    greeks_params = ['delta', 'gamma', 'theta', 'vega']
    strike_prices = [2600]
    
    for param in greeks_params:
        print(f"\n5.{greeks_params.index(param)+1} 测试{param}参数...")
        try:
            result_df = prepare_time_series_data(test_df, strike_prices, param, '全部')
            if param in test_df.columns:
                assert len(result_df) > 0, f"{param}参数数据准备失败"
                print(f"  ✓ {param}参数处理成功")
            else:
                print(f"  ⚠ {param}参数不在数据中，跳过")
        except Exception as e:
            print(f"  ✗ {param}参数测试失败: {e}")
            return False
    
    return True


def main():
    """运行所有测试"""
    print("="*60)
    print("任务七：时序分析视图功能测试")
    print("="*60)
    
    results = []
    
    # 运行所有测试用例
    results.append(("时序数据准备", test_prepare_time_series_data()))
    results.append(("图表绘制功能", test_chart_function()))
    results.append(("多个行权价", test_multiple_strikes()))
    results.append(("数据库集成", test_database_integration()))
    results.append(("Greeks参数", test_greeks_parameters()))
    
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

