import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
# 显示全部列
pd.set_option('display.max_columns', None)
from pprint import pprint
from credentials import client_id, client_secret, http_base_url
import time

class DeribitAPI:
    def __init__(self, client_id, client_secret, base_url=None, timeout=10, max_retries=3):
        """
        初始化 Deribit API 客户端
        
        :param client_id: API客户端ID
        :param client_secret: API客户端密钥
        :param base_url: API基础URL（可选）
        :param timeout: 请求超时时间（秒），默认10秒
        :param max_retries: 最大重试次数，默认3次
        """
        self.client_id = client_id
        self.client_secret = client_secret
        # 如果未指定 base_url，使用 credentials.py 中配置的 http_base_url
        self.base_url = base_url or http_base_url
        self.timeout = timeout
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.access_token = self.authenticate()

    def authenticate(self):
        """
        使用 client_id 和 client_secret 进行认证，返回 access_token。
        包含错误处理和重试机制。
        """
        auth_url = f"{self.base_url}/public/auth"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        try:
            # 发送认证请求（带超时）
            response = self.session.get(
                auth_url, 
                params=params, 
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )

            # 检查请求是否成功
            if response.status_code == 200:
                data = response.json()
                access_token = data['result']['access_token']

                return access_token
            else:
                pass

                return None
        except requests.exceptions.Timeout:
            pass

            return None
        except requests.exceptions.ConnectionError as e:
            pass


            return None
        except requests.exceptions.RequestException as e:
            return None

    def get_book_summary_by_currency(self, currency="ETH", kind="option"):
        """
        使用 access_token 获取指定货币（如 ETH）的期权数据。
        需要认证。
        """
        # 检查认证状态
        if not self.access_token:
            pass

            return None
        
        url = f"{self.base_url}/public/get_book_summary_by_currency"
        params = {
            "currency": currency,
            "kind": kind
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, params=params, headers=headers)

        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()

            # pprint(data)

            return data
        else:
            pass

    def get_historical_volatility(self, currency="BTC"):
        """
        获取指定货币的历史波动率。
        """
        url = f"{self.base_url}/public/get_historical_volatility"
        params = {
            "currency": currency
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, params=params, headers=headers)

        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()

            pprint(data)
        else:
            pass

# 获取持仓
    def get_position(self, instrument_name):
        """
        获取指定合约的仓位信息
        :param instrument_name: 合约名称，例如 'BTC-PERPETUAL'
        :return: 仓位信息的 JSON 响应
        """
        url = f"{self.base_url}/private/get_position"
        params = {
            "instrument_name": instrument_name
        }

        response = requests.get(url, headers=self.headers, params=params)

        # 检查响应是否成功
        if response.status_code == 200:
            return response.json()
        else:
            pass

            return None

# 获取全部持仓
    def get_all_positions(self, currency="ETH", kind="option"):
        """
        使用 access_token 获取指定货币（如 BTC）和类别（如 future）的持仓信息。
        需要认证。
        """
        # 检查认证状态
        if not self.access_token:
            pass

            return None
        
        url = f"{self.base_url}/private/get_positions"
        params = {
            "currency": currency,
            "kind": kind
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = self.session.get(
                url, 
                params=params, 
                headers=headers,
                timeout=self.timeout
            )

            # 检查请求是否成功
            if response.status_code == 200:
                data = response.json()

                # pprint(data)
                return data
            else:
                pass

                # 返回错误信息，而不是None
                try:
                    error_data = response.json()
                    return error_data
                except:
                    return {'error': {'code': response.status_code, 'message': response.text}}
        except requests.exceptions.Timeout:
            pass

            return None
        except requests.exceptions.ConnectionError as e:
            pass

            return None
        except requests.exceptions.RequestException as e:
            return None

    def get_instrument(self, instrument_name="BTC-13JAN23-16000-P"):
        """
        使用 public API 获取指定期权或期货合约的详细信息。

        :param instrument_name: 合约名称，例如 "BTC-13JAN23-16000-P"。
        :return: 合约的详细信息
        """
        url = f"{self.base_url}/public/get_instrument"
        params = {
            "instrument_name": instrument_name
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.get(url, params=params, headers=headers)

        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()

            # pprint(data)

            return data
        else:
            pass

    def get_instruments(self, currency="ETH", kind="option"):
        """
        获取指定货币和类型的工具列表（无需认证）。
        
        :param currency: 货币类型，例如 "ETH" 或 "BTC"
        :param kind: 工具类型，例如 "option" 或 "future"
        :return: 工具列表
        """
        url = f"{self.base_url}/public/get_instruments"
        params = {
            "currency": currency,
            "kind": kind
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.get(url, params=params, headers=headers)

        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()
            instruments = data.get('result', [])
            return data
        else:
            pass

            return None

    def get_order_book(self, instrument_name, depth=1):
        """
        获取订单簿数据，包含Greeks数据（delta, gamma, theta, vega, rho）。
        需要认证。
        
        :param instrument_name: 合约名称，例如 "ETH-30NOV25-2600-C"
        :param depth: 订单簿深度，默认1即可获取Greeks数据
        :return: 订单簿数据，包含Greeks
        """
        # 检查认证状态
        if not self.access_token:
            pass

            return None
        
        url = f"{self.base_url}/public/get_order_book"
        params = {
            "instrument_name": instrument_name,
            "depth": depth
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, params=params, headers=headers)

        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            
            # 检查是否包含Greeks数据
            if 'greeks' in result:
                greeks = result['greeks']
            
            return data
        else:
            pass

            return None

# 获取实时行情
    def get_index_price(self, index_name="ada_usd"):
        """
        获取指定 index 的价格。
        """
        url = f"{self.base_url}/public/get_index_price"
        params = {
            "index_name": index_name
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.get(url, params=params, headers=headers)

        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()

            pprint(data)

            return data
        else:
            pass

if __name__ == "__main__":
    api = DeribitAPI(client_id, client_secret)

    # 获取 ETH 的期权数据
    # api.get_book_summary_by_currency(currency="ETH", kind="option")

    # 获取 BTC 的历史波动率数据
    # api.get_historical_volatility(currency="BTC")

    # 获取全部持仓
    all_position = api.get_all_positions('ETH', 'option')
    pos_df = pd.DataFrame(all_position['result'])
