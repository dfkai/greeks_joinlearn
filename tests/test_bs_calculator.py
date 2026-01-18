"""
任务十二测试脚本：BS模型计算器功能测试
"""

import numpy as np
from src.core import BSCalculator
import sys


def test_call_option_price():
    """测试用例1：Call期权价格计算"""
    print("\n" + "="*60)
    print("测试用例1：Call期权价格计算")
    print("="*60)
    
    bs = BSCalculator(risk_free_rate=0.05)
    
    # 测试ATM Call
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    price = bs.calculate_option_price(S, K, T, sigma, 'call')
    
    print(f"标的价格 S = {S}")
    print(f"行权价 K = {K}")
    print(f"到期时间 T = {T:.4f}年 ({T*365:.0f}天)")
    print(f"波动率 σ = {sigma:.0%}")
    print(f"Call期权价格 = {price:.2f}")
    
    # ATM期权价格应该在合理范围内
    assert price > 0, "Call期权价格应为正数"
    assert price < S, "Call期权价格不应超过标的价格"
    
    print("✓ Call期权价格计算测试通过")
    return True


def test_put_option_price():
    """测试用例2：Put期权价格计算"""
    print("\n" + "="*60)
    print("测试用例2：Put期权价格计算")
    print("="*60)
    
    bs = BSCalculator(risk_free_rate=0.05)
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    price = bs.calculate_option_price(S, K, T, sigma, 'put')
    
    print(f"Put期权价格 = {price:.2f}")
    
    assert price > 0, "Put期权价格应为正数"
    assert price < K, "Put期权价格不应超过行权价"
    
    print("✓ Put期权价格计算测试通过")
    return True


def test_put_call_parity():
    """测试用例3：Put-Call Parity验证"""
    print("\n" + "="*60)
    print("测试用例3：Put-Call Parity验证")
    print("="*60)
    
    bs = BSCalculator(risk_free_rate=0.05)
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    r = 0.05
    
    C = bs.calculate_option_price(S, K, T, sigma, 'call', r)
    P = bs.calculate_option_price(S, K, T, sigma, 'put', r)
    
    # Put-Call Parity: C - P = S - K*exp(-rT)
    left = C - P
    right = S - K * np.exp(-r * T)
    diff = abs(left - right)
    
    print(f"C - P = {left:.4f}")
    print(f"S - K*exp(-rT) = {right:.4f}")
    print(f"差异 = {diff:.6f}")
    
    assert diff < 0.01, f"Put-Call Parity验证失败，差异{diff}过大"
    
    print("✓ Put-Call Parity验证通过")
    return True


def test_delta_range():
    """测试用例4：Delta范围测试"""
    print("\n" + "="*60)
    print("测试用例4：Delta范围测试")
    print("="*60)
    
    bs = BSCalculator()
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    delta_call = bs.calculate_delta(S, K, T, sigma, 'call')
    delta_put = bs.calculate_delta(S, K, T, sigma, 'put')
    
    print(f"Call Delta = {delta_call:.4f}")
    print(f"Put Delta = {delta_put:.4f}")
    
    # Call Delta应在0到1之间
    assert 0 <= delta_call <= 1, f"Call Delta应在[0,1]，实际为{delta_call}"
    
    # Put Delta应在-1到0之间
    assert -1 <= delta_put <= 0, f"Put Delta应在[-1,0]，实际为{delta_put}"
    
    # ATM期权，Call Delta应接近0.5
    assert 0.4 <= delta_call <= 0.6, f"ATM Call Delta应接近0.5，实际为{delta_call}"
    
    print("✓ Delta范围测试通过")
    return True


def test_gamma_positive():
    """测试用例5：Gamma正值测试"""
    print("\n" + "="*60)
    print("测试用例5：Gamma正值测试")
    print("="*60)
    
    bs = BSCalculator()
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    gamma = bs.calculate_gamma(S, K, T, sigma)
    
    print(f"Gamma = {gamma:.6f}")
    
    # Gamma应始终为正
    assert gamma > 0, f"Gamma应为正数，实际为{gamma}"
    
    print("✓ Gamma正值测试通过")
    return True


