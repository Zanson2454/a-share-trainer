"""
数据层 — AKShare 封装
提供行情、财务、新闻、政策数据的分层管理
"""
import importlib.util
import os
from pathlib import Path

import pandas as pd
from typing import Optional


class AKShareClient:
    """AKShare 数据客户端 — 免费、无需 API Key"""

    _available = None
    _sina_fetcher = None
    _sina_fetcher_checked = False

    @classmethod
    def check_available(cls) -> bool:
        """检测可用数据源：优先 Sina fetcher，AKShare 作为兜底。"""
        if cls._available is not None:
            return cls._available
        if cls._load_sina_fetcher() is not None:
            cls._available = True
            return cls._available
        try:
            import akshare as ak  # noqa: F401
            cls._available = True
        except ImportError:
            cls._available = False
        return cls._available

    @classmethod
    def install_guide(cls) -> str:
        """返回安装建议"""
        return "确认 /Users/zhangang/Documents/PyFile/stock_data/fetcher.py 存在，或运行 pip install akshare>=1.12.0"

    @classmethod
    def _load_sina_fetcher(cls):
        """加载 Hermes 产出的 Sina 数据管道。"""
        if cls._sina_fetcher_checked:
            return cls._sina_fetcher

        default_path = Path(__file__).resolve().parents[3] / "stock_data" / "fetcher.py"
        fetcher_path = Path(os.getenv("SINA_FETCHER_PATH", str(default_path)))
        cls._sina_fetcher_checked = True

        if not fetcher_path.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location("a_share_sina_fetcher", fetcher_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls._sina_fetcher = module
        except Exception as e:
            print(f"[Sina] 数据管道加载失败: {e}")
            cls._sina_fetcher = None
        return cls._sina_fetcher

    @staticmethod
    def _parse_date(value) -> Optional[pd.Timestamp]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) == 8 and text.isdigit():
            return pd.to_datetime(text, format="%Y%m%d")
        return pd.to_datetime(text)

    @classmethod
    def _normalize_kline_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """统一 Sina/AKShare 字段为 date/open/high/low/close/volume。"""
        if df is None or df.empty:
            return pd.DataFrame()

        normalized = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        }).copy()

        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in normalized.columns]
        if missing:
            raise ValueError("K线数据缺少字段: " + ",".join(missing))

        normalized = normalized[required]
        normalized["date"] = pd.to_datetime(normalized["date"])
        for col in ["open", "high", "low", "close", "volume"]:
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
        normalized = normalized.dropna(subset=["date", "open", "high", "low", "close"])
        return normalized.sort_values("date").reset_index(drop=True)

    @classmethod
    def _filter_by_date(cls, df: pd.DataFrame, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        filtered = df.copy()
        filtered["date"] = pd.to_datetime(filtered["date"])
        start = cls._parse_date(start_date)
        end = cls._parse_date(end_date)
        if start is not None:
            filtered = filtered[filtered["date"] >= start]
        if end is not None:
            filtered = filtered[filtered["date"] <= end]
        return filtered.reset_index(drop=True)

    # ============================================================
    # 行情数据层
    # ============================================================

    @staticmethod
    def get_daily_kline(code: str, start_date: str = None, end_date: str = None,
                         period: str = "daily") -> Optional[pd.DataFrame]:
        """
        获取日K线数据
        :param code: 股票代码，如 '600519'
        :param start_date: 开始日期 '20240101'
        :param end_date: 结束日期 '20241231'
        :param period: daily/weekly/monthly
        :return: DataFrame with columns: date, open, high, low, close, volume
        """
        fetcher = AKShareClient._load_sina_fetcher()
        if fetcher is not None and period == "daily":
            try:
                df = fetcher.get_stock_daily(code, start_date=start_date, end_date=end_date, adjust="qfq")
                df = AKShareClient._normalize_kline_df(df)
                if not df.empty:
                    return df
            except Exception as e:
                print(f"[Sina] 获取K线失败 {code}: {e}")

        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                start_date=start_date or "20200101",
                end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
            if df is not None and not df.empty:
                return AKShareClient._normalize_kline_df(df)
        except Exception as e:
            print(f"[AKShare] 获取K线失败 {code}: {e}")
        return None

    @staticmethod
    def get_realtime_quote(codes: list[str]) -> Optional[pd.DataFrame]:
        """获取实时行情"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                # 过滤指定代码
                df = df[df["代码"].isin(codes)]
                return df
        except Exception as e:
            print(f"[AKShare] 获取实时行情失败: {e}")
        return None

    @staticmethod
    def get_index_data(index_code: str = "000300",
                       start_date: str = None,
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取指数数据
        :param index_code: 000300(沪深300), 000001(上证), 399001(深证)
        """
        fetcher = AKShareClient._load_sina_fetcher()
        if fetcher is not None:
            try:
                df = fetcher.get_index_daily(index_code, start_date=start_date, end_date=end_date)
                df = AKShareClient._normalize_kline_df(df)
                if not df.empty:
                    return df
            except Exception as e:
                print(f"[Sina] 获取指数数据失败 {index_code}: {e}")

        try:
            import akshare as ak
            market = "sh" if index_code.startswith("0") else "sz"
            df = ak.stock_zh_index_daily(symbol=f"{market}{index_code}")
            if df is not None and not df.empty:
                df = AKShareClient._normalize_kline_df(df)
                return AKShareClient._filter_by_date(df, start_date, end_date)
        except Exception as e:
            print(f"[AKShare] 获取指数数据失败: {e}")
        return None

    # ============================================================
    # 财务数据层
    # ============================================================

    @staticmethod
    def get_financial_data(code: str) -> dict:
        """获取财务指标"""
        result = {}
        try:
            import akshare as ak
            # 获取主要财务指标
            df = ak.stock_financial_analysis_indicator(symbol=code)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                result = {
                    "pe": latest.get("市盈率", None),
                    "pb": latest.get("市净率", None),
                    "roe": latest.get("净资产收益率", None),
                    "revenue_growth": latest.get("营业收入增长率", None),
                    "profit_growth": latest.get("净利润增长率", None),
                    "debt_ratio": latest.get("资产负债率", None),
                }
        except Exception as e:
            print(f"[AKShare] 获取财务数据失败 {code}: {e}")
        return result

    # ============================================================
    # 新闻/政策数据层
    # ============================================================

    @staticmethod
    def get_market_news() -> list[dict]:
        """获取市场新闻 — 提取 事件→影响行业→相关公司→验证指标"""
        news_list = []
        try:
            import akshare as ak
            df = ak.stock_info_global_em()
            if df is not None and not df.empty:
                for _, row in df.head(10).iterrows():
                    news_list.append({
                        "title": str(row.iloc[0]) if len(row) > 0 else "",
                        "time": str(row.iloc[1]) if len(row) > 1 else "",
                    })
        except Exception as e:
            print(f"[AKShare] 获取新闻失败: {e}")
        return news_list

    @staticmethod
    def get_sector_performance() -> Optional[pd.DataFrame]:
        """获取行业板块表现"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[AKShare] 获取板块数据失败: {e}")
        return None

    @staticmethod
    def get_hot_sectors() -> list[dict]:
        """获取热门板块 — 区分主线/支线/一日游"""
        sectors = []
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                # 按涨跌幅排序
                df_sorted = df.sort_values(by="涨跌幅", ascending=False)
                for _, row in df_sorted.head(10).iterrows():
                    change = float(row.get("涨跌幅", 0))
                    category = "主线" if change > 3 else ("支线" if change > 1.5 else "一日游")
                    sectors.append({
                        "name": row.get("板块名称", ""),
                        "change": change,
                        "category": category,
                    })
        except Exception as e:
            print(f"[AKShare] 获取热门板块失败: {e}")
        return sectors
