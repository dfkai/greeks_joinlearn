"""
任务十二：BS模型计算器（期权定价引擎）
实现Black-Scholes期权定价模型，计算理论价格和Greeks
"""

import numpy as np
from scipy.stats import norm
from typing import Union, Dict, List
import pandas as pd


class BSCalculator:
    """Black-Scholes期权定价模型计算器"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        初始化BS计算器
        
        :param risk_free_rate: 无风险利率（年化），默认5%
        """
        self.risk_free_rate = risk_free_rate
    
    def _calculate_d1_d2(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                         T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                         r: float = None) -> tuple:
        """
        计算d1和d2
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param r: 无风险利率
        :return: (d1, d2)
        """
        if r is None:
            r = self.risk_free_rate
        
        # 避免除零错误
        T = np.maximum(T, 1e-10)
        sigma = np.maximum(sigma, 1e-10)
        
        # 计算d1和d2
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        return d1, d2
    
    def calculate_option_price(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                               T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                               option_type: str = 'call', r: float = None) -> Union[float, np.ndarray]:
        """
        计算期权价格（支持向量化）
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param option_type: 期权类型 'call' 或 'put'
        :param r: 无风险利率
        :return: 期权价格
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        if option_type.lower() == 'call' or option_type.upper() == 'C':
            # Call期权价格：C = S*N(d1) - K*exp(-rT)*N(d2)
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            # Put期权价格：P = K*exp(-rT)*N(-d2) - S*N(-d1)
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return price
    
    def calculate_delta(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                       T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                       option_type: str = 'call', r: float = None) -> Union[float, np.ndarray]:
        """
        计算Delta
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param option_type: 期权类型
        :param r: 无风险利率
        :return: Delta值
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        if option_type.lower() == 'call' or option_type.upper() == 'C':
            # Call Delta: Δ = N(d1)
            delta = norm.cdf(d1)
        else:  # put
            # Put Delta: Δ = N(d1) - 1
            delta = norm.cdf(d1) - 1
        
        return delta
    
    def calculate_gamma(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                       T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                       r: float = None) -> Union[float, np.ndarray]:
        """
        计算Gamma（Call和Put的Gamma相同）
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param r: 无风险利率
        :return: Gamma值
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        # Gamma: Γ = N'(d1) / (S * σ * √T)
        # N'(d1) = 1/√(2π) * exp(-d1²/2)
        T = np.maximum(T, 1e-10)
        sigma = np.maximum(sigma, 1e-10)
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        return gamma
    
    def calculate_theta(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                       T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                       option_type: str = 'call', r: float = None) -> Union[float, np.ndarray]:
        """
        计算Theta（注意：返回值是每年的Theta，需要除以365得到每日Theta）
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param option_type: 期权类型
        :param r: 无风险利率
        :return: Theta值（年化）
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        T = np.maximum(T, 1e-10)
        
        if option_type.lower() == 'call' or option_type.upper() == 'C':
            # Call Theta: Θ = -S*N'(d1)*σ/(2√T) - rK*exp(-rT)*N(d2)
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2))
        else:  # put
            # Put Theta: Θ = -S*N'(d1)*σ/(2√T) + rK*exp(-rT)*N(-d2)
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2))
        
        return theta
    
    def calculate_vega(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                      T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                      r: float = None) -> Union[float, np.ndarray]:
        """
        计算Vega（Call和Put的Vega相同）
        注意：返回值是波动率变化1个单位（1.0即100%）时的价格变化
        如果需要1%变化的影响，需要除以100
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param r: 无风险利率
        :return: Vega值
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        T = np.maximum(T, 1e-10)
        
        # Vega: ν = S * √T * N'(d1)
        vega = S * np.sqrt(T) * norm.pdf(d1)
        
        return vega
    
    def calculate_rho(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                     T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                     option_type: str = 'call', r: float = None) -> Union[float, np.ndarray]:
        """
        计算Rho
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param option_type: 期权类型
        :param r: 无风险利率
        :return: Rho值
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        T = np.maximum(T, 1e-10)
        
        if option_type.lower() == 'call' or option_type.upper() == 'C':
            # Call Rho: ρ = K*T*exp(-rT)*N(d2)
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            # Put Rho: ρ = -K*T*exp(-rT)*N(-d2)
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
        
        return rho
    
    def calculate_vanna(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                       T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                       r: float = None) -> Union[float, np.ndarray]:
        """
        计算Vanna（二阶Greeks）
        Vanna = ∂²C/∂S∂σ = ∂Delta/∂σ = ∂Vega/∂S
        衡量波动率变化对Delta的影响，或标的价格变化对Vega的影响
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param r: 无风险利率
        :return: Vanna值
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        S = np.maximum(S, 1e-10)
        T = np.maximum(T, 1e-10)
        sigma = np.maximum(sigma, 1e-10)
        
        # 标准 Vanna 公式（修正）: -N'(d1) × d2 / (S × σ)
        # 负号是关键！Vanna = ∂Vega/∂S = ∂Delta/∂σ
        # 物理含义：Vega曲线的斜率（对价格的导数）
        vanna = -norm.pdf(d1) * d2 / (S * sigma)
        
        return vanna
    
    def calculate_volga(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                       T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                       r: float = None) -> Union[float, np.ndarray]:
        """
        计算Volga（又称Vomma，二阶Greeks）
        Volga = ∂²C/∂σ² = ∂Vega/∂σ
        衡量Vega对波动率变化的敏感性
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param r: 无风险利率
        :return: Volga值
        """
        if r is None:
            r = self.risk_free_rate
        
        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        
        T = np.maximum(T, 1e-10)
        sigma = np.maximum(sigma, 1e-10)
        
        # Volga = S * √T * N'(d1) * d1 * d2 / σ
        # 或者：Volga = Vega * d1 * d2 / σ
        vega = self.calculate_vega(S, K, T, sigma, r)
        volga = vega * d1 * d2 / sigma
        
        return volga
    
    def calculate_all_greeks(self, S: Union[float, np.ndarray], K: Union[float, np.ndarray], 
                            T: Union[float, np.ndarray], sigma: Union[float, np.ndarray], 
                            option_type: str = 'call', r: float = None, 
                            include_second_order: bool = True) -> Dict:
        """
        一次性计算所有Greeks（提高效率）
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率（年化）
        :param option_type: 期权类型
        :param r: 无风险利率
        :param include_second_order: 是否包含二阶Greeks（Vanna, Volga）
        :return: 包含所有Greeks的字典
        """
        if r is None:
            r = self.risk_free_rate
        
        price = self.calculate_option_price(S, K, T, sigma, option_type, r)
        delta = self.calculate_delta(S, K, T, sigma, option_type, r)
        gamma = self.calculate_gamma(S, K, T, sigma, r)
        theta = self.calculate_theta(S, K, T, sigma, option_type, r)
        vega = self.calculate_vega(S, K, T, sigma, r)
        rho = self.calculate_rho(S, K, T, sigma, option_type, r)
        
        result = {
            'price': price,
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'theta_daily': theta / 365,  # 每日Theta
            'vega': vega,
            'vega_percent': vega / 100,  # 1%波动率变化的影响
            'rho': rho
        }
        
        # 添加二阶Greeks
        if include_second_order:
            vanna = self.calculate_vanna(S, K, T, sigma, r)
            volga = self.calculate_volga(S, K, T, sigma, r)
            result['vanna'] = vanna
            result['volga'] = volga
        
        return result
    
    def price_scenario_analysis(self, K: float, T: float, sigma: float, 
                                option_type: str = 'call', 
                                S_min: float = None, S_max: float = None, 
                                current_S: float = 3000, num_points: int = 50, 
                                r: float = None) -> pd.DataFrame:
        """
        标的价格扫描情景分析
        
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma: 波动率
        :param option_type: 期权类型
        :param S_min: 最低价格（默认current_S的50%）
        :param S_max: 最高价格（默认current_S的150%）
        :param current_S: 当前标的价格
        :param num_points: 价格点数
        :param r: 无风险利率
        :return: DataFrame包含价格和所有Greeks
        """
        if r is None:
            r = self.risk_free_rate
        
        # 设置价格范围
        if S_min is None:
            S_min = current_S * 0.5
        if S_max is None:
            S_max = current_S * 1.5
        
        # 生成价格序列
        S_range = np.linspace(S_min, S_max, num_points)
        
        # 批量计算Greeks
        results = []
        for S in S_range:
            greeks = self.calculate_all_greeks(S, K, T, sigma, option_type, r)
            results.append({
                'spot_price': S,
                'option_price': greeks['price'],
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'theta_daily': greeks['theta_daily'],
                'vega': greeks['vega'],
                'vega_percent': greeks['vega_percent'],
                'rho': greeks['rho']
            })
        
        df = pd.DataFrame(results)
        df['current_spot'] = current_S  # 标记当前价格
        
        return df
    
    def time_decay_analysis(self, S: float, K: float, sigma: float, 
                           option_type: str = 'call', 
                           T_current: float = None, days_to_expiry: int = None,
                           num_points: int = 50, r: float = None) -> pd.DataFrame:
        """
        时间衰减情景分析
        
        :param S: 标的价格
        :param K: 行权价
        :param sigma: 波动率
        :param option_type: 期权类型
        :param T_current: 当前到期时间（年）
        :param days_to_expiry: 剩余天数（与T_current二选一）
        :param num_points: 时间点数
        :param r: 无风险利率
        :return: DataFrame包含时间和所有Greeks
        """
        if r is None:
            r = self.risk_free_rate
        
        # 确定时间范围
        if T_current is None and days_to_expiry is not None:
            T_current = days_to_expiry / 365.0
        elif T_current is None:
            T_current = 30 / 365.0  # 默认30天
        
        # 生成时间序列（从当前到到期）
        T_range = np.linspace(T_current, 0.001, num_points)  # 避免T=0
        days_range = T_range * 365
        
        # 批量计算Greeks
        results = []
        for T, days in zip(T_range, days_range):
            greeks = self.calculate_all_greeks(S, K, T, sigma, option_type, r)
            results.append({
                'days_to_expiry': days,
                'time_to_maturity': T,
                'option_price': greeks['price'],
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'theta_daily': greeks['theta_daily'],
                'vega': greeks['vega'],
                'rho': greeks['rho']
            })
        
        return pd.DataFrame(results)
    
    def volatility_scenario_analysis(self, S: float, K: float, T: float, 
                                     sigma_current: float, option_type: str = 'call',
                                     vol_change_min: float = -0.5, vol_change_max: float = 0.5,
                                     num_points: int = 50, r: float = None) -> pd.DataFrame:
        """
        波动率扫描情景分析
        
        :param S: 标的价格
        :param K: 行权价
        :param T: 到期时间（年）
        :param sigma_current: 当前波动率
        :param option_type: 期权类型
        :param vol_change_min: 波动率最小变化（-50%即-0.5）
        :param vol_change_max: 波动率最大变化（+50%即+0.5）
        :param num_points: 波动率点数
        :param r: 无风险利率
        :return: DataFrame包含波动率和所有Greeks
        """
        if r is None:
            r = self.risk_free_rate
        
        # 生成波动率序列
        vol_change_range = np.linspace(vol_change_min, vol_change_max, num_points)
        sigma_range = sigma_current * (1 + vol_change_range)
        sigma_range = np.maximum(sigma_range, 0.01)  # 确保波动率至少1%
        
        # 批量计算Greeks
        results = []
        for vol_change, sigma in zip(vol_change_range, sigma_range):
            greeks = self.calculate_all_greeks(S, K, T, sigma, option_type, r)
            results.append({
                'iv_change_percent': vol_change * 100,
                'volatility': sigma,
                'option_price': greeks['price'],
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'vega': greeks['vega'],
                'vega_percent': greeks['vega_percent'],
                'rho': greeks['rho']
            })
        
        df = pd.DataFrame(results)
        df['current_iv'] = sigma_current
        
        return df


if __name__ == "__main__":
    # 测试代码
    print("="*60)
    print("BS模型计算器测试")
    print("="*60)
    
    # 初始化计算器
    bs = BSCalculator(risk_free_rate=0.05)
    
    # 测试参数
    S = 3000  # ETH当前价格
    K = 3000  # ATM行权价
    T = 30 / 365  # 30天到期
    sigma = 1.0  # 100%波动率（加密货币典型值）
    
    print("\n测试1: 计算ATM Call期权价格和Greeks")
    print("-" * 60)
    greeks_call = bs.calculate_all_greeks(S, K, T, sigma, 'call')
    print(f"标的价格 S = {S}")
    print(f"行权价 K = {K}")
    print(f"到期时间 T = {T:.4f}年 ({T*365:.0f}天)")
    print(f"波动率 σ = {sigma:.2%}")
    print(f"\nCall期权价格: {greeks_call['price']:.4f}")
    print(f"Delta: {greeks_call['delta']:.4f}")
    print(f"Gamma: {greeks_call['gamma']:.6f}")
    print(f"Theta (年): {greeks_call['theta']:.4f}")
    print(f"Theta (日): {greeks_call['theta_daily']:.4f}")
    print(f"Vega: {greeks_call['vega']:.4f}")
    print(f"Rho: {greeks_call['rho']:.4f}")
    
    print("\n测试2: 计算ATM Put期权价格和Greeks")
    print("-" * 60)
    greeks_put = bs.calculate_all_greeks(S, K, T, sigma, 'put')
    print(f"Put期权价格: {greeks_put['price']:.4f}")
    print(f"Delta: {greeks_put['delta']:.4f}")
    print(f"Gamma: {greeks_put['gamma']:.6f}")
    print(f"Theta (日): {greeks_put['theta_daily']:.4f}")
    
    print("\n测试3: 验证Put-Call Parity")
    print("-" * 60)
    parity_left = greeks_call['price'] - greeks_put['price']
    parity_right = S - K * np.exp(-bs.risk_free_rate * T)
    print(f"C - P = {parity_left:.4f}")
    print(f"S - K*exp(-rT) = {parity_right:.4f}")
    print(f"差异: {abs(parity_left - parity_right):.6f}")
    if abs(parity_left - parity_right) < 0.01:
        print("✓ Put-Call Parity验证通过")
    
    print("\n测试4: 价格扫描情景分析")
    print("-" * 60)
    price_scenario = bs.price_scenario_analysis(K, T, sigma, 'call', current_S=S, num_points=10)
    print(f"生成 {len(price_scenario)} 个价格点")
    print("\n前5个价格点:")
    print(price_scenario[['spot_price', 'option_price', 'delta', 'gamma']].head())
    
    print("\n测试5: 时间衰减分析")
    print("-" * 60)
    time_scenario = bs.time_decay_analysis(S, K, sigma, 'call', days_to_expiry=30, num_points=10)
    print(f"生成 {len(time_scenario)} 个时间点")
    print("\n前5个时间点:")
    print(time_scenario[['days_to_expiry', 'option_price', 'theta_daily']].head())
    
    print("\n测试6: 波动率敏感性分析")
    print("-" * 60)
    vol_scenario = bs.volatility_scenario_analysis(S, K, T, sigma, 'call', num_points=10)
    print(f"生成 {len(vol_scenario)} 个波动率点")
    print("\n前5个波动率点:")
    print(vol_scenario[['iv_change_percent', 'volatility', 'option_price', 'vega']].head())
    
    print("\n" + "="*60)
    print("BS模型计算器测试完成")
    print("="*60)

