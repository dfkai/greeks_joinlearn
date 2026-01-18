"""
任务二：HTTP方式获取期权链数据
实现批量获取期权链数据和Greeks数据
"""

import pandas as pd
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from api.Deribit_HTTP import DeribitAPI
from credentials import client_id, client_secret


class OptionsChainFetcher:
    """期权链数据获取器"""
    
    def __init__(self, currency="ETH", max_workers=10):
        """
        初始化期权链数据获取器
        
        :param currency: 货币类型，默认"ETH"
        :param max_workers: 并发线程数，默认10
        """
        self.api = DeribitAPI(client_id, client_secret)
        self.currency = currency
        self.max_workers = max_workers
        
    def get_all_instruments(self) -> List[Dict]:
        """
        获取所有期权工具列表
        
        :return: 期权工具列表
        """
        data = self.api.get_instruments(currency=self.currency, kind="option")
        if data and 'result' in data:
            return data['result']
        return []
    
    def parse_instrument_name(self, instrument_name: str) -> Dict:
        """
        解析期权工具名称，提取到期日、行权价、类型等信息
        
        :param instrument_name: 工具名称，例如 "ETH-30NOV25-2600-C"
        :return: 解析后的信息字典
        """
        parts = instrument_name.split('-')
        if len(parts) >= 4:
            currency = parts[0]
            date_str = parts[1]  # 例如 "30NOV25"
            strike = int(parts[2])
            option_type = parts[3]  # "C" 或 "P"
            
            # 解析日期
            try:
                expiration_date = pd.to_datetime(date_str, format='%d%b%y')
            except:
                expiration_date = None
            
            return {
                'currency': currency,
                'date_str': date_str,
                'expiration_date': expiration_date,
                'strike': strike,
                'option_type': option_type,
                'instrument_name': instrument_name
            }
        return {}
    
    def get_order_book_with_retry(self, instrument_name: str, max_retries=3, retry_delay=1) -> Optional[Dict]:
        """
        获取订单簿数据（包含Greeks），带重试机制
        
        :param instrument_name: 工具名称
        :param max_retries: 最大重试次数
        :param retry_delay: 重试延迟（秒）
        :return: 订单簿数据
        """
        for attempt in range(max_retries):
            try:
                data = self.api.get_order_book(instrument_name)
                if data and 'result' in data:
                    return data['result']
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"获取 {instrument_name} 失败，已重试 {max_retries} 次: {e}")
        return None
    
    def fetch_greeks_batch(self, instrument_names: List[str]) -> List[Dict]:
        """
        批量获取Greeks数据
        
        :param instrument_names: 工具名称列表
        :return: Greeks数据列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_name = {
                executor.submit(self.get_order_book_with_retry, name): name 
                for name in instrument_names
            }
            
            for future in as_completed(future_to_name):
                instrument_name = future_to_name[future]
                try:
                    order_book = future.result()
                    if order_book and 'greeks' in order_book:
                        # 合并基础信息和Greeks数据
                        parsed_info = self.parse_instrument_name(instrument_name)
                        
                        # 提取stats中的volume信息（如果存在）
                        stats = order_book.get('stats', {})
                        volume = None
                        if isinstance(stats, dict):
                            # stats可能包含volume或volume_usd
                            volume = stats.get('volume') or stats.get('volume_usd')
                        
                        # 如果stats中没有，尝试从order_book顶层获取
                        if volume is None:
                            volume = order_book.get('volume')
                        
                        greeks_data = {
                            **parsed_info,
                            **order_book.get('greeks', {}),
                            'mark_price': order_book.get('mark_price'),
                            'mark_iv': order_book.get('mark_iv'),
                            'underlying_price': order_book.get('underlying_price'),
                            'open_interest': order_book.get('open_interest'),
                            'best_bid_price': order_book.get('best_bid_price'),
                            'best_ask_price': order_book.get('best_ask_price'),
                            'volume': volume,  # 添加volume字段
                        }
                        results.append(greeks_data)
                except Exception as e:
                    print(f"处理 {instrument_name} 时出错: {e}")
        
        return results
    
    def get_options_chain_all_expirations(self) -> pd.DataFrame:
        """
        获取所有到期日的期权链数据（包含Greeks）
        
        :return: 包含所有期权数据的DataFrame
        """
        print("步骤1: 获取所有期权工具列表...")
        instruments = self.get_all_instruments()
        print(f"找到 {len(instruments)} 个期权工具")
        
        if not instruments:
            return pd.DataFrame()
        
        instrument_names = [inst.get('instrument_name') for inst in instruments if inst.get('instrument_name')]
        
        print(f"步骤2: 批量获取 {len(instrument_names)} 个期权的Greeks数据...")
        print(f"使用 {self.max_workers} 个并发线程")
        
        greeks_data = self.fetch_greeks_batch(instrument_names)
        
        print(f"成功获取 {len(greeks_data)} 个期权的Greeks数据")
        
        # 转换为DataFrame
        df = pd.DataFrame(greeks_data)
        
        if not df.empty:
            # 确保日期列是datetime类型
            if 'expiration_date' in df.columns:
                df['expiration_date'] = pd.to_datetime(df['expiration_date'])
            
            # 按到期日和行权价排序
            df = df.sort_values(['expiration_date', 'strike', 'option_type'])
        
        return df
    
    def get_options_chain_by_expiration(self, expiration_date: pd.Timestamp) -> pd.DataFrame:
        """
        获取指定到期日的期权链数据
        
        :param expiration_date: 到期日期
        :return: 包含指定到期日期权数据的DataFrame
        """
        # 先获取所有数据
        df_all = self.get_options_chain_all_expirations()
        
        if df_all.empty:
            return pd.DataFrame()
        
        # 筛选指定到期日
        if 'expiration_date' in df_all.columns:
            df_filtered = df_all[df_all['expiration_date'].dt.date == expiration_date.date()].copy()
            return df_filtered
        
        return pd.DataFrame()
    
    def get_options_chain_summary(self) -> pd.DataFrame:
        """
        快速获取期权链摘要（不包含Greeks，但速度更快）
        
        :return: 期权链摘要DataFrame
        """
        print("获取期权链摘要（快速模式，不包含Greeks）...")
        data = self.api.get_book_summary_by_currency(currency=self.currency, kind="option")
        
        if not data or 'result' not in data:
            return pd.DataFrame()
        
        summaries = data['result']
        df = pd.DataFrame(summaries)
        
        # 字段映射：API返回的字段名 -> 数据库期望的字段名
        # API返回: bid_price, ask_price -> 数据库期望: best_bid_price, best_ask_price
        field_mapping = {
            'bid_price': 'best_bid_price',
            'ask_price': 'best_ask_price',
        }
        
        # 重命名字段
        df.rename(columns=field_mapping, inplace=True)
        
        # 确保volume字段存在（如果API返回了volume）
        # volume字段可能为0或None，这是正常的（表示该期权没有成交量）
        if 'volume' not in df.columns:
            print("警告: API返回数据中未找到volume字段")
            df['volume'] = None
        else:
            # 确保volume是数值类型
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # 可选：添加volume_usd字段（如果API返回了）
        if 'volume_usd' in df.columns:
            df['volume_usd'] = pd.to_numeric(df['volume_usd'], errors='coerce')
        
        # 解析instrument_name提取信息
        if 'instrument_name' in df.columns:
            parsed = df['instrument_name'].apply(self.parse_instrument_name)
            parsed_df = pd.DataFrame(parsed.tolist())
            df = pd.concat([df, parsed_df], axis=1)
        
        # 解析underlying_index提取到期日
        if 'underlying_index' in df.columns:
            df['date_str_from_index'] = df['underlying_index'].str.extract(r'(\d{2}[A-Z]{3}\d{2})')
            df['expiration_date'] = pd.to_datetime(df['date_str_from_index'], format='%d%b%y', errors='coerce')
        
        # 数据质量检查：记录volume字段的统计信息
        if 'volume' in df.columns:
            volume_stats = {
                'total': len(df),
                'non_null': df['volume'].notna().sum(),
                'non_zero': (df['volume'] > 0).sum(),
                'null_count': df['volume'].isna().sum(),
                'zero_count': (df['volume'] == 0).sum()
            }
            print(f"成交量数据统计: 总计={volume_stats['total']}, "
                  f"非空={volume_stats['non_null']}, "
                  f"非零={volume_stats['non_zero']}, "
                  f"空值={volume_stats['null_count']}, "
                  f"零值={volume_stats['zero_count']}")
        
        return df


if __name__ == "__main__":
    # 测试代码
    fetcher = OptionsChainFetcher(currency="ETH", max_workers=10)
    
    # 测试1: 获取快速摘要
    print("\n" + "="*60)
    print("测试1: 获取期权链摘要（快速）")
    print("="*60)
    df_summary = fetcher.get_options_chain_summary()
    print(f"\n获取到 {len(df_summary)} 条数据")
    if not df_summary.empty:
        print("\n前5条数据:")
        print(df_summary[['instrument_name', 'expiration_date', 'strike', 'option_type', 'mark_price', 'mark_iv']].head())
    
    # 测试2: 获取少量期权的完整Greeks数据（测试用）
    print("\n" + "="*60)
    print("测试2: 获取前5个期权的完整Greeks数据")
    print("="*60)
    instruments = fetcher.get_all_instruments()
    if instruments:
        test_instruments = [inst['instrument_name'] for inst in instruments[:5]]
        greeks_data = fetcher.fetch_greeks_batch(test_instruments)
        df_greeks = pd.DataFrame(greeks_data)
        if not df_greeks.empty:
            print(f"\n获取到 {len(df_greeks)} 条Greeks数据")
            print("\nGreeks数据示例:")
            print(df_greeks[['instrument_name', 'expiration_date', 'strike', 'option_type', 
                           'delta', 'gamma', 'theta', 'vega', 'mark_price', 'mark_iv']].head())

