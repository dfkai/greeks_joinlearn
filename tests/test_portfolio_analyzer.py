"""
任务十三测试脚本：持仓组合Greeks分析功能测试
"""

from src.core import PortfolioAnalyzer
import sys


def test_single_position():
    """测试用例1：单个持仓Greeks计算"""
    print("\n" + "="*60)
    print("测试用例1：单个持仓Greeks计算")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    
    # 添加单个Call持仓
    analyzer.add_position('2025-12-30', 3000, 'C', 1, volatility=1.0)
    
    greeks = analyzer.calculate_portfolio_greeks()
    
    print(f"单个ATM Call持仓Greeks:")
    print(f"  Delta: {greeks['delta']:.4f} (应接近0.5)")
    print(f"  Gamma: {greeks['gamma']:.6f} (应为正)")
    print(f"  Theta: {greeks['theta_daily']:.4f} (应为负)")
    print(f"  Vega: {greeks['vega']:.2f} (应为正)")
    
    assert 0.4 <= greeks['delta'] <= 0.6, "ATM Call Delta应接近0.5"
    assert greeks['gamma'] > 0, "Gamma应为正"
    assert greeks['vega'] > 0, "Vega应为正"
    
    print("✓ 单个持仓测试通过")
    return True


def test_long_straddle():
    """测试用例2：Long Straddle策略"""
    print("\n" + "="*60)
    print("测试用例2：Long Straddle策略")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    
    # 加载Long Straddle模板
    analyzer.load_strategy_template('long_straddle', 3000)
    
    positions_df = analyzer.get_positions_df()
    print(f"持仓数量: {len(positions_df)}")
    print(positions_df)
    
    greeks = analyzer.calculate_portfolio_greeks()
    
    print(f"\nLong Straddle组合Greeks:")
    print(f"  Delta: {greeks['delta']:.4f} (应接近0)")
    print(f"  Gamma: {greeks['gamma']:.6f} (应为正)")
    print(f"  Theta: {greeks['theta_daily']:.4f} (应为负)")
    print(f"  Vega: {greeks['vega']:.2f} (应为正)")
    
    assert len(positions_df) == 2, "Long Straddle应有2个持仓"
    assert abs(greeks['delta']) < 0.1, "Long Straddle Delta应接近0"
    assert greeks['gamma'] > 0, "Long Straddle Gamma应为正"
    assert greeks['theta_daily'] < 0, "Long Straddle Theta应为负"
    assert greeks['vega'] > 0, "Long Straddle Vega应为正"
    
    print("✓ Long Straddle测试通过")
    return True


def test_short_strangle():
    """测试用例3：Short Strangle策略"""
    print("\n" + "="*60)
    print("测试用例3：Short Strangle策略")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    
    analyzer.load_strategy_template('short_strangle', 3000)
    
    greeks = analyzer.calculate_portfolio_greeks()
    
    print(f"Short Strangle组合Greeks:")
    print(f"  Delta: {greeks['delta']:.4f} (应接近0)")
    print(f"  Gamma: {greeks['gamma']:.6f} (应为负)")
    print(f"  Theta: {greeks['theta_daily']:.4f} (应为正)")
    print(f"  Vega: {greeks['vega']:.2f} (应为负)")
    
    assert abs(greeks['delta']) < 0.1, "Short Strangle Delta应接近0"
    assert greeks['gamma'] < 0, "Short Strangle Gamma应为负"
    assert greeks['theta_daily'] > 0, "Short Strangle Theta应为正"
    assert greeks['vega'] < 0, "Short Strangle Vega应为负"
    
    print("✓ Short Strangle测试通过")
    return True


def test_greeks_additivity():
    """测试用例4：Greeks线性相加验证"""
    print("\n" + "="*60)
    print("测试用例4：Greeks线性相加验证")
    print("="*60)
    
    analyzer1 = PortfolioAnalyzer()
    analyzer1.current_spot_price = 3000
    analyzer1.add_position('2025-12-30', 3000, 'C', 1, volatility=1.0)
    greeks1 = analyzer1.calculate_portfolio_greeks()
    
    analyzer2 = PortfolioAnalyzer()
    analyzer2.current_spot_price = 3000
    analyzer2.add_position('2025-12-30', 3200, 'P', 1, volatility=1.0)
    greeks2 = analyzer2.calculate_portfolio_greeks()
    
    # 组合两个持仓
    analyzer3 = PortfolioAnalyzer()
    analyzer3.current_spot_price = 3000
    analyzer3.add_position('2025-12-30', 3000, 'C', 1, volatility=1.0)
    analyzer3.add_position('2025-12-30', 3200, 'P', 1, volatility=1.0)
    greeks3 = analyzer3.calculate_portfolio_greeks()
    
    # 验证线性相加
    delta_sum = greeks1['delta'] + greeks2['delta']
    gamma_sum = greeks1['gamma'] + greeks2['gamma']
    
    print(f"持仓1 Delta: {greeks1['delta']:.4f}")
    print(f"持仓2 Delta: {greeks2['delta']:.4f}")
    print(f"预期组合 Delta: {delta_sum:.4f}")
    print(f"实际组合 Delta: {greeks3['delta']:.4f}")
    print(f"差异: {abs(delta_sum - greeks3['delta']):.6f}")
    
    assert abs(delta_sum - greeks3['delta']) < 1e-6, "Delta线性相加验证失败"
    assert abs(gamma_sum - greeks3['gamma']) < 1e-6, "Gamma线性相加验证失败"
    
    print("✓ Greeks线性相加验证通过")
    return True


