import pandas as pd
# 显示所有列
pd.set_option('display.max_columns', None)
from pprint import pprint
from api.Deribit_HTTP import DeribitAPI
from credentials import client_id, client_secret
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial

api = DeribitAPI(client_id, client_secret)

# 获取 ETH 的期权数据
data = api.get_book_summary_by_currency(currency="ETH", kind="option")
# pprint(data)

# 提取 'result' 部分的数据
data_result = data['result']

# 将数据转换为 DataFrame
df = pd.DataFrame(data_result)

# 显示 mark_iv instrument_name underlying_index
df = df[['mark_iv', 'instrument_name', 'underlying_index', 'open_interest', 'underlying_price']]

# 根据 underlying_index 排序
df = df.sort_values(by='underlying_index')

# 使用正则表达式提取日期部分 '11OCT24'
df['date_str'] = df['underlying_index'].str.extract(r'(\d{2}[A-Z]{3}\d{2})')
# 将提取的日期字符串转换为标准日期格式 'dd-mmm-yy' -> 'YYYY-MM-DD'
df['expiration_date'] = pd.to_datetime(df['date_str'], format='%d%b%y')

# 三个月内的期权数据
df = df[df['expiration_date'] < pd.Timestamp.now() + pd.DateOffset(months=2)]

# 使用正则表达式提取 instrument_name 中的执行价 (strike price)
df['strike_price'] = df['instrument_name'].str.extract(r'-(\d+)-')
# 将提取出的执行价转换为整数类型
df['strike_price'] = df['strike_price'].astype(int)

# 根据 strike_price 排序 倒序
df = df.sort_values(by='strike_price', ascending=False)

# strike_price +/- 50% 的 underlying_price 范围筛选一下
df = df[(df['strike_price'] > df['underlying_price'] * 0.5) & (df['strike_price'] < df['underlying_price'] * 1.5)]

# 打印 DataFrame
print(df.head())

# exit()

def fit_volatility_smile(strikes, ivs, open_interests):
    if open_interests.sum() > 0:
        weighted_iv = np.average(ivs, weights=open_interests)
    else:
        weighted_iv = np.nan  # 如果无有效数据，则返回 NaN

    # 检查数据有效性
    print("Strikes:", strikes)
    print("IVs:", ivs)
    print("Weighted IV:", weighted_iv)

    if len(strikes) > 0 and len(ivs) > 0 and len(strikes) == len(ivs):
        # 对执行价（strike）与隐含波动率（IV）做二次多项式拟合
        p = Polynomial.fit(strikes, ivs, 2)
    else:
        p = None  # 如果数据无效，返回 None

    return p, weighted_iv



# 当前价格
current_price = df['underlying_price'].unique()[0]  # 获取唯一的当前价格

# 预测价格差
predicted_prices = []

# 为了绘制价格锥
for date in df['expiration_date'].unique():
    subset = df[df['expiration_date'] == date]

    # 计算拟合波动率和加权平均隐含波动率
    poly, iv_combined = fit_volatility_smile(subset['strike_price'], subset['mark_iv'], subset['open_interest'])

    # 如果 iv_combined 是 NaN 或 poly 是 None，跳过该日期
    if np.isnan(iv_combined) or poly is None:
        continue

    # 计算到期天数
    days_to_expiration = (pd.to_datetime(date) - pd.Timestamp.now()).days

    # 确保到期天数为正数
    if days_to_expiration <= 0:
        continue

    # 计算价格差
    price_diff = current_price * iv_combined/100 * np.sqrt(days_to_expiration / 252)

    # 预测的价格范围
    predicted_prices.append((current_price - price_diff, current_price + price_diff, date))

# 整理为 DataFrame 方便绘图
predicted_prices_df = pd.DataFrame(predicted_prices, columns=['Lower Price', 'Upper Price', 'Expiration Date'])

# 打印预测价格 DataFrame，检查是否有数据
print(predicted_prices_df)

# 检查 DataFrame 是否为空
if predicted_prices_df.empty:
    print("没有有效的预测价格数据，无法绘图。")
else:
    # 确保按到期日期排序
    predicted_prices_df = predicted_prices_df.sort_values(by='Expiration Date')

    # 绘制图形
    plt.figure(figsize=(12, 6))

    # 绘制下限和上限价格的散点
    plt.scatter(predicted_prices_df['Lower Price'], predicted_prices_df['Expiration Date'], color='blue', label='Lower Price', marker='o')
    plt.scatter(predicted_prices_df['Upper Price'], predicted_prices_df['Expiration Date'], color='red', label='Upper Price', marker='o')

    # 添加当前价格水平线
    current_price = df['underlying_price'].unique()[0]
    plt.axvline(x=current_price, color='green', linestyle='--', label='Current Price')

    # 连接下限和上限的散点
    plt.plot(predicted_prices_df['Lower Price'], predicted_prices_df['Expiration Date'], color='blue', linestyle='-', alpha=0.6)
    plt.plot(predicted_prices_df['Upper Price'], predicted_prices_df['Expiration Date'], color='red', linestyle='-', alpha=0.6)

    # 填充下限和上限之间的区域
    plt.fill_betweenx(predicted_prices_df['Expiration Date'],
                      predicted_prices_df['Lower Price'],
                      predicted_prices_df['Upper Price'],
                      color='lightblue', alpha=0.3)

    # 计算68%置信区间（±1个标准差）
    predicted_prices_df['Mean Price'] = (predicted_prices_df['Lower Price'] + predicted_prices_df['Upper Price']) / 2
    predicted_prices_df['Lower 68%'] = predicted_prices_df['Mean Price'] - (predicted_prices_df['Upper Price'] - predicted_prices_df['Mean Price']) * 0.6827
    predicted_prices_df['Upper 68%'] = predicted_prices_df['Mean Price'] + (predicted_prices_df['Upper Price'] - predicted_prices_df['Mean Price']) * 0.6827

    # 绘制68%置信区间
    plt.plot(predicted_prices_df['Lower 68%'], predicted_prices_df['Expiration Date'], color='orange', linestyle='--', label='Lower 68% CI')
    plt.plot(predicted_prices_df['Upper 68%'], predicted_prices_df['Expiration Date'], color='purple', linestyle='--', label='Upper 68% CI')

    # 填充68%置信区间
    plt.fill_betweenx(predicted_prices_df['Expiration Date'],
                      predicted_prices_df['Lower 68%'],
                      predicted_prices_df['Upper 68%'],
                      color='lightyellow', alpha=0.5)

    # 将 Y 轴时间倒转
    plt.gca().invert_yaxis()

    # 图形设置
    plt.xlabel('Price')
    plt.ylabel('Expiration Date')
    plt.title('Price Cone Based on Implied Volatility with 68% Confidence Interval')
    plt.legend()
    plt.grid()
    plt.show()

'''
# 我要绘制价格锥
1. underlying 品种的预测价格范围
2. 对应的时间

不同时间得到隐含波动率，

当前价格 * 隐含波动率 * sqrt(到期天数/252) = +/- 预测价格差

用+/- 预测价格差结合当前价格绘制出价格锥

'''