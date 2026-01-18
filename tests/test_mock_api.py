import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 将项目根目录加入路径，确保能导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.Deribit_HTTP import DeribitAPI

class TestDeribitMock(unittest.TestCase):
    def setUp(self):
        # 初始化 API，传入伪造的 Key
        self.api = DeribitAPI(client_id="fake_id", client_secret="fake_secret")
        # 手动设置 access_token，跳过真实认证
        self.api.access_token = "mock_token_123"

    @patch('api.Deribit_HTTP.requests.Session.get')
    def test_authenticate_mock(self, mock_get):
        """测试认证逻辑（模拟网络请求）"""
        # 1. 准备假数据
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"access_token": "new_mock_token_456"}
        }
        mock_get.return_value = mock_response

        # 2. 调用被测函数
        token = self.api.authenticate()

        # 3. 验证结果
        self.assertEqual(token, "new_mock_token_456")
        print("\n✅ 认证逻辑测试通过 (Mock)")

    @patch('api.Deribit_HTTP.requests.get')
    def test_get_instrument_mock(self, mock_get):
        """测试获取合约信息（模拟网络请求）"""
        # 1. 准备假数据
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "instrument_name": "ETH-30NOV25-2600-C",
                "kind": "option"
            }
        }
        mock_get.return_value = mock_response

        # 2. 调用被测函数
        result = self.api.get_instrument("ETH-30NOV25-2600-C")

        # 3. 验证代码是否正确解析了数据
        self.assertIsNotNone(result)
        self.assertEqual(result['result']['instrument_name'], "ETH-30NOV25-2600-C")
        print("✅ 获取合约逻辑测试通过 (Mock)")

if __name__ == '__main__':
    unittest.main()
