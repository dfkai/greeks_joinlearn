"""
任务八：ETH期权数据完整性检查
检查数据库中是否完整下载了Deribit上所有ETH期权数据
"""

import pandas as pd
from typing import Dict, List, Set, Optional
from datetime import datetime
from .data_fetcher import OptionsChainFetcher
from src.core import OptionsDatabase
import logging

logger = logging.getLogger(__name__)


class DataCompletenessChecker:
    """数据完整性检查器"""
    
    def __init__(self, currency: str = "ETH", db_path: str = "options_data.duckdb"):
        """
        初始化数据完整性检查器
        
        :param currency: 货币类型，默认"ETH"
        :param db_path: 数据库文件路径
        """
        self.currency = currency
        self.fetcher = OptionsChainFetcher(currency=currency)
        self.db = OptionsDatabase(db_path=db_path)
    
    def get_api_instruments(self) -> List[Dict]:
        """
        从Deribit API获取所有ETH期权工具列表
        
        :return: 期权工具列表
        """
        try:
            logger.info(f"正在从Deribit API获取所有{self.currency}期权工具列表...")
            instruments = self.fetcher.get_all_instruments()
            logger.info(f"API返回 {len(instruments)} 个期权工具")
            return instruments
        except Exception as e:
            logger.error(f"获取API工具列表失败: {e}")
            return []
    
    def get_stored_instruments(self) -> List[str]:
        """
        从数据库查询已存储的期权工具名称列表
        
        :return: 工具名称列表
        """
        try:
            logger.info("正在从数据库查询已存储的期权工具列表...")
            instruments = self.db.get_all_stored_instruments()
            logger.info(f"数据库中有 {len(instruments)} 个期权工具")
            return instruments
        except Exception as e:
            logger.error(f"查询数据库工具列表失败: {e}")
            return []
    
    def compare_instruments(self, api_instruments: List[Dict], 
                           stored_instruments: List[str]) -> Dict:
        """
        对比API和数据库中的期权工具，找出缺失和过期的
        
        :param api_instruments: API返回的期权工具列表
        :param stored_instruments: 数据库中已存储的工具名称列表
        :return: 对比结果字典
        """
        # 提取API中的工具名称
        api_names = set()
        api_instruments_dict = {}
        for inst in api_instruments:
            name = inst.get('instrument_name')
            if name:
                api_names.add(name)
                api_instruments_dict[name] = inst
        
        # 数据库中的工具名称集合
        stored_names = set(stored_instruments)
        
        # 找出缺失的期权（API中有但数据库中没有）
        missing_names = api_names - stored_names
        
        # 找出过期的期权（数据库中有但API中已不存在）
        expired_names = stored_names - api_names
        
        # 计算覆盖率
        total_api = len(api_names)
        total_stored = len(stored_names)
        coverage_rate = (total_stored / total_api * 100) if total_api > 0 else 0
        
        result = {
            'api_total': total_api,
            'stored_total': total_stored,
            'missing_count': len(missing_names),
            'missing_names': sorted(list(missing_names)),
            'expired_count': len(expired_names),
            'expired_names': sorted(list(expired_names)),
            'coverage_rate': coverage_rate,
            'api_instruments_dict': api_instruments_dict
        }
        
        logger.info(f"对比完成: API总数={total_api}, 已存储={total_stored}, "
                   f"缺失={len(missing_names)}, 过期={len(expired_names)}, "
                   f"覆盖率={coverage_rate:.2f}%")
        
        return result
    
    def analyze_by_dimension(self, comparison_result: Dict) -> Dict:
        """
        按到期日、行权价、期权类型等维度统计缺失情况
        
        :param comparison_result: 对比结果字典
        :return: 按维度统计的结果
        """
        missing_names = comparison_result['missing_names']
        api_instruments_dict = comparison_result['api_instruments_dict']
        
        if not missing_names:
            return {
                'by_expiration': {},
                'by_strike_range': {},
                'by_option_type': {},
                'by_currency': {}
            }
        
        # 解析缺失的期权信息
        missing_data = []
        for name in missing_names:
            inst = api_instruments_dict.get(name, {})
            missing_data.append({
                'instrument_name': name,
                'expiration_timestamp': inst.get('expiration_timestamp'),
                'strike': inst.get('strike'),
                'option_type': inst.get('option_type'),
                'currency': inst.get('currency', self.currency)
            })
        
        df_missing = pd.DataFrame(missing_data)
        
        # 按到期日统计
        by_expiration = {}
        if 'expiration_timestamp' in df_missing.columns and not df_missing.empty:
            df_missing['expiration_date'] = pd.to_datetime(df_missing['expiration_timestamp'], unit='ms', errors='coerce')
            exp_counts = df_missing['expiration_date'].dt.date.value_counts().to_dict()
            by_expiration = {str(k): int(v) for k, v in exp_counts.items()}
        
        # 按行权价范围统计
        by_strike_range = {}
        if 'strike' in df_missing.columns and not df_missing.empty:
            df_missing['strike'] = pd.to_numeric(df_missing['strike'], errors='coerce')
            strike_ranges = {
                '0-1000': len(df_missing[(df_missing['strike'] >= 0) & (df_missing['strike'] < 1000)]),
                '1000-2000': len(df_missing[(df_missing['strike'] >= 1000) & (df_missing['strike'] < 2000)]),
                '2000-3000': len(df_missing[(df_missing['strike'] >= 2000) & (df_missing['strike'] < 3000)]),
                '3000-4000': len(df_missing[(df_missing['strike'] >= 3000) & (df_missing['strike'] < 4000)]),
                '4000+': len(df_missing[df_missing['strike'] >= 4000])
            }
            by_strike_range = {k: v for k, v in strike_ranges.items() if v > 0}
        
        # 按期权类型统计
        by_option_type = {}
        if 'option_type' in df_missing.columns and not df_missing.empty:
            type_counts = df_missing['option_type'].value_counts().to_dict()
            by_option_type = {str(k): int(v) for k, v in type_counts.items()}
        
        # 按货币类型统计
        by_currency = {}
        if 'currency' in df_missing.columns and not df_missing.empty:
            currency_counts = df_missing['currency'].value_counts().to_dict()
            by_currency = {str(k): int(v) for k, v in currency_counts.items()}
        
        return {
            'by_expiration': by_expiration,
            'by_strike_range': by_strike_range,
            'by_option_type': by_option_type,
            'by_currency': by_currency
        }
    
    def generate_report(self, comparison_result: Dict, 
                       dimension_analysis: Dict) -> Dict:
        """
        生成数据完整性报告
        
        :param comparison_result: 对比结果字典
        :param dimension_analysis: 按维度统计的结果
        :return: 完整报告字典
        """
        report = {
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'currency': self.currency,
            'summary': {
                'api_total': comparison_result['api_total'],
                'stored_total': comparison_result['stored_total'],
                'missing_count': comparison_result['missing_count'],
                'expired_count': comparison_result['expired_count'],
                'coverage_rate': round(comparison_result['coverage_rate'], 2)
            },
            'missing_instruments': comparison_result['missing_names'][:100],  # 限制显示前100个
            'expired_instruments': comparison_result['expired_names'][:100],  # 限制显示前100个
            'dimension_analysis': dimension_analysis,
            'is_complete': comparison_result['missing_count'] == 0
        }
        
        return report
    
    def check_completeness(self) -> Dict:
        """
        执行完整的数据完整性检查流程
        
        :return: 完整性报告字典
        """
        logger.info("="*60)
        logger.info("开始数据完整性检查")
        logger.info("="*60)
        
        # 1. 获取API工具列表
        api_instruments = self.get_api_instruments()
        if not api_instruments:
            logger.warning("无法获取API工具列表，检查终止")
            return {
                'error': '无法获取API工具列表',
                'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 2. 获取数据库工具列表
        stored_instruments = self.get_stored_instruments()
        
        # 3. 对比
        comparison_result = self.compare_instruments(api_instruments, stored_instruments)
        
        # 4. 按维度分析
        dimension_analysis = self.analyze_by_dimension(comparison_result)
        
        # 5. 生成报告
        report = self.generate_report(comparison_result, dimension_analysis)
        
        logger.info("="*60)
        logger.info("数据完整性检查完成")
        logger.info("="*60)
        
        return report
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    checker = DataCompletenessChecker(currency="ETH", db_path="options_data.duckdb")
    
    try:
        report = checker.check_completeness()
        
        print("\n" + "="*60)
        print("数据完整性报告")
        print("="*60)
        print(f"\n检查时间: {report.get('check_time')}")
        print(f"货币类型: {report.get('currency')}")
        
        summary = report.get('summary', {})
        print(f"\n【摘要】")
        print(f"  API总数: {summary.get('api_total', 0)}")
        print(f"  已存储: {summary.get('stored_total', 0)}")
        print(f"  缺失数量: {summary.get('missing_count', 0)}")
        print(f"  过期数量: {summary.get('expired_count', 0)}")
        print(f"  覆盖率: {summary.get('coverage_rate', 0)}%")
        
        if summary.get('missing_count', 0) > 0:
            print(f"\n【缺失的期权（前10个）】")
            missing = report.get('missing_instruments', [])[:10]
            for i, name in enumerate(missing, 1):
                print(f"  {i}. {name}")
        
        if summary.get('expired_count', 0) > 0:
            print(f"\n【过期的期权（前10个）】")
            expired = report.get('expired_instruments', [])[:10]
            for i, name in enumerate(expired, 1):
                print(f"  {i}. {name}")
        
        dim_analysis = report.get('dimension_analysis', {})
        if dim_analysis.get('by_expiration'):
            print(f"\n【按到期日统计缺失情况】")
            for exp_date, count in list(dim_analysis['by_expiration'].items())[:5]:
                print(f"  {exp_date}: {count}个")
        
        if dim_analysis.get('by_option_type'):
            print(f"\n【按期权类型统计缺失情况】")
            for opt_type, count in dim_analysis['by_option_type'].items():
                print(f"  {opt_type}: {count}个")
        
    finally:
        checker.close()

