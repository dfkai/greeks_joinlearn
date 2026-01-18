"""
持仓数据解析工具
支持新旧两种JSON格式的解析
"""

import json
from typing import Dict, Any


def parse_positions_json(positions_json: str) -> Dict[str, Dict[str, Any]]:
    """
    解析positions_json，支持新旧两种格式
    
    新格式（紧凑）：
    {
        'name': {
            't': 'option',  # type
            's': 10,         # size
            'ap': 95.0,      # average_price
            'mp': 100.0,     # mark_price
            'd': 0.5,        # delta
            'iv': 0.8,       # mark_iv (期权)
            'g': 0.01,       # gamma (期权)
            'th': -0.05,     # theta (期权)
            'v': 0.2,        # vega (期权)
            've': 1.5        # value_eth (期货)
        }
    }
    
    旧格式（完整字段名）：
    {
        'name': {
            'asset_type': 'option',
            'size': 10,
            'average_price': 95.0,
            ...
        }
    }
    
    :param positions_json: JSON字符串
    :return: 解析后的持仓字典（统一转换为旧格式，保持兼容性）
    """
    positions = json.loads(positions_json)
    
    # 检查是否是紧凑格式（通过检查第一个字段是否是单字母）
    if positions:
        first_pos = list(positions.values())[0]
        is_compact_format = 't' in first_pos and 's' in first_pos
        
        if is_compact_format:
            # 转换为完整格式（保持向后兼容）
            expanded_positions = {}
            for name, pos in positions.items():
                expanded_pos = {
                    'asset_type': pos.get('t', 'option'),
                    'size': pos.get('s', 0),
                    'average_price': pos.get('ap', 0),
                    'mark_price': pos.get('mp', 0),
                    'delta': pos.get('d', 0),
                }
                
                asset_type = expanded_pos['asset_type']
                if asset_type == 'option':
                    if 'iv' in pos:
                        expanded_pos['mark_iv'] = pos['iv']
                    expanded_pos['gamma'] = pos.get('g', 0)
                    expanded_pos['theta'] = pos.get('th', 0)
                    expanded_pos['vega'] = pos.get('v', 0)
                elif asset_type in ['future', 'perpetual']:
                    if 've' in pos:
                        expanded_pos['value_eth'] = pos['ve']
                    expanded_pos['gamma'] = 0.0
                    expanded_pos['theta'] = 0.0
                    expanded_pos['vega'] = 0.0
                    expanded_pos['mark_iv'] = None
                
                expanded_positions[name] = expanded_pos
            return expanded_positions
    
    # 已经是完整格式，直接返回
    return positions