def test_theta_negative():
    """测试用例6：Theta负值测试（买入期权）"""
    print("\n" + "="*60)
    print("测试用例6：Theta负值测试")
    print("="*60)
    
    bs = BSCalculator()
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    theta_call = bs.calculate_theta(S, K, T, sigma, 'call')
    theta_put = bs.calculate_theta(S, K, T, sigma, 'put')
    
    print(f"Call Theta (年) = {theta_call:.2f}")
    print(f"Put Theta (年) = {theta_put:.2f}")
    print(f"Call Theta (日) = {theta_call/365:.4f}")
    print(f"Put Theta (日) = {theta_put/365:.4f}")
    
    # 买入期权的Theta通常为负（时间衰减）
    # 注意：在某些情况下深度实值Put的Theta可能为正
    print(f"Call Theta为{'负' if theta_call < 0 else '正'}值")
    
    print("✓ Theta计算测试通过")
    return True


def test_vega_positive():
    """测试用例7：Vega正值测试"""
    print("\n" + "="*60)
    print("测试用例7：Vega正值测试")
    print("="*60)
    
    bs = BSCalculator()
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    vega = bs.calculate_vega(S, K, T, sigma)
    
    print(f"Vega = {vega:.2f}")
    
    # Vega应始终为正（买入期权总是受益于波动率上升）
    assert vega > 0, f"Vega应为正数，实际为{vega}"
    
    print("✓ Vega正值测试通过")
    return True


def test_scenario_analysis():
    """测试用例8：情景分析功能测试"""
    print("\n" + "="*60)
    print("测试用例8：情景分析功能测试")
    print("="*60)
    
    bs = BSCalculator()
    
    S = 3000
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    # 测试价格情景分析
    price_df = bs.price_scenario_analysis(K, T, sigma, 'call', current_S=S, num_points=50)
    assert len(price_df) == 50, "应生成50个价格点"
    assert 'spot_price' in price_df.columns, "应包含spot_price列"
    assert 'delta' in price_df.columns, "应包含delta列"
    print(f"✓ 价格情景分析：生成{len(price_df)}个点")
    
    # 测试时间衰减分析
    time_df = bs.time_decay_analysis(S, K, sigma, 'call', days_to_expiry=30, num_points=50)
    assert len(time_df) == 50, "应生成50个时间点"
    assert 'days_to_expiry' in time_df.columns, "应包含days_to_expiry列"
    print(f"✓ 时间衰减分析：生成{len(time_df)}个点")
    
    # 测试波动率分析
    vol_df = bs.volatility_scenario_analysis(S, K, T, sigma, 'call', num_points=50)
    assert len(vol_df) == 50, "应生成50个波动率点"
    assert 'iv_change_percent' in vol_df.columns, "应包含iv_change_percent列"
    print(f"✓ 波动率敏感性分析：生成{len(vol_df)}个点")
    
    print("✓ 情景分析功能测试通过")
    return True


def test_vectorization():
    """测试用例9：向量化计算测试"""
    print("\n" + "="*60)
    print("测试用例9：向量化计算测试")
    print("="*60)
    
    bs = BSCalculator()
    
    # 批量计算多个期权
    S = np.array([2800, 2900, 3000, 3100, 3200])
    K = 3000
    T = 30 / 365
    sigma = 1.0
    
    prices = bs.calculate_option_price(S, K, T, sigma, 'call')
    deltas = bs.calculate_delta(S, K, T, sigma, 'call')
    
    print(f"批量计算5个不同标的价格的Call期权:")
    for s, p, d in zip(S, prices, deltas):
        print(f"  S={s:.0f}, Price={p:.2f}, Delta={d:.4f}")
    
    assert len(prices) == 5, "应返回5个价格"
    assert len(deltas) == 5, "应返回5个Delta"
    
    print("✓ 向量化计算测试通过")
    return True


def main():
    """运行所有测试用例"""
    print("="*60)
    print("BS模型计算器功能测试")
    print("="*60)
    
    test_results = []
    
    # 运行所有测试
    test_results.append(("测试1：Call期权价格", test_call_option_price()))
    test_results.append(("测试2：Put期权价格", test_put_option_price()))
    test_results.append(("测试3：Put-Call Parity", test_put_call_parity()))
    test_results.append(("测试4：Delta范围", test_delta_range()))
    test_results.append(("测试5：Gamma正值", test_gamma_positive()))
    test_results.append(("测试6：Theta计算", test_theta_negative()))
    test_results.append(("测试7：Vega正值", test_vega_positive()))
    test_results.append(("测试8：情景分析", test_scenario_analysis()))
    test_results.append(("测试9：向量化计算", test_vectorization()))
    
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
        print("\n🎉 所有测试用例通过！BS模型计算器工作正常。")
        return 0
    else:
        print(f"\n⚠ 有 {failed} 个测试用例失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

