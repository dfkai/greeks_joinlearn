"""
任务一：Deribit API研究与环境准备 - 测试脚本
目的：验证API连接，确认获取期权链数据和Greeks数据的API端点
"""

import requests
import pandas as pd
from pprint import pprint
from credentials import client_id, client_secret

# Deribit API基础URL
BASE_URL = "https://www.deribit.com/api/v2"

def authenticate():
    """认证并获取access_token"""
    auth_url = f"{BASE_URL}/public/auth"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.get(auth_url, params=params, headers={"Content-Type": "application/json"})
    
    if response.status_code == 200:
        data = response.json()
        access_token = data['result']['access_token']
        print("✓ 认证成功")
        return access_token
    else:
        print(f"✗ 认证失败，状态码: {response.status_code}")
        print(f"响应信息: {response.text}")
        return None

def test_get_instruments(currency="ETH", kind="option"):
    """测试获取期权工具列表"""
    print(f"\n{'='*60}")
    print(f"测试1: 获取 {currency} {kind} 工具列表")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/public/get_instruments"
    params = {
        "currency": currency,
        "kind": kind
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        instruments = data.get('result', [])
        print(f"✓ 成功获取 {len(instruments)} 个期权工具")
        
        # 显示前5个工具
        if instruments:
            print("\n前5个期权工具示例:")
            for i, inst in enumerate(instruments[:5]):
                print(f"  {i+1}. {inst.get('instrument_name', 'N/A')}")
                print(f"     到期日: {inst.get('expiration_timestamp', 'N/A')}")
                print(f"     行权价: {inst.get('strike', 'N/A')}")
                print(f"     类型: {inst.get('option_type', 'N/A')}")
        
        return instruments
    else:
        print(f"✗ 请求失败，状态码: {response.status_code}")
        print(f"响应信息: {response.text}")
        return None

def test_get_book_summary(currency="ETH", kind="option"):
    """测试获取期权链摘要数据"""
    print(f"\n{'='*60}")
    print(f"测试2: 获取 {currency} {kind} 期权链摘要")
    print(f"{'='*60}")
    
    access_token = authenticate()
    if not access_token:
        return None
    
    url = f"{BASE_URL}/public/get_book_summary_by_currency"
    params = {
        "currency": currency,
        "kind": kind
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        summaries = data.get('result', [])
        print(f"✓ 成功获取 {len(summaries)} 个期权摘要")
        
        # 显示第一个期权的所有字段
        if summaries:
            print("\n第一个期权摘要的所有字段:")
            first_summary = summaries[0]
            for key, value in first_summary.items():
                print(f"  {key}: {value}")
            
            # 检查是否包含Greeks相关字段
            greeks_fields = [k for k in first_summary.keys() if 'greeks' in k.lower() or k.lower() in ['delta', 'gamma', 'theta', 'vega']]
            if greeks_fields:
                print(f"\n✓ 发现Greeks相关字段: {greeks_fields}")
            else:
                print("\n⚠ 未发现Greeks字段，可能需要通过get_order_book获取")
        
        return summaries
    else:
        print(f"✗ 请求失败，状态码: {response.status_code}")
        print(f"响应信息: {response.text}")
        return None

def test_get_order_book(instrument_name, access_token=None):
    """测试获取订单簿（包含Greeks数据）"""
    print(f"\n{'='*60}")
    print(f"测试3: 获取订单簿数据（包含Greeks）")
    print(f"工具: {instrument_name}")
    print(f"{'='*60}")
    
    if not access_token:
        access_token = authenticate()
        if not access_token:
            return None
    
    url = f"{BASE_URL}/public/get_order_book"
    params = {
        "instrument_name": instrument_name,
        "depth": 1  # 只需要1层深度即可获取Greeks
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        result = data.get('result', {})
        print("✓ 成功获取订单簿数据")
        
        # 显示所有字段
        print("\n订单簿数据的所有字段:")
        for key, value in result.items():
            if key == 'greeks':
                print(f"\n  {key}:")
                if isinstance(value, dict):
                    for greek_key, greek_value in value.items():
                        print(f"    {greek_key}: {greek_value}")
                else:
                    print(f"    {value}")
            elif key in ['bids', 'asks']:
                print(f"  {key}: {len(value) if isinstance(value, list) else 'N/A'} 条记录")
            else:
                print(f"  {key}: {value}")
        
        # 检查Greeks数据
        if 'greeks' in result:
            print("\n✓ 成功获取Greeks数据!")
            greeks = result['greeks']
            print(f"  Delta: {greeks.get('delta', 'N/A')}")
            print(f"  Gamma: {greeks.get('gamma', 'N/A')}")
            print(f"  Theta: {greeks.get('theta', 'N/A')}")
            print(f"  Vega: {greeks.get('vega', 'N/A')}")
        else:
            print("\n⚠ 未找到Greeks数据")
        
        return result
    else:
        print(f"✗ 请求失败，状态码: {response.status_code}")
        print(f"响应信息: {response.text}")
        return None

def test_get_instrument(instrument_name):
    """测试获取单个工具信息"""
    print(f"\n{'='*60}")
    print(f"测试4: 获取工具详细信息")
    print(f"工具: {instrument_name}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/public/get_instrument"
    params = {
        "instrument_name": instrument_name
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        result = data.get('result', {})
        print("✓ 成功获取工具信息")
        
        print("\n工具信息的关键字段:")
        key_fields = ['instrument_name', 'instrument_type', 'kind', 'currency', 
                     'expiration_timestamp', 'strike', 'option_type', 'tick_size', 
                     'min_trade_amount', 'settlement_period']
        for field in key_fields:
            if field in result:
                print(f"  {field}: {result[field]}")
        
        return result
    else:
        print(f"✗ 请求失败，状态码: {response.status_code}")
        print(f"响应信息: {response.text}")
        return None

def main():
    """主测试流程"""
    print("="*60)
    print("Deribit API 测试脚本")
    print("任务一：API研究与环境准备")
    print("="*60)
    
    # 1. 测试认证
    print("\n步骤1: 测试API认证")
    access_token = authenticate()
    
    if not access_token:
        print("\n✗ 认证失败，无法继续测试")
        return
    
    # 2. 获取工具列表
    instruments = test_get_instruments(currency="ETH", kind="option")
    
    if not instruments:
        print("\n✗ 无法获取工具列表，测试终止")
        return
    
    # 选择一个工具进行详细测试
    test_instrument = instruments[0].get('instrument_name')
    print(f"\n选择测试工具: {test_instrument}")
    
    # 3. 获取工具详细信息
    instrument_info = test_get_instrument(test_instrument)
    
    # 4. 获取订单簿（包含Greeks）
    order_book = test_get_order_book(test_instrument, access_token)
    
    # 5. 获取期权链摘要
    summaries = test_get_book_summary(currency="ETH", kind="option")
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print("✓ API认证: 成功")
    print(f"✓ 获取工具列表: 成功 ({len(instruments)} 个工具)")
    print(f"✓ 获取工具信息: {'成功' if instrument_info else '失败'}")
    print(f"✓ 获取订单簿(Greeks): {'成功' if order_book and 'greeks' in order_book else '失败'}")
    print(f"✓ 获取期权链摘要: {'成功' if summaries else '失败'}")
    
    print("\n关键发现:")
    print("1. get_instruments - 获取所有期权工具列表（无需认证）")
    print("2. get_instrument - 获取单个工具基本信息（无需认证）")
    print("3. get_order_book - 获取订单簿，包含Greeks数据（需要认证）")
    print("4. get_book_summary_by_currency - 获取期权链摘要（需要认证）")
    
    print("\n推荐的数据获取策略:")
    print("- 使用 get_instruments 获取所有期权列表")
    print("- 使用 get_order_book 批量获取每个期权的Greeks数据")
    print("- 或使用 get_book_summary_by_currency 获取摘要，然后补充Greeks数据")

if __name__ == "__main__":
    main()


