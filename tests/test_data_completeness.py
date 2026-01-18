"""
任务八测试脚本：数据完整性检查功能测试
"""

import sys
from pathlib import Path
from src.collectors import DataCompletenessChecker
from src.core import OptionsDatabase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_case_1_get_api_instruments():
    """测试用例1：测试获取Deribit API所有ETH期权列表"""
    print("\n" + "="*60)
    print("测试用例1：获取Deribit API所有ETH期权列表")
    print("="*60)
    
    try:
        checker = DataCompletenessChecker(currency="ETH")
        api_instruments = checker.get_api_instruments()
        
        assert api_instruments is not None, "API工具列表不应为None"
        assert isinstance(api_instruments, list), "API工具列表应为列表类型"
        assert len(api_instruments) > 0, "应该获取到至少一个期权工具"
        
        print(f"✓ 成功获取 {len(api_instruments)} 个ETH期权工具")
        if api_instruments:
            print(f"  示例工具: {api_instruments[0].get('instrument_name', 'N/A')}")
        
        checker.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_2_get_stored_instruments():
    """测试用例2：测试从数据库查询已存储期权列表"""
    print("\n" + "="*60)
    print("测试用例2：从数据库查询已存储期权列表")
    print("="*60)
    
    try:
        db_path = "options_data.duckdb"
        if not Path(db_path).exists():
            print(f"⚠ 数据库文件不存在: {db_path}，跳过此测试")
            return True
        
        checker = DataCompletenessChecker(currency="ETH", db_path=db_path)
        stored_instruments = checker.get_stored_instruments()
        
        assert stored_instruments is not None, "数据库工具列表不应为None"
        assert isinstance(stored_instruments, list), "数据库工具列表应为列表类型"
        
        print(f"✓ 成功查询到 {len(stored_instruments)} 个已存储的期权工具")
        if stored_instruments:
            print(f"  示例工具: {stored_instruments[0]}")
        
        checker.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_3_compare_logic():
    """测试用例3：测试对比逻辑正确性（模拟部分缺失场景）"""
    print("\n" + "="*60)
    print("测试用例3：测试对比逻辑正确性")
    print("="*60)
    
    try:
        # 模拟API数据
        api_instruments = [
            {'instrument_name': 'ETH-30NOV25-2600-C'},
            {'instrument_name': 'ETH-30NOV25-2600-P'},
            {'instrument_name': 'ETH-30NOV25-2700-C'},
            {'instrument_name': 'ETH-30NOV25-2700-P'},
        ]
        
        # 模拟数据库数据（缺失2个）
        stored_instruments = [
            'ETH-30NOV25-2600-C',
            'ETH-30NOV25-2700-C',
        ]
        
        checker = DataCompletenessChecker(currency="ETH")
        result = checker.compare_instruments(api_instruments, stored_instruments)
        
        assert result['api_total'] == 4, f"API总数应为4，实际为{result['api_total']}"
        assert result['stored_total'] == 2, f"已存储数应为2，实际为{result['stored_total']}"
        assert result['missing_count'] == 2, f"缺失数应为2，实际为{result['missing_count']}"
        assert result['coverage_rate'] == 50.0, f"覆盖率应为50%，实际为{result['coverage_rate']}%"
        
        print(f"✓ 对比逻辑测试通过")
        print(f"  API总数: {result['api_total']}")
        print(f"  已存储: {result['stored_total']}")
        print(f"  缺失: {result['missing_count']}")
        print(f"  覆盖率: {result['coverage_rate']}%")
        
        checker.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_4_report_generation():
    """测试用例4：测试报告生成功能"""
    print("\n" + "="*60)
    print("测试用例4：测试报告生成功能")
    print("="*60)
    
    try:
        checker = DataCompletenessChecker(currency="ETH")
        
        # 模拟对比结果
        comparison_result = {
            'api_total': 100,
            'stored_total': 95,
            'missing_count': 5,
            'missing_names': ['ETH-30NOV25-2600-C', 'ETH-30NOV25-2600-P', 
                            'ETH-30NOV25-2700-C', 'ETH-30NOV25-2700-P', 
                            'ETH-30NOV25-2800-C'],
            'expired_count': 2,
            'expired_names': ['ETH-01JAN24-2000-C', 'ETH-01JAN24-2000-P'],
            'coverage_rate': 95.0,
            'api_instruments_dict': {}
        }
        
        # 模拟维度分析
        dimension_analysis = {
            'by_expiration': {'2025-11-30': 5},
            'by_strike_range': {'2000-3000': 5},
            'by_option_type': {'call': 3, 'put': 2},
            'by_currency': {'ETH': 5}
        }
        
        report = checker.generate_report(comparison_result, dimension_analysis)
        
        assert 'check_time' in report, "报告应包含检查时间"
        assert 'summary' in report, "报告应包含摘要"
        assert 'missing_instruments' in report, "报告应包含缺失列表"
        assert 'dimension_analysis' in report, "报告应包含维度分析"
        
        print(f"✓ 报告生成测试通过")
        print(f"  检查时间: {report['check_time']}")
        print(f"  摘要: {report['summary']}")
        print(f"  缺失数量: {len(report['missing_instruments'])}")
        
        checker.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_5_edge_cases():
    """测试用例5：测试边界情况"""
    print("\n" + "="*60)
    print("测试用例5：测试边界情况")
    print("="*60)
    
    try:
        checker = DataCompletenessChecker(currency="ETH")
        
        # 测试1：空API列表
        result1 = checker.compare_instruments([], [])
        assert result1['api_total'] == 0, "空API列表应返回0"
        assert result1['coverage_rate'] == 0, "空API列表覆盖率应为0"
        print("✓ 空API列表测试通过")
        
        # 测试2：空数据库列表
        api_instruments = [{'instrument_name': 'ETH-30NOV25-2600-C'}]
        result2 = checker.compare_instruments(api_instruments, [])
        assert result2['missing_count'] == 1, "空数据库应显示所有API工具为缺失"
        print("✓ 空数据库列表测试通过")
        
        # 测试3：完全匹配
        result3 = checker.compare_instruments(api_instruments, ['ETH-30NOV25-2600-C'])
        assert result3['missing_count'] == 0, "完全匹配应无缺失"
        assert result3['coverage_rate'] == 100.0, "完全匹配覆盖率应为100%"
        print("✓ 完全匹配测试通过")
        
        checker.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_6_full_check():
    """测试用例6：完整检查流程（如果数据库存在）"""
    print("\n" + "="*60)
    print("测试用例6：完整检查流程")
    print("="*60)
    
    try:
        db_path = "options_data.duckdb"
        if not Path(db_path).exists():
            print(f"⚠ 数据库文件不存在: {db_path}，跳过完整检查测试")
            return True
        
        checker = DataCompletenessChecker(currency="ETH", db_path=db_path)
        report = checker.check_completeness()
        
        assert 'error' not in report, f"检查不应返回错误: {report.get('error')}"
        assert 'summary' in report, "报告应包含摘要"
        
        summary = report['summary']
        print(f"✓ 完整检查测试通过")
        print(f"  API总数: {summary.get('api_total', 0)}")
        print(f"  已存储: {summary.get('stored_total', 0)}")
        print(f"  缺失: {summary.get('missing_count', 0)}")
        print(f"  覆盖率: {summary.get('coverage_rate', 0)}%")
        
        checker.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试用例"""
    print("="*60)
    print("数据完整性检查功能测试")
    print("="*60)
    
    test_results = []
    
    # 运行所有测试用例
    test_results.append(("测试用例1：获取API工具列表", test_case_1_get_api_instruments()))
    test_results.append(("测试用例2：查询数据库工具列表", test_case_2_get_stored_instruments()))
    test_results.append(("测试用例3：对比逻辑", test_case_3_compare_logic()))
    test_results.append(("测试用例4：报告生成", test_case_4_report_generation()))
    test_results.append(("测试用例5：边界情况", test_case_5_edge_cases()))
    test_results.append(("测试用例6：完整检查流程", test_case_6_full_check()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(test_results)} 个测试用例")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    
    if failed == 0:
        print("\n🎉 所有测试用例通过！")
        return 0
    else:
        print(f"\n⚠ 有 {failed} 个测试用例失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

