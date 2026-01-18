"""
任务三：数据库设计与实现
使用DuckDB存储期权链数据和Greeks数据
"""

import duckdb
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path


class OptionsDatabase:
    """期权数据数据库管理类"""
    
    def __init__(self, db_path: str = "options_data.duckdb"):
        """
        初始化数据库
        
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据表"""
        # 期权链数据表（使用ROWID作为主键，自动生成）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS options_chain (
                instrument_name VARCHAR NOT NULL,
                currency VARCHAR,
                expiration_date TIMESTAMP,
                strike DECIMAL(18, 2),
                option_type VARCHAR(1),
                mark_price DECIMAL(18, 8),
                mark_iv DECIMAL(10, 4),
                underlying_price DECIMAL(18, 8),
                open_interest DECIMAL(18, 8),
                best_bid_price DECIMAL(18, 8),
                best_ask_price DECIMAL(18, 8),
                volume DECIMAL(18, 8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Greeks数据表（不使用外键约束，简化设计）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS options_greeks (
                instrument_name VARCHAR NOT NULL,
                delta DECIMAL(18, 8),
                gamma DECIMAL(18, 8),
                theta DECIMAL(18, 8),
                vega DECIMAL(18, 8),
                rho DECIMAL(18, 8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 持仓组合表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                portfolio_id INTEGER PRIMARY KEY,
                portfolio_name VARCHAR NOT NULL,
                description VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 持仓组合明细表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                position_id INTEGER PRIMARY KEY,
                portfolio_id INTEGER NOT NULL,
                instrument_name VARCHAR NOT NULL,
                quantity DECIMAL(18, 4),
                entry_price DECIMAL(18, 8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # DuckDB会自动优化查询，不需要显式创建索引
    
    def insert_options_chain(self, df: pd.DataFrame, replace: bool = False, clear_all: bool = False):
        """
        插入期权链数据
        
        :param df: 包含期权链数据的DataFrame
        :param replace: 是否替换已存在的数据（仅替换匹配的记录）
        :param clear_all: 是否清空所有旧数据再插入（完全刷新）
        """
        # 如果clear_all=True，先清空所有数据
        if clear_all:
            self.conn.execute("DELETE FROM options_chain")
        if df.empty:
            return
        
        # 准备数据列映射
        column_mapping = {
            'instrument_name': 'instrument_name',
            'currency': 'currency',
            'expiration_date': 'expiration_date',
            'strike': 'strike',
            'option_type': 'option_type',
            'mark_price': 'mark_price',
            'mark_iv': 'mark_iv',
            'underlying_price': 'underlying_price',
            'open_interest': 'open_interest',
            'best_bid_price': 'best_bid_price',
            'best_ask_price': 'best_ask_price',
            'volume': 'volume'
        }
        
        # 选择存在的列
        available_cols = {k: v for k, v in column_mapping.items() if v in df.columns}
        
        if not available_cols:
            print("警告: DataFrame中没有可用的列")
            return
        
        # 准备插入的数据 - 直接使用DataFrame，重命名列
        insert_df = df[list(available_cols.values())].copy()
        insert_df.rename(columns={v: k for k, v in available_cols.items()}, inplace=True)
        
        # 确保日期格式正确
        if 'expiration_date' in insert_df.columns:
            insert_df['expiration_date'] = pd.to_datetime(insert_df['expiration_date'])
        
        # 确保volume字段是数值类型，None值保持为None（数据库允许NULL）
        if 'volume' in insert_df.columns:
            insert_df['volume'] = pd.to_numeric(insert_df['volume'], errors='coerce')
        
        # 确保其他数值字段也是正确的类型
        numeric_fields = ['mark_price', 'mark_iv', 'underlying_price', 'open_interest', 
                         'best_bid_price', 'best_ask_price', 'strike']
        for field in numeric_fields:
            if field in insert_df.columns:
                insert_df[field] = pd.to_numeric(insert_df[field], errors='coerce')
        
        # 添加时间戳
        insert_df['created_at'] = datetime.now()
        insert_df['updated_at'] = datetime.now()
        
        # 确保列的顺序和表结构一致
        table_columns = ['instrument_name', 'currency', 'expiration_date', 'strike', 'option_type',
                        'mark_price', 'mark_iv', 'underlying_price', 'open_interest',
                        'best_bid_price', 'best_ask_price', 'volume', 'created_at', 'updated_at']
        
        # 只选择存在的列，并按表结构顺序排列
        final_columns = [col for col in table_columns if col in insert_df.columns]
        insert_df = insert_df[final_columns]
        
        if replace and not insert_df.empty:
            # 先注册临时表
            self.conn.register('temp_insert_df', insert_df)
            # 删除已存在的数据
            self.conn.execute("DELETE FROM options_chain WHERE instrument_name IN (SELECT instrument_name FROM temp_insert_df)")
            self.conn.unregister('temp_insert_df')
        
        # 插入数据（DuckDB使用register方法）
        # 只插入存在的列（不包含id，让数据库自动生成）
        if not insert_df.empty:
            self.conn.register('temp_insert_df', insert_df)
            columns_str = ', '.join(final_columns)
            # 使用INSERT INTO ... SELECT，id会自动生成
            self.conn.execute(f"INSERT INTO options_chain ({columns_str}) SELECT {columns_str} FROM temp_insert_df")
            self.conn.unregister('temp_insert_df')
        
        print(f"成功插入 {len(insert_df)} 条期权链数据")
    
    def insert_greeks(self, df: pd.DataFrame, replace: bool = False, clear_all: bool = False):
        """
        插入Greeks数据
        
        :param df: 包含Greeks数据的DataFrame
        :param replace: 是否替换已存在的数据（仅替换匹配的记录）
        :param clear_all: 是否清空所有旧数据再插入（完全刷新）
        """
        # 如果clear_all=True，先清空所有数据
        if clear_all:
            self.conn.execute("DELETE FROM options_greeks")
        if df.empty:
            return
        
        # 准备数据列
        greeks_cols = ['instrument_name', 'delta', 'gamma', 'theta', 'vega', 'rho']
        available_cols = [col for col in greeks_cols if col in df.columns]
        
        if 'instrument_name' not in available_cols:
            print("警告: DataFrame中缺少instrument_name列")
            return
        
        insert_df = df[available_cols].copy()
        insert_df['created_at'] = datetime.now()
        insert_df['updated_at'] = datetime.now()
        
        if replace:
            # 删除旧数据
            self.conn.register('temp_insert_df', insert_df)
            self.conn.execute("DELETE FROM options_greeks WHERE instrument_name IN (SELECT instrument_name FROM temp_insert_df)")
            self.conn.unregister('temp_insert_df')
        
        # 插入数据
        self.conn.register('temp_insert_df', insert_df)
        self.conn.execute("INSERT INTO options_greeks SELECT * FROM temp_insert_df")
        self.conn.unregister('temp_insert_df')
        
        print(f"成功插入 {len(insert_df)} 条Greeks数据")
    
    def clear_all_data(self):
        """
        清空所有期权数据（用于完全刷新数据）
        清空 options_chain 和 options_greeks 表
        """
        self.conn.execute("DELETE FROM options_chain")
        self.conn.execute("DELETE FROM options_greeks")
        print("已清空所有期权数据")
    
    def insert_options_with_greeks(self, df: pd.DataFrame, replace: bool = False, clear_all: bool = False):
        """
        同时插入期权链数据和Greeks数据
        
        :param df: 包含完整数据的DataFrame（包含期权链和Greeks）
        :param replace: 是否替换已存在的数据（仅替换匹配的记录）
        :param clear_all: 是否清空所有旧数据再插入（完全刷新）
        """
        # 如果clear_all=True，先清空所有数据
        if clear_all:
            self.clear_all_data()
        
        # 分离期权链数据和Greeks数据
        chain_cols = ['instrument_name', 'currency', 'expiration_date', 'strike', 'option_type',
                     'mark_price', 'mark_iv', 'underlying_price', 'open_interest',
                     'best_bid_price', 'best_ask_price', 'volume']
        
        greeks_cols = ['instrument_name', 'delta', 'gamma', 'theta', 'vega', 'rho']
        
        chain_df = df[[col for col in chain_cols if col in df.columns]].copy()
        greeks_df = df[[col for col in greeks_cols if col in df.columns]].copy()
        
        # 如果clear_all=True，replace参数不再需要（因为已经清空了）
        self.insert_options_chain(chain_df, replace=replace if not clear_all else False)
        self.insert_greeks(greeks_df, replace=replace if not clear_all else False)
    
    def get_options_by_expiration(self, expiration_date: pd.Timestamp) -> pd.DataFrame:
        """
        根据到期日查询期权数据
        
        :param expiration_date: 到期日期
        :return: 期权数据DataFrame
        """
        query = """
            SELECT oc.*, og.delta, og.gamma, og.theta, og.vega, og.rho
            FROM options_chain oc
            LEFT JOIN options_greeks og ON oc.instrument_name = og.instrument_name
            WHERE DATE(oc.expiration_date) = ?
            ORDER BY oc.strike, oc.option_type
        """
        return self.conn.execute(query, [expiration_date.date()]).df()
    
    def get_options_by_strike_range(self, min_strike: float, max_strike: float, 
                                   expiration_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
        """
        根据行权价范围查询期权数据
        
        :param min_strike: 最小行权价
        :param max_strike: 最大行权价
        :param expiration_date: 可选的到期日筛选
        :return: 期权数据DataFrame
        """
        query = """
            SELECT oc.*, og.delta, og.gamma, og.theta, og.vega, og.rho
            FROM options_chain oc
            LEFT JOIN options_greeks og ON oc.instrument_name = og.instrument_name
            WHERE oc.strike >= ? AND oc.strike <= ?
        """
        params = [min_strike, max_strike]
        
        if expiration_date:
            query += " AND DATE(oc.expiration_date) = ?"
            params.append(expiration_date.date())
        
        query += " ORDER BY oc.expiration_date, oc.strike, oc.option_type"
        
        return self.conn.execute(query, params).df()
    
    def get_latest_options_chain(self, limit: int = 1000) -> pd.DataFrame:
        """
        获取最新的期权链数据
        
        :param limit: 返回记录数限制
        :return: 期权数据DataFrame
        """
        query = """
            SELECT oc.*, og.delta, og.gamma, og.theta, og.vega, og.rho
            FROM options_chain oc
            LEFT JOIN options_greeks og ON oc.instrument_name = og.instrument_name
            ORDER BY oc.updated_at DESC
            LIMIT ?
        """
        return self.conn.execute(query, [limit]).df()
    
    def get_all_options_chain(self) -> pd.DataFrame:
        """
        获取所有期权链历史数据（用于时序分析）
        按到期日排序，确保包含所有历史数据
        
        :return: 期权数据DataFrame（包含所有历史记录）
        """
        query = """
            SELECT oc.*, og.delta, og.gamma, og.theta, og.vega, og.rho
            FROM options_chain oc
            LEFT JOIN options_greeks og ON oc.instrument_name = og.instrument_name
            ORDER BY oc.expiration_date, oc.strike, oc.option_type, oc.updated_at
        """
        return self.conn.execute(query).df()
    
    def get_all_expiration_dates(self) -> List[pd.Timestamp]:
        """
        获取所有唯一的到期日
        
        :return: 到期日列表
        """
        query = "SELECT DISTINCT expiration_date FROM options_chain ORDER BY expiration_date"
        df = self.conn.execute(query).df()
        if df.empty:
            return []
        return pd.to_datetime(df['expiration_date']).tolist()
    
    def get_all_stored_instruments(self) -> List[str]:
        """
        获取数据库中所有已存储的期权工具名称列表
        
        :return: 工具名称列表
        """
        query = "SELECT DISTINCT instrument_name FROM options_chain ORDER BY instrument_name"
        df = self.conn.execute(query).df()
        if df.empty:
            return []
        return df['instrument_name'].tolist()
    
    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息
        
        :return: 统计信息字典
        """
        stats = {}
        
        # 期权链数据统计
        chain_count = self.conn.execute("SELECT COUNT(*) FROM options_chain").fetchone()[0]
        stats['options_chain_count'] = chain_count
        
        # Greeks数据统计
        greeks_count = self.conn.execute("SELECT COUNT(*) FROM options_greeks").fetchone()[0]
        stats['greeks_count'] = greeks_count
        
        # 唯一到期日数量
        exp_count = self.conn.execute("SELECT COUNT(DISTINCT expiration_date) FROM options_chain").fetchone()[0]
        stats['unique_expiration_dates'] = exp_count
        
        # 最新更新时间
        latest_update = self.conn.execute("SELECT MAX(updated_at) FROM options_chain").fetchone()[0]
        stats['latest_update'] = latest_update
        
        return stats
    
    def check_volume_data_quality(self) -> Dict:
        """
        检查成交量数据质量
        
        :return: 数据质量统计字典
        """
        query = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(volume) as non_null_count,
                COUNT(CASE WHEN volume > 0 THEN 1 END) as non_zero_count,
                COUNT(CASE WHEN volume IS NULL THEN 1 END) as null_count,
                COUNT(CASE WHEN volume = 0 THEN 1 END) as zero_count,
                SUM(volume) as total_volume,
                AVG(volume) as avg_volume,
                MAX(volume) as max_volume
            FROM options_chain
        """
        result = self.conn.execute(query).fetchone()
        
        quality_stats = {
            'total_count': result[0] or 0,
            'non_null_count': result[1] or 0,
            'non_zero_count': result[2] or 0,
            'null_count': result[3] or 0,
            'zero_count': result[4] or 0,
            'total_volume': float(result[5]) if result[5] else 0.0,
            'avg_volume': float(result[6]) if result[6] else 0.0,
            'max_volume': float(result[7]) if result[7] else 0.0,
        }
        
        # 计算数据完整性百分比
        if quality_stats['total_count'] > 0:
            quality_stats['completeness_pct'] = (quality_stats['non_null_count'] / quality_stats['total_count']) * 100
            quality_stats['non_zero_pct'] = (quality_stats['non_zero_count'] / quality_stats['total_count']) * 100
        else:
            quality_stats['completeness_pct'] = 0.0
            quality_stats['non_zero_pct'] = 0.0
        
        return quality_stats
    
    def get_instruments_without_volume(self) -> pd.DataFrame:
        """
        获取没有成交量数据的期权列表
        
        :return: 没有成交量数据的期权DataFrame
        """
        query = """
            SELECT instrument_name, expiration_date, strike, option_type, 
                   mark_price, open_interest, volume
            FROM options_chain
            WHERE volume IS NULL OR volume = 0
            ORDER BY expiration_date, strike, option_type
        """
        return self.conn.execute(query).df()
    
    def create_portfolio(self, portfolio_name: str, description: str = "") -> int:
        """
        创建新的持仓组合
        
        :param portfolio_name: 组合名称
        :param description: 组合描述
        :return: 组合ID
        """
        result = self.conn.execute("""
            INSERT INTO portfolios (portfolio_name, description)
            VALUES (?, ?)
            RETURNING portfolio_id
        """, [portfolio_name, description]).fetchone()
        return result[0] if result else None
    
    def add_position(self, portfolio_id: int, instrument_name: str, 
                    quantity: float, entry_price: float = None):
        """
        添加持仓到组合
        
        :param portfolio_id: 组合ID
        :param instrument_name: 工具名称
        :param quantity: 数量（正数=买入，负数=卖出）
        :param entry_price: 入场价格
        """
        self.conn.execute("""
            INSERT INTO portfolio_positions (portfolio_id, instrument_name, quantity, entry_price)
            VALUES (?, ?, ?, ?)
        """, [portfolio_id, instrument_name, quantity, entry_price])
    
    def get_portfolio_positions(self, portfolio_id: int) -> pd.DataFrame:
        """
        获取组合的所有持仓
        
        :param portfolio_id: 组合ID
        :return: 持仓DataFrame
        """
        query = """
            SELECT pp.*, oc.strike, oc.option_type, oc.expiration_date, oc.mark_price,
                   og.delta, og.gamma, og.theta, og.vega, og.rho
            FROM portfolio_positions pp
            LEFT JOIN options_chain oc ON pp.instrument_name = oc.instrument_name
            LEFT JOIN options_greeks og ON pp.instrument_name = og.instrument_name
            WHERE pp.portfolio_id = ?
        """
        return self.conn.execute(query, [portfolio_id]).df()
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    # 测试代码
    print("="*60)
    print("数据库测试")
    print("="*60)
    
    # 创建数据库实例
    db = OptionsDatabase("test_options.duckdb")
    
    # 测试统计信息
    print("\n1. 数据库统计信息:")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 测试获取到期日列表
    print("\n2. 获取到期日列表:")
    exp_dates = db.get_all_expiration_dates()
    print(f"   找到 {len(exp_dates)} 个到期日")
    if exp_dates:
        print(f"   最早: {exp_dates[0]}")
        print(f"   最晚: {exp_dates[-1]}")
    
    # 关闭数据库
    db.close()
    print("\n测试完成")

