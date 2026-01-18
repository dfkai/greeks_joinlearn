"""
任务十三：持仓组合Greeks分析与可视化
基于BS模型，实现期权组合构建、Greeks计算和风险分析
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from .bs_calculator import BSCalculator
from datetime import datetime, timedelta


class Position:
    """单个持仓"""
    
    def __init__(self, expiration_date: str, strike: float, option_type: str, 
                 quantity: int, volatility: float = None, entry_price: float = None):
        """
        初始化持仓
        
        :param expiration_date: 到期日（字符串格式 'YYYY-MM-DD'）
        :param strike: 行权价
        :param option_type: 期权类型 'C' 或 'P'
        :param quantity: 数量（正数=买入，负数=卖出）
        :param volatility: 波动率（如果为None，使用默认值1.0）
        :param entry_price: 建仓时的实际入场价格（mark_price），如果为None，后续会使用BS理论价格计算
        """
        self.expiration_date = pd.to_datetime(expiration_date)
        self.strike = strike
        self.option_type = option_type.upper()
        self.quantity = quantity
        self.volatility = volatility if volatility is not None else 1.0
        self.entry_price = entry_price  # 建仓时的实际入场价格
    
    def days_to_expiry(self, current_date: datetime = None) -> int:
        """计算剩余天数"""
        if current_date is None:
            current_date = datetime.now()
        delta = self.expiration_date - pd.to_datetime(current_date)
        return max(delta.days, 0)
    
    def time_to_maturity(self, current_date: datetime = None) -> float:
        """计算剩余时间（年）"""
        return self.days_to_expiry(current_date) / 365.0
    
    def __repr__(self):
        sign = '+' if self.quantity > 0 else ''
        return f"{sign}{self.quantity} {self.option_type} {self.strike} exp:{self.expiration_date.strftime('%Y-%m-%d')}"


class PortfolioAnalyzer:
    """持仓组合分析器"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        初始化组合分析器
        
        :param risk_free_rate: 无风险利率
        """
        self.bs_calculator = BSCalculator(risk_free_rate=risk_free_rate)
        self.positions: List[Position] = []
        self.current_spot_price = 3000.0  # 默认当前价格
    
    def add_position(self, expiration_date: str, strike: float, option_type: str, 
                    quantity: int, volatility: float = None, entry_price: float = None):
        """
        添加持仓
        
        :param expiration_date: 到期日
        :param strike: 行权价
        :param option_type: 期权类型
        :param quantity: 数量
        :param volatility: 波动率
        :param entry_price: 建仓时的实际入场价格（mark_price），如果为None，将使用BS理论价格计算
        """
        position = Position(expiration_date, strike, option_type, quantity, volatility, entry_price)
        self.positions.append(position)
    
    def remove_position(self, index: int):
        """删除指定索引的持仓"""
        if 0 <= index < len(self.positions):
            self.positions.pop(index)
    
    def clear_positions(self):
        """清空所有持仓"""
        self.positions = []
    
    def get_positions_df(self) -> pd.DataFrame:
        """获取持仓列表DataFrame"""
        if not self.positions:
            return pd.DataFrame()
        
        positions_data = []
        for i, pos in enumerate(self.positions):
            positions_data.append({
                'index': i,
                'expiration_date': pos.expiration_date.strftime('%Y-%m-%d'),
                'strike': pos.strike,
                'option_type': pos.option_type,
                'quantity': pos.quantity,
                'volatility': pos.volatility,
                'entry_price': pos.entry_price,  # 建仓价格
                'days_to_expiry': pos.days_to_expiry()
            })
        
        return pd.DataFrame(positions_data)
    
    def calculate_cost_basis(self, current_spot_price: float = None) -> float:
        """
        计算建仓成本（成本基准）
        
        建仓成本 = Σ(entry_price × quantity)
        其中entry_price是建仓时的实际入场价格（mark_price）
        如果entry_price为None，使用当前价格下的BS理论价格作为近似值
        
        :param current_spot_price: 当前标的价格（用于计算entry_price为None时的理论价格）
        :return: 建仓成本
        """
        if not self.positions:
            return 0.0
        
        if current_spot_price is None:
            current_spot_price = self.current_spot_price
        
        cost_basis = 0.0
        for pos in self.positions:
            if pos.entry_price is not None:
                # 使用实际的建仓价格
                entry_price = pos.entry_price
            else:
                # 如果未提供entry_price，使用当前价格和原始到期时间计算BS理论价格
                # 注意：这里使用原始的到期时间（从现在到到期日），而不是调整后的时间
                # 这样可以确保建仓成本的计算不会因为时间流逝而变化
                T_original = pos.time_to_maturity(current_date=datetime.now())
                if T_original > 0:
                    entry_price = self.bs_calculator.calculate_option_price(
                        current_spot_price,
                        pos.strike,
                        T_original,
                        pos.volatility,
                        pos.option_type.lower()
                    )
                else:
                    # 如果期权已经到期，使用当前的内在价值作为建仓成本
                    if pos.option_type.upper() == 'C':
                        entry_price = max(current_spot_price - pos.strike, 0.0)
                    else:
                        entry_price = max(pos.strike - current_spot_price, 0.0)
            
            # 建仓成本 = entry_price × quantity
            cost_basis += entry_price * pos.quantity
        
        return cost_basis
    
    def calculate_portfolio_greeks(self, spot_price: float = None, 
                                   current_date: datetime = None,
                                   volatility_multiplier: float = 1.0,
                                   time_days_offset: int = 0) -> Dict:
        """
        计算组合的总Greeks（线性相加）
        
        :param spot_price: 标的价格（如果None，使用current_spot_price）
        :param current_date: 当前日期
        :param volatility_multiplier: 波动率倍数（1.0表示无变化，1.1表示+10%，0.9表示-10%）
        :param time_days_offset: 时间偏移天数（0表示当前，正数表示未来）
        :return: 组合Greeks字典
        """
        if spot_price is None:
            spot_price = self.current_spot_price
        
        if not self.positions:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'theta_daily': 0.0,
                'vega': 0.0,
                'rho': 0.0,
                'vanna': 0.0,
                'volga': 0.0,
                'position_value': 0.0
            }
        
        # 计算调整后的日期
        if current_date is None:
            current_date = datetime.now()
        adjusted_date = current_date + timedelta(days=time_days_offset)
        
        # 累积Greeks（包含二阶Greeks）
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0
        total_vanna = 0.0
        total_volga = 0.0
        total_value = 0.0
        
        for pos in self.positions:
            # 使用调整后的日期计算剩余时间
            T = pos.time_to_maturity(adjusted_date)
            
            # 如果已到期或接近到期（T <= 0.001年，即小于0.365天），使用内在价值
            if T <= 0.001:
                # 计算内在价值
                if pos.option_type.upper() == 'C':
                    # Call内在价值 = max(S - K, 0)
                    intrinsic_value = max(spot_price - pos.strike, 0.0)
                    # Delta: ITM时为1，OTM时为0
                    delta = 1.0 if spot_price > pos.strike else 0.0
                else:  # Put
                    # Put内在价值 = max(K - S, 0)
                    intrinsic_value = max(pos.strike - spot_price, 0.0)
                    # Delta: ITM时为-1，OTM时为0
                    delta = -1.0 if spot_price < pos.strike else 0.0
                
                # 到期时，其他Greeks都为0
                total_delta += delta * pos.quantity
                total_value += intrinsic_value * pos.quantity
                # Gamma, Theta, Vega, Rho, Vanna, Volga在到期时都为0
                continue
            
            # 应用波动率倍数
            adjusted_volatility = pos.volatility * volatility_multiplier
            
            # 计算该持仓的Greeks
            greeks = self.bs_calculator.calculate_all_greeks(
                S=spot_price,
                K=pos.strike,
                T=T,
                sigma=adjusted_volatility,
                option_type=pos.option_type
            )
            
            # 加权累加（乘以数量）
            total_delta += greeks['delta'] * pos.quantity
            total_gamma += greeks['gamma'] * pos.quantity
            total_theta += greeks['theta'] * pos.quantity
            total_vega += greeks['vega'] * pos.quantity
            total_rho += greeks['rho'] * pos.quantity
            total_vanna += greeks.get('vanna', 0.0) * pos.quantity
            total_volga += greeks.get('volga', 0.0) * pos.quantity
            total_value += greeks['price'] * pos.quantity
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'theta_daily': total_theta / 365,
            'vega': total_vega,
            'vega_percent': total_vega / 100,
            'rho': total_rho,
            'vanna': total_vanna,
            'volga': total_volga,
            'position_value': total_value
        }
    
    def calculate_single_position_greeks(self, position: Position, spot_price: float = None,
                                         elapsed_days: int = 0, current_date: datetime = None,
                                         volatility_multiplier: float = 1.0) -> Dict:
        """
        计算单个期权在指定已过天数下的Greeks
        
        用于叠加对比模式，计算单个期权的时间曲线
        
        :param position: Position对象
        :param spot_price: 标的价格（如果None，使用current_spot_price）
        :param elapsed_days: 从当前快照起已过天数（0表示当前）
        :param current_date: 当前日期（如果None，使用datetime.now()）
        :param volatility_multiplier: 波动率倍数（1.0表示无变化）
        :return: 单个期权的Greeks字典
        """
        if spot_price is None:
            spot_price = self.current_spot_price
        
        if current_date is None:
            current_date = datetime.now()
        
        # 计算调整后的日期
        adjusted_date = current_date + timedelta(days=elapsed_days)
        
        # 计算剩余时间
        T = position.time_to_maturity(adjusted_date)
        
        # 如果已到期或接近到期，使用内在价值
        if T <= 0.001:
            # 计算内在价值
            if position.option_type.upper() == 'C':
                intrinsic_value = max(spot_price - position.strike, 0.0)
                delta = 1.0 if spot_price > position.strike else 0.0
            else:  # Put
                intrinsic_value = max(position.strike - spot_price, 0.0)
                delta = -1.0 if spot_price < position.strike else 0.0
            
            return {
                'delta': delta * position.quantity,
                'gamma': 0.0,
                'theta': 0.0,
                'theta_daily': 0.0,
                'vega': 0.0,
                'rho': 0.0,
                'vanna': 0.0,
                'volga': 0.0,
                'position_value': intrinsic_value * position.quantity,
                'remaining_days': 0
            }
        
        # 应用波动率倍数
        adjusted_volatility = position.volatility * volatility_multiplier
        
        # 计算该期权的Greeks
        greeks = self.bs_calculator.calculate_all_greeks(
            S=spot_price,
            K=position.strike,
            T=T,
            sigma=adjusted_volatility,
            option_type=position.option_type
        )
        
        # 乘以数量
        remaining_days = max(int((position.expiration_date - adjusted_date).days), 0)
        
        return {
            'delta': greeks['delta'] * position.quantity,
            'gamma': greeks['gamma'] * position.quantity,
            'theta': greeks['theta'] * position.quantity,
            'theta_daily': greeks['theta'] * position.quantity / 365,
            'vega': greeks['vega'] * position.quantity,
            'rho': greeks['rho'] * position.quantity,
            'vanna': greeks.get('vanna', 0.0) * position.quantity,
            'volga': greeks.get('volga', 0.0) * position.quantity,
            'position_value': greeks['price'] * position.quantity,
            'remaining_days': remaining_days
        }
    
    def calculate_smart_price_range(self, price_range_mode: str = "smart") -> tuple:
        """
        计算智能价格范围
        
        :param price_range_mode: 价格范围模式
            - "smart": 智能范围（基于当前价格和行权价）
            - "linear": 线性范围（当前价格*0.01到*100）
            - "log": 对数范围（使用对数分布）
            - "strike_based": 基于行权价范围
        :return: (spot_min, spot_max) 元组
        """
        if not self.positions:
            return (self.current_spot_price * 0.5, self.current_spot_price * 1.5)
        
        if price_range_mode == "smart":
            # 智能范围：基于当前价格和行权价
            strikes = [pos.strike for pos in self.positions]
            min_strike = min(strikes) if strikes else self.current_spot_price
            max_strike = max(strikes) if strikes else self.current_spot_price
            
            # 计算范围：min(当前价格*0.01, min(strikes)*0.1) 到 max(当前价格*10, max(strikes)*10)
            spot_min = min(self.current_spot_price * 0.01, min_strike * 0.1)
            spot_max = max(self.current_spot_price * 10, max_strike * 10)
            
            # 确保最小值不为0或负数
            spot_min = max(spot_min, 1.0)
            
        elif price_range_mode == "linear":
            # 线性范围：当前价格的0.01倍到100倍
            spot_min = self.current_spot_price * 0.01
            spot_max = self.current_spot_price * 100.0
            
        elif price_range_mode == "strike_based":
            # 基于行权价范围
            strikes = [pos.strike for pos in self.positions]
            if strikes:
                spot_min = min(strikes) * 0.1
                spot_max = max(strikes) * 10.0
            else:
                spot_min = self.current_spot_price * 0.5
                spot_max = self.current_spot_price * 1.5
        else:
            # 默认：智能范围
            return self.calculate_smart_price_range("smart")
        
        return (spot_min, spot_max)
    
    def greeks_vs_spot_price(self, spot_min: float = None, spot_max: float = None, 
                            num_points: int = 50, current_date: datetime = None,
                            price_range_mode: str = "smart", use_log_scale: bool = False,
                            volatility_multiplier: float = 1.0, time_days_offset: int = 0) -> pd.DataFrame:
        """
        组合Greeks vs 标的价格分析
        
        :param spot_min: 最低价格（如果为None，则使用price_range_mode自动计算）
        :param spot_max: 最高价格（如果为None，则使用price_range_mode自动计算）
        :param num_points: 价格点数
        :param current_date: 当前日期
        :param price_range_mode: 价格范围模式（"smart", "linear", "log", "strike_based"）
        :param use_log_scale: 是否使用对数分布点（适用于极端范围）
        :param volatility_multiplier: 波动率倍数（1.0表示无变化，1.1表示+10%，0.9表示-10%）
        :param time_days_offset: 时间偏移天数（0表示当前，正数表示未来）
        :return: DataFrame包含价格和组合Greeks
        """
        if not self.positions:
            return pd.DataFrame()
        
        # 设置价格范围
        if spot_min is None or spot_max is None:
            calculated_min, calculated_max = self.calculate_smart_price_range(price_range_mode)
            if spot_min is None:
                spot_min = calculated_min
            if spot_max is None:
                spot_max = calculated_max
        
        # 生成价格序列
        if use_log_scale:
            # 使用对数分布：适用于极端范围（0.01x到100x）
            # 确保spot_min > 0
            spot_min = max(spot_min, 1.0)
            spot_range = np.logspace(np.log10(spot_min), np.log10(spot_max), num_points)
        else:
            # 使用线性分布
            spot_range = np.linspace(spot_min, spot_max, num_points)
        
        # 计算每个价格点的组合Greeks
        results = []
        for spot in spot_range:
            greeks = self.calculate_portfolio_greeks(
                spot, 
                current_date,
                volatility_multiplier=volatility_multiplier,
                time_days_offset=time_days_offset
            )
            results.append({
                'spot_price': spot,
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'theta_daily': greeks['theta_daily'],
                'vega': greeks['vega'],
                'rho': greeks['rho'],
                'vanna': greeks.get('vanna', 0.0),
                'volga': greeks.get('volga', 0.0),
                'position_value': greeks['position_value']
            })
        
        df = pd.DataFrame(results)
        df['current_spot'] = self.current_spot_price
        
        return df
    
    def pnl_vs_spot_price(self, spot_min: float = None, spot_max: float = None, 
                         num_points: int = 50, current_date: datetime = None,
                         volatility_multiplier: float = 1.0, time_days_offset: int = 0,
                         price_range_mode: str = "smart", use_log_scale: bool = False) -> pd.DataFrame:
        """
        组合PnL vs 标的价格分析
        
        标准PnL计算：
        - 建仓成本 = Σ(entry_price × quantity)
        - PnL = 当前组合价值 - 建仓成本
        
        :param spot_min: 最低价格
        :param spot_max: 最高价格
        :param num_points: 价格点数
        :param current_date: 当前日期
        :param volatility_multiplier: 波动率倍数（1.0表示无变化，1.1表示+10%，0.9表示-10%）
        :param time_days_offset: 时间偏移天数（0表示当前，正数表示未来）
        :param price_range_mode: 价格范围模式（"smart", "linear", "log", "strike_based"）
        :param use_log_scale: 是否使用对数分布点（适用于极端范围）
        :return: DataFrame包含价格和PnL
        """
        if not self.positions:
            return pd.DataFrame()
        
        # 计算建仓成本（使用建仓时的标的价格，如果没有则使用当前价格）
        # 注意：为了准确计算建仓成本，应该使用建仓时的标的价格
        # 但为了简化，这里使用当前价格作为近似值
        cost_basis = self.calculate_cost_basis(self.current_spot_price)
        
        # 计算不同价格下的组合价值
        greeks_df = self.greeks_vs_spot_price(
            spot_min, spot_max, num_points, current_date,
            price_range_mode=price_range_mode,
            use_log_scale=use_log_scale,
            volatility_multiplier=volatility_multiplier,
            time_days_offset=time_days_offset
        )
        
        if greeks_df.empty:
            return pd.DataFrame()
        
        # 计算当前价格下的组合价值（用于显示）
        current_greeks = self.calculate_portfolio_greeks(
            self.current_spot_price, 
            current_date,
            volatility_multiplier=volatility_multiplier,
            time_days_offset=time_days_offset
        )
        current_value = current_greeks['position_value']
        
        # PnL = 当前组合价值 - 建仓成本（标准计算）
        greeks_df['pnl'] = greeks_df['position_value'] - cost_basis
        greeks_df['cost_basis'] = cost_basis  # 建仓成本
        greeks_df['current_value'] = current_value  # 当前价值
        
        return greeks_df
    
    def calculate_max_loss_at_expiration(self, spot_min: float = None, spot_max: float = None,
                                        num_points: int = 200, cost_basis: float = None) -> float:
        """
        计算到期时的最大亏损
        
        对于期权组合，最大亏损发生在到期时（T=0），此时期权价值等于内在价值。
        最大亏损 = min(到期时组合价值) - 建仓成本
        
        :param spot_min: 最低标的价格（如果None，使用当前价格的10%）
        :param spot_max: 最高标的价格（如果None，使用当前价格的300%）
        :param num_points: 价格点数
        :param cost_basis: 建仓成本（如果None，自动计算）
        :return: 最大亏损（负数表示亏损）
        """
        if not self.positions:
            return 0.0
        
        if cost_basis is None:
            cost_basis = self.calculate_cost_basis(self.current_spot_price)
        
        # 确定价格范围
        if spot_min is None:
            spot_min = self.current_spot_price * 0.1
        if spot_max is None:
            spot_max = self.current_spot_price * 3.0
        
        # 生成价格序列
        spot_prices = np.linspace(spot_min, spot_max, num_points)
        
        # 计算到期时（T=0）的组合价值
        expiration_values = []
        for spot_price in spot_prices:
            portfolio_value = 0.0
            for pos in self.positions:
                # 计算到期时的内在价值
                if pos.option_type.upper() == 'C':
                    # Call内在价值 = max(S - K, 0)
                    intrinsic_value = max(spot_price - pos.strike, 0.0)
                else:  # Put
                    # Put内在价值 = max(K - S, 0)
                    intrinsic_value = max(pos.strike - spot_price, 0.0)
                
                # 组合价值 = Σ(内在价值 × 数量)
                portfolio_value += intrinsic_value * pos.quantity
            
            expiration_values.append(portfolio_value)
        
        # 最大亏损 = 最小组合价值 - 建仓成本
        min_expiration_value = min(expiration_values)
        max_loss = min_expiration_value - cost_basis
        
        return max_loss
    
    def time_decay_analysis(self, days_range: Tuple[int, int] = None, 
                           num_points: int = 50, spot_price: float = None) -> pd.DataFrame:
        """
        时间衰减分析（组合价值随时间变化）
        
        :param days_range: 天数范围（min_days, max_days），默认从0到最远到期日
        :param num_points: 时间点数
        :param spot_price: 标的价格（如果None，使用current_spot_price）
        :return: DataFrame包含时间和组合Greeks
        """
        if not self.positions:
            return pd.DataFrame()
        
        if spot_price is None:
            spot_price = self.current_spot_price
        
        # 确定时间范围
        if days_range is None:
            max_days = max(pos.days_to_expiry() for pos in self.positions)
            days_range = (0, max_days)
        
        # 生成时间序列（从最远到期日到0）
        days_array = np.linspace(days_range[1], days_range[0], num_points)
        
        # 计算每个时间点的组合Greeks
        results = []
        current_date = datetime.now()
        
        for days in days_array:
            # 模拟未来日期
            future_date = current_date + timedelta(days=days_range[1] - days)
            greeks = self.calculate_portfolio_greeks(spot_price, future_date)
            
            results.append({
                'days_to_expiry': days,
                'date': future_date,
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'theta_daily': greeks['theta_daily'],
                'vega': greeks['vega'],
                'rho': greeks['rho'],
                'vanna': greeks.get('vanna', 0.0),
                'volga': greeks.get('volga', 0.0),
                'position_value': greeks['position_value']
            })
        
        return pd.DataFrame(results)
    
    def volatility_sensitivity_analysis(self, iv_change_range: Tuple[float, float] = (-0.5, 0.5),
                                        num_points: int = 50, spot_price: float = None,
                                        current_date: datetime = None) -> pd.DataFrame:
        """
        波动率敏感性分析（组合Greeks vs IV变化）
        
        :param iv_change_range: IV变化范围（-0.5表示-50%，0.5表示+50%）
        :param num_points: 波动率点数
        :param spot_price: 标的价格
        :param current_date: 当前日期
        :return: DataFrame包含IV变化和组合Greeks
        """
        if not self.positions:
            return pd.DataFrame()
        
        if spot_price is None:
            spot_price = self.current_spot_price
        
        # 生成IV变化序列
        iv_changes = np.linspace(iv_change_range[0], iv_change_range[1], num_points)
        
        # 保存原始波动率
        original_vols = [pos.volatility for pos in self.positions]
        
        results = []
        for iv_change in iv_changes:
            # 调整所有持仓的波动率
            for i, pos in enumerate(self.positions):
                pos.volatility = original_vols[i] * (1 + iv_change)
                pos.volatility = max(pos.volatility, 0.01)  # 确保至少1%
            
            # 计算调整后的Greeks
            greeks = self.calculate_portfolio_greeks(spot_price, current_date)
            
            results.append({
                'iv_change_percent': iv_change * 100,
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'vega': greeks['vega'],
                'rho': greeks['rho'],
                'vanna': greeks.get('vanna', 0.0),
                'volga': greeks.get('volga', 0.0),
                'position_value': greeks['position_value']
            })
        
        # 恢复原始波动率
        for i, pos in enumerate(self.positions):
            pos.volatility = original_vols[i]
        
        return pd.DataFrame(results)
    
    def load_strategy_template(self, strategy_name: str, current_spot: float = None):
        """
        加载预设策略模板
        
        :param strategy_name: 策略名称
        :param current_spot: 当前标的价格
        """
        if current_spot is None:
            current_spot = self.current_spot_price
        
        self.clear_positions()
        
        # 计算ATM行权价（取整到100的倍数）
        atm_strike = round(current_spot / 100) * 100
        
        # 策略模板定义
        templates = {
            'long_straddle': [
                # 买入跨式：ATM Call + ATM Put
                (atm_strike, 'C', 1),
                (atm_strike, 'P', 1)
            ],
            'short_straddle': [
                # 卖出跨式：卖出ATM Call + ATM Put
                (atm_strike, 'C', -1),
                (atm_strike, 'P', -1)
            ],
            'long_strangle': [
                # 买入宽跨式：OTM Call + OTM Put
                (atm_strike + 200, 'C', 1),
                (atm_strike - 200, 'P', 1)
            ],
            'short_strangle': [
                # 卖出宽跨式
                (atm_strike + 200, 'C', -1),
                (atm_strike - 200, 'P', -1)
            ],
            'bull_call_spread': [
                # 牛市价差：买入低行权价Call，卖出高行权价Call
                (atm_strike - 100, 'C', 1),
                (atm_strike + 100, 'C', -1)
            ],
            'bear_put_spread': [
                # 熊市价差：买入高行权价Put，卖出低行权价Put
                (atm_strike + 100, 'P', 1),
                (atm_strike - 100, 'P', -1)
            ],
            'iron_condor': [
                # 铁秃鹰
                (atm_strike - 300, 'P', 1),   # 买入远端Put
                (atm_strike - 100, 'P', -1),  # 卖出近端Put
                (atm_strike + 100, 'C', -1),  # 卖出近端Call
                (atm_strike + 300, 'C', 1)    # 买入远端Call
            ],
            'butterfly': [
                # 蝶式价差
                (atm_strike - 200, 'C', 1),
                (atm_strike, 'C', -2),
                (atm_strike + 200, 'C', 1)
            ],
            'call_calendar_spread': [
                # Call日历价差（需要不同到期日，这里简化处理）
                (atm_strike, 'C', -1),  # 卖出近月
                (atm_strike, 'C', 1)    # 买入远月
            ]
        }
        
        if strategy_name not in templates:
            raise ValueError(f"未知策略: {strategy_name}. 可用策略: {list(templates.keys())}")
        
        # 默认到期日：30天后
        default_expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 添加策略持仓
        for strike, option_type, quantity in templates[strategy_name]:
            # 计算entry_price（使用当前价格下的BS理论价格）
            T = (pd.to_datetime(default_expiry) - datetime.now()).days / 365.0
            if T > 0:
                entry_price = self.bs_calculator.calculate_option_price(
                    current_spot,
                    strike,
                    T,
                    1.0,  # 默认波动率1.0
                    option_type.lower()
                )
            else:
                entry_price = 0.0
            
            self.add_position(default_expiry, strike, option_type, quantity, volatility=1.0, entry_price=entry_price)
    
    def summary(self) -> Dict:
        """
        组合摘要信息
        
        :return: 摘要字典
        """
        if not self.positions:
            return {
                'total_positions': 0,
                'long_positions': 0,
                'short_positions': 0,
                'unique_strikes': 0,
                'unique_expirations': 0
            }
        
        df = self.get_positions_df()
        
        return {
            'total_positions': len(self.positions),
            'long_positions': len(df[df['quantity'] > 0]),
            'short_positions': len(df[df['quantity'] < 0]),
            'unique_strikes': df['strike'].nunique(),
            'unique_expirations': df['expiration_date'].nunique(),
            'net_quantity': df['quantity'].sum()
        }


if __name__ == "__main__":
    # 测试代码
    print("="*60)
    print("持仓组合分析器测试")
    print("="*60)
    
    # 创建分析器
    analyzer = PortfolioAnalyzer(risk_free_rate=0.05)
    analyzer.current_spot_price = 3000
    
    # 测试1: 添加单个持仓
    print("\n测试1: 添加单个持仓")
    print("-" * 60)
    analyzer.add_position('2025-12-30', 3000, 'C', 1, volatility=1.0)
    print(f"持仓列表:\n{analyzer.get_positions_df()}")
    
    # 测试2: 计算单个持仓的Greeks
    print("\n测试2: 计算单个持仓的Greeks")
    print("-" * 60)
    greeks = analyzer.calculate_portfolio_greeks()
    print(f"组合Greeks:")
    for key, value in greeks.items():
        print(f"  {key}: {value:.4f}")
    
    # 测试3: Long Straddle策略
    print("\n测试3: Long Straddle策略")
    print("-" * 60)
    analyzer.load_strategy_template('long_straddle', current_spot=3000)
    print(f"持仓列表:\n{analyzer.get_positions_df()}")
    greeks_straddle = analyzer.calculate_portfolio_greeks()
    print(f"\nLong Straddle Greeks:")
    print(f"  Delta: {greeks_straddle['delta']:.4f} (应接近0)")
    print(f"  Gamma: {greeks_straddle['gamma']:.6f} (应为正)")
    print(f"  Theta: {greeks_straddle['theta_daily']:.4f} (应为负)")
    print(f"  Vega: {greeks_straddle['vega']:.2f} (应为正)")
    
    # 测试4: Greeks vs 价格分析
    print("\n测试4: Greeks vs 价格分析")
    print("-" * 60)
    greeks_price_df = analyzer.greeks_vs_spot_price(num_points=10)
    print(f"生成 {len(greeks_price_df)} 个价格点")
    print(f"\n前5个价格点的Delta:")
    print(greeks_price_df[['spot_price', 'delta', 'gamma']].head())
    
    # 测试5: PnL分析
    print("\n测试5: PnL vs 价格分析")
    print("-" * 60)
    pnl_df = analyzer.pnl_vs_spot_price(num_points=10)
    print(f"当前持仓价值: {pnl_df['initial_value'].iloc[0]:.2f}")
    print(f"\n不同价格下的PnL:")
    print(pnl_df[['spot_price', 'pnl', 'position_value']].head())
    
    # 测试6: 时间衰减分析
    print("\n测试6: 时间衰减分析")
    print("-" * 60)
    time_df = analyzer.time_decay_analysis(num_points=10)
    print(f"生成 {len(time_df)} 个时间点")
    print(f"\n前5个时间点:")
    print(time_df[['days_to_expiry', 'position_value', 'theta_daily']].head())
    
    # 测试7: 波动率敏感性分析
    print("\n测试7: 波动率敏感性分析")
    print("-" * 60)
    vol_df = analyzer.volatility_sensitivity_analysis(num_points=10)
    print(f"生成 {len(vol_df)} 个波动率点")
    print(f"\n前5个波动率点:")
    print(vol_df[['iv_change_percent', 'vega', 'position_value']].head())
    
    print("\n" + "="*60)
    print("持仓组合分析器测试完成")
    print("="*60)

