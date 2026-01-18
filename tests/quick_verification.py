"""
快速验证脚本 - 验证任务1-7的所有功能是否正常
"""

import sys
from pathlib import Path

print("="*60)
print("Deribit期权链数据分析系统 - 功能验证")
print("="*60)

# 检查1: 依赖包
print("\n1. 检查依赖包...")
try:
    import streamlit
    import pandas
    import numpy
    import duckdb
    import plotly
    import requests
    print("  ✓ 所有依赖包已安装")
except ImportError as e:
    print(f"  ✗ 缺少依赖包: {e}")
    print("  请运行: pip install -r requirements.txt")
    sys.exit(1)

# 检查2: 配置文件
print("\n2. 检查配置文件...")
try:
    from credentials import client_id, client_secret
    if client_id and client_secret:
        print("  ✓ credentials.py配置正确")
    else:
        print("  ⚠ credentials.py中的API凭证为空，请配置")
except ImportError:
    print("  ✗ credentials.py文件不存在")
    sys.exit(1)

# 检查3: 核心模块
print("\n3. 检查核心模块...")
modules = [
    ('Deribit_HTTP', 'DeribitAPI'),
    ('data_fetcher', 'OptionsChainFetcher'),
    ('database', 'OptionsDatabase'),
    ('data_collector', 'DataCollector'),
]

for module_name, class_name in modules:
    try:
        module = __import__(module_name)
        cls = getattr(module, class_name)
        print(f"  ✓ {module_name}.{class_name} 可导入")
    except Exception as e:
        print(f"  ✗ {module_name}.{class_name} 导入失败: {e}")

# 检查4: 数据库文件
print("\n4. 检查数据库文件...")
db_path = "options_data.duckdb"
if Path(db_path).exists():
    print(f"  ✓ 数据库文件存在: {db_path}")
    try:
        from src.core import OptionsDatabase
        db = OptionsDatabase(db_path)
        stats = db.get_statistics()
        print(f"    期权链记录数: {stats.get('options_chain_count', 0)}")
        print(f"    Greeks记录数: {stats.get('greeks_count', 0)}")
        print(f"    唯一到期日: {stats.get('unique_expiration_dates', 0)}")
        db.close()
    except Exception as e:
        print(f"  ⚠ 数据库文件存在但无法读取: {e}")
else:
    print(f"  ⚠ 数据库文件不存在: {db_path}")
    print("    请先运行数据采集脚本创建数据库")

# 检查5: Streamlit应用
print("\n5. 检查Streamlit应用...")
if Path("app.py").exists():
    print("  ✓ app.py文件存在")
    # 检查语法错误
    try:
        with open("app.py", "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, "app.py", "exec")
        print("  ✓ app.py语法正确")
    except SyntaxError as e:
        print(f"  ✗ app.py语法错误: {e}")
        sys.exit(1)
else:
    print("  ✗ app.py文件不存在")
    sys.exit(1)

# 检查6: API连接（可选）
print("\n6. 测试API连接（可选）...")
try:
    from api.Deribit_HTTP import DeribitAPI
    from credentials import client_id, client_secret
    
    print("  正在测试API连接...")
    api = DeribitAPI(client_id, client_secret)
    if api.access_token:
        print("  ✓ API认证成功")
        
        # 测试获取工具列表
        data = api.get_instruments("ETH", "option")
        if data and 'result' in data:
            count = len(data['result'])
            print(f"  ✓ 可以获取ETH期权工具列表 ({count} 个)")
    else:
        print("  ⚠ API认证失败，请检查凭证")
except Exception as e:
    print(f"  ⚠ API连接测试失败: {e}")

# 总结
print("\n" + "="*60)
print("验证完成")
print("="*60)
print("\n如果所有检查都通过，您可以：")
print("1. 运行数据采集: python -c \"from src.collectors import DataCollector; collector = DataCollector(); collector.collect_summary_data()\"")
print("2. 启动Streamlit应用: streamlit run app.py")
print("\n详细使用说明请查看: 使用指南.md")

