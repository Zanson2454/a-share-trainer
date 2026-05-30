"""
数据层 — AKShare 封装
提供行情、财务、新闻、政策数据的分层管理
"""
import importlib.util
import os
from pathlib import Path

import pandas as pd
from typing import Optional

from .stock_cache import search_cached, needs_sync, sync as sync_cache


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
        获取K线数据
        :param code: 股票代码
        :param period: daily/weekly/monthly/60/30/15/5/1
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
                adjust="qfq"
            )
            if df is not None and not df.empty:
                return AKShareClient._normalize_kline_df(df)
        except Exception as e:
            print(f"[AKShare] 获取K线失败 {code}: {e}")
        return None

    @staticmethod
    def get_kline_for_period(code: str, period: str) -> Optional[pd.DataFrame]:
        """
        获取指定周期的K线数据用于形态识别。
        日线/周线/月线直接获取；15/30/60分钟直接获取；
        120分钟/4小时通过60分钟数据重采样。
        """
        if period in ("daily", "weekly", "monthly"):
            return AKShareClient.get_daily_kline(code, period=period)

        if period in ("15", "30", "60"):
            # AKShare stock_zh_a_hist supports 15/30/60 min periods
            return AKShareClient.get_daily_kline(code, period=period)

        # 120min / 4h → fetch 60min and resample
        if period in ("120", "4h"):
            df = AKShareClient.get_daily_kline(code, period="60")
            if df is None or df.empty:
                return None
            freq = "2h" if period == "120" else "4h"
            df = df.copy()
            df.set_index("date", inplace=True)
            resampled = df.resample(freq).agg({
                "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
            }).dropna()
            resampled = resampled.reset_index()
            return resampled

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
        """获取财务指标 — 三源合并，追踪来源和时效性"""
        fields = ["pe", "pb", "roe", "revenue_growth", "profit_growth", "debt_ratio"]
        result: dict = {f: None for f in fields}
        sources: dict[str, str] = {f: "" for f in fields}
        report_dates: dict[str, str] = {}
        quality_notes: list[str] = []

        # 1. AKShare（完整财务，报告期明确）
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=code)
            if df is not None and not df.empty:
                latest_row = df.iloc[-1]
                # AKShare 列名是中文
                ak_map = {
                    "pe": "市盈率", "pb": "市净率", "roe": "净资产收益率",
                    "revenue_growth": "营业收入增长率", "profit_growth": "净利润增长率",
                    "debt_ratio": "资产负债率",
                }
                for field, col in ak_map.items():
                    val = latest_row.get(col)
                    if val is not None:
                        try:
                            result[field] = float(val)
                        except (ValueError, TypeError):
                            result[field] = None
                        if result[field] is not None:
                            sources[field] = "AKShare"
                # 报告期
                report_col = None
                for c in ["报告期", "日期"]:
                    if c in df.columns:
                        report_col = c
                        break
                if report_col:
                    rp = str(latest_row.get(report_col, ""))[:10]
                    if rp:
                        for f in fields:
                            report_dates[f] = rp
                quality_notes.append(f"AKShare: 报告期 {report_dates.get('pe', '?')}")
        except Exception as e:
            quality_notes.append(f"AKShare: 获取失败({e})")

        # 2. Sina（PE/PB/市值/名称 — 实时快照）
        fetcher = AKShareClient._load_sina_fetcher()
        if fetcher is not None:
            try:
                sina = fetcher.get_stock_realtime(code)
                if sina:
                    result["_name"] = sina.get("name", "")
                    result["_mktcap"] = sina.get("mktcap", 0)
                    result["_industry"] = sina.get("industry", "")
                    # 交叉校验 PE/PB
                    for f in ["pe", "pb"]:
                        sina_val = sina.get(f)
                        if sina_val and sina_val > 0:
                            sina_val = float(sina_val)
                            if result[f] is not None:
                                diff_pct = abs(result[f] - sina_val) / max(result[f], 1) * 100
                                if diff_pct > 20:
                                    quality_notes.append(
                                        f"{f}: AKShare={result[f]:.1f} vs Sina={sina_val:.1f} 差异{diff_pct:.0f}%"
                                    )
                                # Sina PE/PB 是实时数据，优先使用
                                sources[f] = "Sina(实时)"
                                result[f] = sina_val
                            elif not sources[f]:
                                result[f] = sina_val
                                sources[f] = "Sina"
                    quality_notes.append("Sina: PE/PB/市值/名称已获取")
            except Exception as e:
                quality_notes.append(f"Sina: 获取失败({e})")

        # 3. Tushare（ROE/负债率/增速 — 深度财报）
        try:
            from .tushare_client import get_financial_indicators
            ts_fin = get_financial_indicators(code)
            if ts_fin:
                ts_map = {
                    "roe": "roe",
                    "debt_ratio": "debt_to_assets",
                    "revenue_growth": "or_yoy",
                    "profit_growth": "profit_yoy",
                }
                ts_rp = ts_fin.get("report_date", "")
                for field, ts_key in ts_map.items():
                    ts_val = ts_fin.get(ts_key)
                    if ts_val is not None:
                        ts_val = float(ts_val)
                        if result[field] is not None and sources[field] == "AKShare":
                            diff_pct = abs(result[field] - ts_val) / max(abs(result[field]), 1) * 100
                            if diff_pct > 15:
                                quality_notes.append(
                                    f"{field}: AKShare={result[field]:.1f} vs Tushare={ts_val:.1f} 差异{diff_pct:.0f}%"
                                )
                        if not sources[field]:
                            sources[field] = "Tushare"
                            result[field] = ts_val
                        if not report_dates.get(field):
                            report_dates[field] = ts_rp
                quality_notes.append(f"Tushare: ROE/负债/增速已获取(报告期 {ts_rp})")
        except Exception as e:
            quality_notes.append(f"Tushare: 获取失败({e})")

        # 汇总数据质量
        source_count = len({s for s in sources.values() if s})
        covered = sum(1 for v in result.values() if v is not None)
        result["_sources"] = sources
        result["_report_dates"] = report_dates
        result["_data_quality"] = {
            "fields_covered": f"{covered}/{len(fields)}",
            "source_count": source_count,
            "notes": quality_notes,
        }

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
        import socket
        sectors = []
        old_timeout = socket.getdefaulttimeout()
        try:
            import akshare as ak
            socket.setdefaulttimeout(3)
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
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
        finally:
            socket.setdefaulttimeout(old_timeout)
        return sectors

    # ============================================================
    # Sina 股票列表（免费、实时PE/PB/市值/换手率）
    # ============================================================

    @staticmethod
    def get_stock_pool(min_mktcap: float = 50, max_pe: float = 200,
                       exclude_st: bool = True) -> pd.DataFrame:
        """
        从缓存+Sina实时数据筛选候选池
        :param min_mktcap: 最小总市值(亿)
        :param max_pe: 最大市盈率
        :param exclude_st: 排除ST
        :return: DataFrame with code, name, pe, pb, mktcap, changepercent
        """
        from .stock_cache import get_stock_pool as cached_pool
        results = cached_pool(min_mktcap=min_mktcap, max_pe=max_pe, exclude_st=exclude_st)
        if results:
            return pd.DataFrame(results)

        # 缓存不可用时回退 Sina
        fetcher = AKShareClient._load_sina_fetcher()
        if fetcher is None:
            return pd.DataFrame()

        try:
            df = fetcher.get_stock_list()
            if df.empty:
                return df
            df = df[df["mktcap"] >= min_mktcap]
            df = df[(df["pe"] > 0) & (df["pe"] <= max_pe)]
            if exclude_st:
                df = df[~df["name"].str.contains("ST|退市", na=False)]
            return df.sort_values("mktcap", ascending=False).reset_index(drop=True)
        except Exception as e:
            print(f"[Sina] 获取股票列表失败: {e}")
            return pd.DataFrame()

    # ============================================================
    # Tushare 数据（复权因子 / 交易日历 / 停复牌 — 120积分）
    # ============================================================

    @staticmethod
    def get_adj_factor(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取复权因子（Tushare）"""
        try:
            from .tushare_client import get_adj_factor
            return get_adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def get_trade_calendar(start_date: str, end_date: str) -> pd.DataFrame:
        """获取交易日历（Tushare）"""
        try:
            from .tushare_client import get_trade_cal
            return get_trade_cal(start_date=start_date, end_date=end_date)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def search_stocks(keyword: str) -> list[dict]:
        """按名称或代码搜索股票，优先使用缓存"""
        # 1. 缓存优先（毫秒级响应）
        cached = search_cached(keyword)
        if cached:
            return cached

        # 2. 缓存为空则触发同步后重试
        if needs_sync():
            sync_cache()
            cached = search_cached(keyword)
            if cached:
                return cached

        # 3. 缓存不可用，回退 Sina/AKShare
        results: list[dict] = []
        fetcher = AKShareClient._load_sina_fetcher()
        if fetcher is not None:
            try:
                df = fetcher.get_stock_list()
                if not df.empty:
                    kw = keyword.strip().upper()
                    mask = df["code"].str.contains(kw, na=False) | df["name"].str.contains(kw, na=False)
                    matched = df[mask].head(10)
                    for _, row in matched.iterrows():
                        results.append({
                            "code": str(row.get("code", "")),
                            "name": str(row.get("name", "")),
                        })
            except Exception as e:
                print(f"[Sina] 搜索股票失败: {e}")

        if not results:
            try:
                import akshare as ak
                df = ak.stock_info_a_code_name()
                if df is not None and not df.empty:
                    kw = keyword.strip().upper()
                    code_col = "code" if "code" in df.columns else "代码"
                    name_col = "name" if "name" in df.columns else "名称"
                    mask = df[code_col].str.contains(kw, na=False) | df[name_col].str.contains(kw, na=False)
                    matched = df[mask].head(10)
                    for _, row in matched.iterrows():
                        results.append({
                            "code": str(row.get(code_col, "")),
                            "name": str(row.get(name_col, "")),
                        })
            except Exception as e:
                print(f"[AKShare] 搜索股票失败: {e}")

        return results
