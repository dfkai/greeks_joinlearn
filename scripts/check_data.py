"""
诊断脚本：检查时序分析数据完整性
检查数据库中是否存在所有到期日、所有行权价的Greeks值
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.core import OptionsDatabase

def check_time_series_data_completeness():
    """检查时序分析数据的完整性"""
    db = OptionsDatabase("options_data.duckdb")
    
    # 获取所有数据
    df_all = db.get_all_options_chain()
    
    if df_all.empty:
        print("数据库为空！")
        return
    
    print("=" * 80)
    print("数据完整性检查报告")
    print("=" * 80)
    
    # 基本信息
    print(f"\n总记录数: {len(df_all)}")
    print(f"唯一到期日数: {df_all['expiration_date'].nunique()}")
    print(f"唯一行权价数: {df_all['strike'].nunique()}")
    
    # 检查到期日范围
    if 'expiration_date' in df_all.columns:
        df_all['expiration_date'] = pd.to_datetime(df_all['expiration_date'])
        unique_dates = sorted(df_all['expiration_date'].dt.date.unique())
        print(f"\n到期日范围: {unique_dates[0]} 到 {unique_dates[-1]}")
        print(f"所有到期日: {unique_dates}")
    
    # 检查Greeks列的缺失情况
    greeks_cols = ['delta', 'gamma', 'theta', 'vega', 'rho']
    print("\n" + "=" * 80)
    print("Greeks值缺失情况统计")
    print("=" * 80)
    
    for col in greeks_cols:
        if col in df_all.columns:
            total = len(df_all)
            missing = df_all[col].isna().sum()
            missing_pct = (missing / total * 100) if total > 0 else 0
            print(f"{col:10s}: 缺失 {missing:6d} / {total:6d} ({missing_pct:5.2f}%)")
    
    # 按到期日和行权价分组，检查每个组合的Greeks值完整性
    print("\n" + "=" * 80)
    print("按到期日+行权价+期权类型分组的数据完整性")
    print("=" * 80)
    
    # 选择几个示例行权价进行检查
    sample_strikes = sorted(df_all['strike'].unique())[:5]  # 前5个行权价
    print(f"\n检查示例行权价: {sample_strikes}")
    
    for strike in sample_strikes:
        strike_df = df_all[df_all['strike'] == strike].copy()
        if strike_df.empty:
            continue
            
        print(f"\n行权价 {strike:.0f}:")
        print(f"  总记录数: {len(strike_df)}")
        
        # 按到期日分组
        for exp_date in sorted(strike_df['expiration_date'].dt.date.unique()):
            exp_df = strike_df[strike_df['expiration_date'].dt.date == exp_date]
            
            # 检查Call和Put
            for opt_type in ['C', 'P']:
                opt_df = exp_df[exp_df['option_type'] == opt_type]
                if not opt_df.empty:
                    greeks_status = []
                    for greek in greeks_cols:
                        if greek in opt_df.columns:
                            has_value = not opt_df[greek].isna().all()
                            greeks_status.append(f"{greek}:{'✓' if has_value else '✗'}")
                    
                    print(f"    {exp_date} {opt_type}: {', '.join(greeks_status)}")
    
    # 检查特定问题：某个到期日是否有某个行权价的数据
    print("\n" + "=" * 80)
    print("检查：每个到期日是否都有所有行权价的数据")
    print("=" * 80)
    
    all_strikes = sorted(df_all['strike'].unique())
    all_exp_dates = sorted(df_all['expiration_date'].dt.date.unique())
    
    print(f"\n总行权价数: {len(all_strikes)}")
    print(f"总到期日数: {len(all_exp_dates)}")
    print(f"理论上应该有 {len(all_strikes) * len(all_exp_dates) * 2} 条记录 (每个到期日*每个行权价*Call+Put)")
    
    # 检查每个到期日的数据覆盖情况
    for exp_date in all_exp_dates:
        exp_df = df_all[df_all['expiration_date'].dt.date == exp_date]
        exp_strikes = sorted(exp_df['strike'].unique())
        missing_strikes = set(all_strikes) - set(exp_strikes)
        
        if missing_strikes:
            print(f"\n{exp_date}: 缺少行权价 {sorted(missing_strikes)[:10]}...")  # 只显示前10个
        else:
            print(f"\n{exp_date}: ✓ 包含所有行权价")
    
    # 检查Greeks值：某个到期日+行权价组合是否有Greeks值
    print("\n" + "=" * 80)
    print("检查：特定到期日+行权价组合的Greeks值存在情况")
    print("=" * 80)
    
    # 选择一个示例行权价
    test_strike = all_strikes[len(all_strikes)//2] if all_strikes else None
    if test_strike:
        print(f"\n检查行权价 {test_strike:.0f} 在所有到期日的Greeks值:")
        strike_df = df_all[df_all['strike'] == test_strike]
        
        for exp_date in all_exp_dates:
            exp_df = strike_df[strike_df['expiration_date'].dt.date == exp_date]
            if not exp_df.empty:
                for opt_type in ['C', 'P']:
                    opt_df = exp_df[exp_df['option_type'] == opt_type]
                    if not opt_df.empty:
                        greeks_vals = {}
                        for greek in greeks_cols:
                            if greek in opt_df.columns:
                                val = opt_df[greek].iloc[0] if len(opt_df) > 0 else None
                                greeks_vals[greek] = val if pd.notna(val) else None
                        
                        has_all = all(v is not None for v in greeks_vals.values())
                        status = "✓" if has_all else "✗"
                        print(f"  {exp_date} {opt_type}: {status} {greeks_vals}")
            else:
                print(f"  {exp_date}: ✗ 无数据")
    
    db.close()
    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)

if __name__ == "__main__":
    check_time_series_data_completeness()

