"""
任务四：数据采集与存储流程
整合数据获取和数据库存储
"""

import pandas as pd
from .data_fetcher import OptionsChainFetcher
from src.core import OptionsDatabase
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集器 - 整合数据获取和存储"""
    
    def __init__(self, currency="ETH", db_path="options_data.duckdb", max_workers=10):
        """
        初始化数据采集器
        
        :param currency: 货币类型
        :param db_path: 数据库路径
        :param max_workers: 并发线程数
        """
        self.fetcher = OptionsChainFetcher(currency=currency, max_workers=max_workers)
        self.db = OptionsDatabase(db_path=db_path)
        self.currency = currency
        logger.info(f"数据采集器初始化完成: currency={currency}, db_path={db_path}")
    
    def collect_summary_data(self, replace: bool = False, clear_all: bool = False):
        """
        采集期权链摘要数据（快速，不包含Greeks）
        
        :param replace: 是否替换已存在的数据（仅替换匹配的记录）
        :param clear_all: 是否清空所有旧数据再插入（完全刷新，推荐用于快照模式）
        """
        logger.info("开始采集期权链摘要数据...")
        try:
            df = self.fetcher.get_options_chain_summary()
            if not df.empty:
                self.db.insert_options_chain(df, replace=replace, clear_all=clear_all)
                logger.info(f"成功采集并存储 {len(df)} 条摘要数据")
                
                # 数据质量检查
                quality_stats = self.db.check_volume_data_quality()
                logger.info(f"成交量数据质量: 总计={quality_stats['total_count']}, "
                          f"非空={quality_stats['non_null_count']} ({quality_stats['completeness_pct']:.2f}%), "
                          f"非零={quality_stats['non_zero_count']} ({quality_stats['non_zero_pct']:.2f}%)")
                
                if quality_stats['completeness_pct'] < 50:
                    logger.warning(f"警告: 成交量数据完整性较低 ({quality_stats['completeness_pct']:.2f}%)")
                
                return len(df)
            else:
                logger.warning("未获取到数据")
                return 0
        except Exception as e:
            logger.error(f"采集摘要数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    def collect_greeks_data(self, limit: int = None, replace: bool = False, clear_all: bool = False):
        """
        采集Greeks数据（较慢，但包含完整Greeks信息）
        
        :param limit: 限制采集数量（None表示全部）
        :param replace: 是否替换已存在的数据（仅替换匹配的记录）
        :param clear_all: 是否清空所有旧数据再插入（完全刷新，推荐用于快照模式）
        """
        logger.info("开始采集Greeks数据...")
        try:
            # 获取所有工具列表
            instruments = self.fetcher.get_all_instruments()
            if not instruments:
                logger.warning("未获取到工具列表")
                return 0
            
            # 如果有限制，只取前N个
            if limit:
                instruments = instruments[:limit]
                logger.info(f"限制采集数量: {limit}")
            
            instrument_names = [inst['instrument_name'] for inst in instruments]
            logger.info(f"开始批量获取 {len(instrument_names)} 个期权的Greeks数据...")
            
            # 批量获取Greeks数据
            greeks_data = self.fetcher.fetch_greeks_batch(instrument_names)
            
            if greeks_data:
                df = pd.DataFrame(greeks_data)
                self.db.insert_options_with_greeks(df, replace=replace, clear_all=clear_all)
                logger.info(f"成功采集并存储 {len(df)} 条Greeks数据")
                return len(df)
            else:
                logger.warning("未获取到Greeks数据")
                return 0
        except Exception as e:
            logger.error(f"采集Greeks数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    def collect_full_data(self, greeks_limit: int = None, replace: bool = False, clear_all: bool = False):
        """
        采集完整数据（摘要 + Greeks）
        
        :param greeks_limit: Greeks数据采集限制（None表示全部）
        :param replace: 是否替换已存在的数据（仅替换匹配的记录）
        :param clear_all: 是否清空所有旧数据再插入（完全刷新，推荐用于快照模式）
        
        注意：如果 clear_all=True，会先清空所有数据，然后插入新数据。
        这适用于快照模式，每次采集都是最新时刻的数据，不需要历史数据。
        """
        logger.info("="*60)
        logger.info("开始完整数据采集流程")
        if clear_all:
            logger.info("模式: 完全刷新（清空所有旧数据）")
        logger.info("="*60)
        
        # 1. 先采集摘要数据（快速）
        # 如果是clear_all模式，只在第一次调用时清空
        summary_count = self.collect_summary_data(replace=replace, clear_all=clear_all)
        
        # 2. 再采集Greeks数据（较慢）
        # 如果clear_all=True，第二次调用时不再清空（因为已经在第一次清空了）
        greeks_count = self.collect_greeks_data(limit=greeks_limit, replace=replace, clear_all=False)
        
        # 3. 显示统计信息
        stats = self.db.get_statistics()
        logger.info("\n数据库统计信息:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\n数据采集完成")
        return summary_count, greeks_count
    
    def get_data_by_expiration(self, expiration_date: pd.Timestamp) -> pd.DataFrame:
        """根据到期日获取数据"""
        return self.db.get_options_by_expiration(expiration_date)
    
    def get_data_by_strike_range(self, min_strike: float, max_strike: float, 
                                 expiration_date: pd.Timestamp = None) -> pd.DataFrame:
        """根据行权价范围获取数据"""
        return self.db.get_options_by_strike_range(min_strike, max_strike, expiration_date)
    
    def get_all_expiration_dates(self):
        """获取所有到期日"""
        return self.db.get_all_expiration_dates()
    
    def check_data_quality(self):
        """
        检查数据质量并返回统计信息
        
        :return: 数据质量统计字典
        """
        return self.db.check_volume_data_quality()
    
    def get_missing_volume_data(self):
        """
        获取缺失成交量数据的期权列表
        
        :return: 缺失成交量数据的期权DataFrame
        """
        return self.db.get_instruments_without_volume()
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    # 测试代码
    collector = DataCollector(currency="ETH", db_path="test_options.duckdb", max_workers=5)
    
    try:
        # 测试1: 采集摘要数据
        print("\n" + "="*60)
        print("测试1: 采集摘要数据（快速）")
        print("="*60)
        summary_count = collector.collect_summary_data(replace=True)
        print(f"采集了 {summary_count} 条摘要数据")
        
        # 测试2: 采集少量Greeks数据
        print("\n" + "="*60)
        print("测试2: 采集Greeks数据（前10个）")
        print("="*60)
        greeks_count = collector.collect_greeks_data(limit=10, replace=True)
        print(f"采集了 {greeks_count} 条Greeks数据")
        
        # 测试3: 查询数据
        print("\n" + "="*60)
        print("测试3: 查询数据")
        print("="*60)
        exp_dates = collector.get_all_expiration_dates()
        print(f"找到 {len(exp_dates)} 个到期日")
        if exp_dates:
            test_date = exp_dates[0]
            df = collector.get_data_by_expiration(test_date)
            print(f"到期日 {test_date.date()} 的数据: {len(df)} 条")
            if not df.empty:
                print("\n数据示例:")
                print(df[['instrument_name', 'strike', 'option_type', 'delta', 'gamma', 'mark_price']].head())
        
    finally:
        collector.close()

