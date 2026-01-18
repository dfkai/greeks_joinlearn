"""
手动获取持仓并保存到数据库（用于测试）
"""

import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.Deribit_HTTP import DeribitAPI
from credentials import client_id, client_secret
from src.core.monitor_database import MonitorDatabase

print("=" * 60)
print("手动获取持仓并保存")
print("=" * 60)
print()

# 1. 获取持仓
print("步骤 1: 获取持仓...")
api = DeribitAPI(client_id, client_secret)

if not api.access_token:
    print("❌ API认证失败")
    sys.exit(1)

print("✅ API认证成功")
print()

all_positions = {}

for currency in ["ETH", "BTC"]:
    for kind in ["option", "future"]:
        print(f"获取 {currency} {kind}...")
        result = api.get_all_positions(currency=currency, kind=kind)
        
        if result and 'result' in result:
            positions = result['result']
            for pos in positions:
                size = pos.get('size', 0)
                if size != 0:
                    instrument = pos.get('instrument_name', '')
                    
                    # 对于期货，计算Value in ETH（用于Delta）
                    if kind == 'future':
                        mark_price = pos.get('mark_price', 0)
                        # 尝试获取value字段（ETH单位），如果没有则计算
                        value_eth = pos.get('value', None)
                        if value_eth is None and mark_price > 0:
                            # Value (ETH) = Size (USD) / Mark Price (ETH)
                            value_eth = size / mark_price if mark_price > 0 else 0
                        delta = value_eth if value_eth is not None else 0.0
                    else:
                        # 期权使用API提供的delta
                        delta = pos.get('delta', 0)
                        value_eth = None
                    
                    all_positions[instrument] = {
                        'asset_type': 'option' if kind == 'option' else ('perpetual' if 'PERPETUAL' in instrument.upper() else 'future'),
                        'size': size,  # 美元单位的持仓数量
                        'value_eth': value_eth,  # ETH单位的持仓价值（期货用）
                        'average_price': pos.get('average_price', 0),
                        'mark_price': pos.get('mark_price', 0),
                        'mark_iv': pos.get('mark_iv', 0) if kind == 'option' else None,
                        'delta': delta,  # 期权：API提供的delta；期货：Value in ETH
                        'gamma': pos.get('gamma', 0) if kind == 'option' else 0.0,
                        'theta': pos.get('theta', 0) if kind == 'option' else 0.0,
                        'vega': pos.get('vega', 0) if kind == 'option' else 0.0,
                    }
                    print(f"  ✅ {instrument}: size={size}, value_eth={value_eth}, delta={delta}")

print()
print(f"共获取 {len(all_positions)} 个持仓")
print()

if len(all_positions) == 0:
    print("⚠️ 当前没有持仓")
    sys.exit(0)

# 2. 计算Greeks
print("步骤 2: 计算组合Greeks...")
# 期权：delta * size（delta是单个期权的delta）
# 期货：delta已经等于value_eth（ETH单位），直接加delta即可
total_delta = (
    sum(pos['delta'] * pos['size'] for pos in all_positions.values() if pos['asset_type'] == 'option') +
    sum(pos['delta'] for pos in all_positions.values() if pos['asset_type'] in ['future', 'perpetual'])
)
total_gamma = sum(pos['gamma'] * pos['size'] for pos in all_positions.values())
total_vega = sum(pos['vega'] * pos['size'] for pos in all_positions.values())
total_theta = sum(pos['theta'] * pos['size'] for pos in all_positions.values())

portfolio_value = sum(pos['mark_price'] * pos['size'] for pos in all_positions.values())
portfolio_pnl = sum((pos['mark_price'] - pos['average_price']) * pos['size'] for pos in all_positions.values())

print(f"  Delta: {total_delta:.4f}")
print(f"  Gamma: {total_gamma:.6f}")
print(f"  Vega: {total_vega:.2f}")
print(f"  Theta: {total_theta:.4f}")
print(f"  组合价值: ${portfolio_value:.2f}")
print(f"  PnL: ${portfolio_pnl:.2f}")
print()

# 3. 保存到数据库
print("步骤 3: 保存到数据库...")
db = MonitorDatabase("monitor.duckdb")

db.insert_position_snapshot(
    timestamp=datetime.now(),
    total_delta=total_delta,
    total_gamma=total_gamma,
    total_theta=total_theta,
    total_vega=total_vega,
    total_rho=0.0,
    portfolio_value=portfolio_value,
    portfolio_pnl=portfolio_pnl,
    positions_json=json.dumps(all_positions),
    underlying_price=3000.0,
    risk_free_rate=0.05
)

print("✅ 快照已保存")
print()

# 4. 验证
print("步骤 4: 验证数据...")
stats = db.get_statistics()
print(f"  数据库快照数量: {stats['snapshot_count']}")
print(f"  最新快照时间: {stats.get('latest_snapshot', 'N/A')}")

latest = db.get_latest_snapshot()
if latest is not None and not latest.empty:
    snapshot = latest.iloc[0]
    positions = json.loads(snapshot['positions_json'])
    print(f"  最新快照持仓数: {len(positions)}")
    print("✅ 数据验证通过")
else:
    print("❌ 无法读取最新快照")

print()
print("=" * 60)
print("完成！请刷新前端页面查看数据")
print("=" * 60)

