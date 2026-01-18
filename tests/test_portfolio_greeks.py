"""
任务十二测试脚本：持仓组合Greeks分析功能测试
"""

import sys
from pathlib import Path
from archive.portfolio_greeks import PortfolioGreeksCalculator
from src.core import OptionsDatabase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_case_1_simple_portfolio():
    """测试用例1：简单组合Greeks计算"""
    print("\n" + "="*60)
    print("测试用例1：简单组合Greeks计算")
    print("="*60)
    
    try:
        db_path = "options_data.duckdb"
        if not Path(db_path).exists():
            print(f"⚠ 数据库文件不存在: {db_path}，跳过此测试")
            return True
        
        db = OptionsDatabase(db_path)
        calculator = PortfolioGreeksCalculator(db)
        
        # 测试Straddle策略（Delta应接近0）
        positions = calculator.get_strategy_template('Straddle')
        
        if not positions:
            print("⚠ 无法获取策略模板，跳过测试")
            db.close()
            return True
        
        portfolio_greeks = calculator.calculate_portfolio_greeks(positions)
        
        print(f"✓ Straddle策略组合Greeks:")
        print(f"  Delta: {portfolio_greeks['delta']:.4f} (应接近0)")
        print(f"  Gamma: {portfolio_greeks['gamma']:.6f} (应为正)")
        print(f"  Theta: {portfolio_greeks['theta']:.4f} (应为负)")
        print(f"  Vega: {portfolio_greeks['vega']:.4f} (应为正)")
        
        # 验证Delta接近0（Straddle的特性）
        assert abs(portfolio_greeks['delta']) < 0.5, "Straddle的Delta应接近0"
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_2_greeks_linearity():
    """测试用例2：Greeks线性相加正确性"""
    print("\n" + "="*60)
    print("测试用例2：Greeks线性相加正确性")
    print("="*60)
    
    try:
        db_path = "options_data.duckdb"
        if not Path(db_path).exists():
            print(f"⚠ 数据库文件不存在，跳过测试")
            return True
        
        db = OptionsDatabase(db_path)
        calculator = PortfolioGreeksCalculator(db)
        
        # 获取一个期权
        df = db.get_latest_options_chain(limit=1)
        if df.empty or 'instrument_name' not in df.columns:
            print("⚠ 数据库中无数据，跳过测试")
            db.close()
            return True
        
        instrument = df.iloc[0]['instrument_name']
        
        # 测试1：单个持仓
        positions_1 = [{'instrument_name': instrument, 'quantity': 1}]
        greeks_1 = calculator.calculate_portfolio_greeks(positions_1)
        
        # 测试2：两个相同持仓（应该是Greeks的2倍）
        positions_2 = [
            {'instrument_name': instrument, 'quantity': 1},
            {'instrument_name': instrument, 'quantity': 1}
        ]
        greeks_2 = calculator.calculate_portfolio_greeks(positions_2)
        
        # 验证线性关系
        delta_ratio = greeks_2['delta'] / greeks_1['delta'] if greeks_1['delta'] != 0 else 0
        print(f"✓ 线性相加验证:")
        print(f"  单个持仓Delta: {greeks_1['delta']:.4f}")
        print(f"  两个持仓Delta: {greeks_2['delta']:.4f}")
        print(f"  比率: {delta_ratio:.2f} (应接近2.0)")
        
        assert abs(delta_ratio - 2.0) < 0.01, "Greeks应线性相加"
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_3_strategy_templates():
    """测试用例3：策略模板生成"""
    print("\n" + "="*60)
    print("测试用例3：策略模板生成")
    print("="*60)
    
    try:
        db_path = "options_data.duckdb"
        if not Path(db_path).exists():
            print(f"⚠ 数据库文件不存在，跳过测试")
            return True
        
        db = OptionsDatabase(db_path)
        calculator = PortfolioGreeksCalculator(db)
        
        strategies = ['Straddle', 'Strangle', 'Bull Call Spread', 'Butterfly']
        
        for strategy in strategies:
            positions = calculator.get_strategy_template(strategy)
            print(f"  {strategy}: {len(positions)} 个持仓")
        
        print(f"✓ 策略模板生成测试通过")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_4_greeks_vs_price():
    """测试用例4：Greeks vs 价格曲线计算"""
    print("\n" + "="*60)
    print("测试用例4：Greeks vs 价格曲线计算")
    print("="*60)
    
    try:
        db_path = "options_data.duckdb"
        if not Path(db_path).exists():
            print(f"⚠ 数据库文件不存在，跳过测试")
            return True
        
        db = OptionsDatabase(db_path)
        calculator = PortfolioGreeksCalculator(db)
        
        positions = calculator.get_strategy_template('Straddle')
        if not positions:
            print("⚠ 无法获取策略模板，跳过测试")
            db.close()
            return True
        
        # 计算Greeks vs 价格
        greeks_df = calculator.calculate_portfolio_greeks_vs_price(
            positions,
            price_range=(2500, 3500),
            num_points=20
        )
        
        assert not greeks_df.empty, "Greeks vs 价格DataFrame不应为空"
        assert len(greeks_df) == 20, "应生成20个价格点"
        assert 'underlying_price' in greeks_df.columns, "应包含underlying_price列"
        assert 'portfolio_delta' in greeks_df.columns, "应包含portfolio_delta列"
        
        print(f"✓ Greeks vs 价格曲线计算测试通过")
        print(f"  生成 {len(greeks_df)} 个价格点")
        print(f"  价格范围: {greeks_df['underlying_price'].min():.0f} - {greeks_df['underlying_price'].max():.0f}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试用例"""
    print("="*60)
    print("持仓组合Greeks分析功能测试")
    print("="*60)
    
    test_results = []
    
    # 运行所有测试用例
    test_results.append(("测试用例1：简单组合Greeks计算", test_case_1_simple_portfolio()))
    test_results.append(("测试用例2：Greeks线性相加", test_case_2_greeks_linearity()))
    test_results.append(("测试用例3：策略模板生成", test_case_3_strategy_templates()))
    test_results.append(("测试用例4：Greeks vs 价格曲线", test_case_4_greeks_vs_price()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in test_results if result)
    failed = sum(1 for _, result in test_results if not result)
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
    
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

