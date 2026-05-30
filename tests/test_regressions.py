import sys
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.backtest import BacktestEngine
from src.commands import stock_select_command, strategy_command
from src.data.akshare_client import AKShareClient


class DataClientRegressionTests(unittest.TestCase):
    def test_get_index_data_filters_date_objects(self):
        fake_index = pd.DataFrame(
            {
                "date": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
                "open": [1.0, 2.0, 3.0],
                "high": [1.1, 2.1, 3.1],
                "low": [0.9, 1.9, 2.9],
                "close": [1.0, 2.0, 3.0],
                "volume": [100, 200, 300],
            }
        )
        fake_akshare = types.SimpleNamespace(stock_zh_index_daily=lambda symbol: fake_index)

        with patch.object(AKShareClient, "_load_sina_fetcher", return_value=None, create=True), \
             patch.dict(sys.modules, {"akshare": fake_akshare}):
            df = AKShareClient.get_index_data("000300", "20240102", "20240103")

        self.assertIsNotNone(df)
        self.assertEqual(list(df["close"]), [1.0, 2.0])


class BacktestRegressionTests(unittest.TestCase):
    def test_empty_kline_returns_data_issue_instead_of_crashing(self):
        empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        result = BacktestEngine.run(empty, lambda df, shares, cash: None, "空数据策略")

        self.assertIn("K线数据为空", result.data_issues)
        self.assertEqual(result.trade_count, 0)


class CommandRegressionTests(unittest.TestCase):
    def test_stock_select_continues_when_sector_data_missing(self):
        kline = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=80, freq="D"),
                "open": range(80, 160),
                "high": range(81, 161),
                "low": range(79, 159),
                "close": range(80, 160),
                "volume": [1000] * 80,
            }
        )

        with patch.object(stock_select_command.AKShareClient, "check_available", return_value=True), \
             patch.object(stock_select_command.AKShareClient, "get_hot_sectors", return_value=[]), \
             patch.object(stock_select_command.AKShareClient, "get_index_data", return_value=None), \
             patch.object(stock_select_command.AKShareClient, "get_daily_kline", return_value=kline), \
             patch.object(stock_select_command.AKShareClient, "get_financial_data", return_value={"pe": 20, "roe": 18, "profit_growth": 25, "debt_ratio": 40}), \
             patch.object(stock_select_command.ObsidianSync, "save_stock_analysis", return_value="/tmp/note.md"), \
             patch.dict(sys.modules, {"akshare": types.SimpleNamespace(stock_zh_a_spot_em=lambda: pd.DataFrame())}):
            output = stock_select_command.execute([])

        self.assertIn("候选股评分", output)
        self.assertNotIn("选股中止", output)

    def test_strategy_name_cannot_escape_strategy_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(strategy_command.Config, "OBSIDIAN_VAULT_PATH", tmp), \
                 patch.object(strategy_command.ObsidianSync, "VAULT_PATH", Path(tmp)):
                output = strategy_command.execute(["../evil"])

            self.assertIn("无效的策略名称", output)
            self.assertFalse((Path(tmp) / "evil.md").exists())


if __name__ == "__main__":
    unittest.main()