def test_price_scenario():
    """测试用例5：价格情景分析"""
    print("\n" + "="*60)
    print("测试用例5：价格情景分析")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    analyzer.load_strategy_template('long_straddle', 3000)
    
    price_df = analyzer.greeks_vs_spot_price(2500, 3500, num_points=50)
    
    print(f"生成价格点数: {len(price_df)}")
    print(f"价格范围: {price_df['spot_price'].min():.0f} - {price_df['spot_price'].max():.0f}")
    
    assert len(price_df) == 50, "应生成50个价格点"
    assert 'delta' in price_df.columns, "应包含delta列"
    assert 'gamma' in price_df.columns, "应包含gamma列"
    
    print("✓ 价格情景分析测试通过")
    return True


def test_pnl_calculation():
    """测试用例6：PnL计算"""
    print("\n" + "="*60)
    print("测试用例6：PnL计算")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    analyzer.add_position('2025-12-30', 3000, 'C', 1, volatility=1.0)
    
    pnl_df = analyzer.pnl_vs_spot_price(2800, 3200, num_points=20)
    
    print(f"初始价值: ${pnl_df['initial_value'].iloc[0]:.2f}")
    print(f"最大损失: ${pnl_df['pnl'].min():.2f}")
    print(f"最大收益: ${pnl_df['pnl'].max():.2f}")
    
    assert 'pnl' in pnl_df.columns, "应包含pnl列"
    assert 'initial_value' in pnl_df.columns, "应包含initial_value列"
    
    print("✓ PnL计算测试通过")
    return True


def test_time_decay():
    """测试用例7：时间衰减分析"""
    print("\n" + "="*60)
    print("测试用例7：时间衰减分析")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    analyzer.load_strategy_template('long_straddle', 3000)
    
    time_df = analyzer.time_decay_analysis(num_points=30)
    
    print(f"生成时间点数: {len(time_df)}")
    print(f"天数范围: {time_df['days_to_expiry'].max():.0f} - {time_df['days_to_expiry'].min():.0f}")
    
    # Long Straddle的价值应该随时间减少（Theta为负）
    first_value = time_df['position_value'].iloc[0]
    last_value = time_df['position_value'].iloc[-1]
    print(f"初始价值: ${first_value:.2f}")
    print(f"到期价值: ${last_value:.2f}")
    print(f"时间衰减: ${first_value - last_value:.2f}")
    
    assert len(time_df) == 30, "应生成30个时间点"
    assert first_value > last_value, "Long Straddle价值应随时间减少"
    
    print("✓ 时间衰减分析测试通过")
    return True


def test_volatility_sensitivity():
    """测试用例8：波动率敏感性分析"""
    print("\n" + "="*60)
    print("测试用例8：波动率敏感性分析")
    print("="*60)
    
    analyzer = PortfolioAnalyzer()
    analyzer.current_spot_price = 3000
    analyzer.load_strategy_template('long_straddle', 3000)
    
    vol_df = analyzer.volatility_sensitivity_analysis((-0.5, 0.5), num_points=30)
    
    print(f"生成波动率点数: {len(vol_df)}")
    print(f"IV变化范围: {vol_df['iv_change_percent'].min():.0f}% - {vol_df['iv_change_percent'].max():.0f}%")
    
    # Long Straddle的价值应该随波动率上升而增加（Vega为正）
    first_value = vol_df['position_value'].iloc[0]  # 低IV
    last_value = vol_df['position_value'].iloc[-1]  # 高IV
    print(f"低IV价值: ${first_value:.2f}")
    print(f"高IV价值: ${last_value:.2f}")
    print(f"IV效应: ${last_value - first_value:.2f}")
    
    assert len(vol_df) == 30, "应生成30个波动率点"
    assert last_value > first_value, "Long Straddle价值应随IV增加而上升"
    
    print("✓ 波动率敏感性分析测试通过")
    return True


def main():
    """运行所有测试"""
    print("="*60)
    print("持仓组合Greeks分析功能测试")
    print("="*60)
    
    test_results = []
    
    test_results.append(("测试1：单个持仓", test_single_position()))
    test_results.append(("测试2：Long Straddle", test_long_straddle()))
    test_results.append(("测试3：Short Strangle", test_short_strangle()))
    test_results.append(("测试4：Greeks线性相加", test_greeks_additivity()))
    test_results.append(("测试5：价格情景分析", test_price_scenario()))
    test_results.append(("测试6：PnL计算", test_pnl_calculation()))
    test_results.append(("测试7：时间衰减", test_time_decay()))
    test_results.append(("测试8：波动率敏感性", test_volatility_sensitivity()))
    
    # 汇总
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
        print("\n🎉 所有测试用例通过！持仓组合分析器工作正常。")
        return 0
    else:
        print(f"\n⚠ 有 {failed} 个测试用例失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

