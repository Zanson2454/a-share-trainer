"""
股票基本信息缓存 — 参考 Tushare stock_basic 设计

字段设计（对齐 Tushare）:
  code, name, exchange, list_status, list_date, delist_date, updated_at
  list_status: L=上市, D=退市, P=暂停上市
增量更新策略:
  1. 首次全量拉取 Sina 股票列表，写入缓存
  2. 后续增量同步：比较新旧列表，新出现的 code → 新增上市
     消失的 code → 标记退市（记录 delist_date）
  3. 每日首次同步时检查，避免频繁请求 Sina 分页接口
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional


CACHE_DIR = Path.home() / ".cache" / "stock_data"
CACHE_FILE = CACHE_DIR / "stock_basic.json"

# 缓存有效期（天）：超过此天数后需同步
MAX_CACHE_AGE_DAYS = 1


def _exchange_from_code(code: str) -> str:
    """从6位代码推断交易所"""
    if code.startswith("6"):
        return "SSE"
    elif code.startswith(("0", "3")):
        return "SZSE"
    elif code.startswith(("8", "4")):
        return "BSE"
    return ""


def _now_iso() -> str:
    return datetime.now().strftime("%Y%m%d")


def _today_str() -> str:
    return date.today().isoformat()


def load_cache() -> dict:
    """从缓存文件加载全部股票，返回 {code: stock_dict}"""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stocks", {})
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(stocks: dict, meta: dict | None = None):
    """写入缓存文件"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "stocks": stocks,
        "meta": meta or {
            "total": len(stocks),
            "listed": sum(1 for s in stocks.values() if s.get("list_status") == "L"),
            "updated_at": _now_iso(),
            "source": "sina",
        },
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_meta() -> dict | None:
    """获取缓存元数据（含更新时间、总数等）"""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("meta", {})
    except (json.JSONDecodeError, IOError):
        return None


def needs_sync() -> bool:
    """缓存是否需要同步（超过有效期）"""
    meta = get_meta()
    if not meta:
        return True
    updated = meta.get("updated_at", "")
    if len(updated) != 8:
        return True
    try:
        last = datetime.strptime(updated, "%Y%m%d").date()
        return (date.today() - last).days >= MAX_CACHE_AGE_DAYS
    except ValueError:
        return True


def get_cached_stock(code: str) -> dict | None:
    """获取单只股票的缓存信息"""
    stocks = load_cache()
    return stocks.get(code)


def search_cached(keyword: str) -> list[dict]:
    """按代码或名称搜索缓存中的股票"""
    stocks = load_cache()
    kw = keyword.strip().upper()
    results = []
    for code, info in stocks.items():
        if kw in code or kw in info.get("name", "").upper():
            results.append({"code": code, "name": info.get("name", "")})
        if len(results) >= 20:
            break
    return results


def get_listed_stocks() -> list[dict]:
    """获取所有上市状态的股票（用于选股池筛选）"""
    stocks = load_cache()
    return [
        {"code": code, **info}
        for code, info in stocks.items()
        if info.get("list_status") == "L"
    ]


def _fetch_sina_stock_list() -> list[dict]:
    """从 Sina 拉取全量股票列表，返回 [{code, name, pe, pb, mktcap, ...}, ...]"""
    from pathlib import Path as _Path
    import importlib.util

    fetcher_path = _Path(__file__).resolve().parents[3] / "stock_data" / "fetcher.py"
    if not fetcher_path.exists():
        print("[StockCache] Sina fetcher 不存在，无法拉取股票列表")
        return []

    spec = importlib.util.spec_from_file_location("sina_fetcher", fetcher_path)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    try:
        df = module.get_stock_list()
        if df is None or df.empty:
            return []
        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                "code": str(row.get("code", "")),
                "name": str(row.get("name", "")),
                "pe": float(row.get("pe", 0) or 0),
                "pb": float(row.get("pb", 0) or 0),
                "mktcap": float(row.get("mktcap", 0) or 0),
                "nmc": float(row.get("nmc", 0) or 0),
                "turnoverratio": float(row.get("turnoverratio", 0) or 0),
            })
        return stocks
    except Exception as e:
        print(f"[StockCache] 拉取 Sina 股票列表失败: {e}")
        return []


def sync(force: bool = False) -> dict:
    """
    增量同步股票基本信息缓存。
    首次调用或缓存过期时，从 Sina 拉取全量列表并与缓存比较：
      - 新出现的 code → 新增，设置 list_date
      - 消失的 code（原状态为 L）→ 标记 list_status='D'，记录 delist_date
      - 名称变更 → 更新 name
    返回: {"added": N, "delisted": N, "renamed": N, "total": N}
    """
    if not force and not needs_sync():
        stocks = load_cache()
        return {"added": 0, "delisted": 0, "renamed": 0, "total": len(stocks)}

    fresh = _fetch_sina_stock_list()
    if not fresh:
        print("[StockCache] 拉取失败，继续使用缓存")
        stocks = load_cache()
        return {"added": 0, "delisted": 0, "renamed": 0, "total": len(stocks)}

    cached = load_cache()
    fresh_codes = {s["code"] for s in fresh}
    cached_codes = set(cached.keys())
    today = _today_str()

    added = 0
    delisted = 0
    renamed = 0

    # 1. 新增上市
    for s in fresh:
        code = s["code"]
        if code not in cached:
            cached[code] = {
                "name": s["name"],
                "exchange": _exchange_from_code(code),
                "list_status": "L",
                "list_date": today,
                "delist_date": None,
                "updated_at": _now_iso(),
            }
            added += 1

    # 2. 检查退市或暂停（缓存在但 Sina 列表中消失）
    for code in cached_codes - fresh_codes:
        info = cached[code]
        if info.get("list_status") == "L":
            info["list_status"] = "D"
            info["delist_date"] = today
            info["updated_at"] = _now_iso()
            delisted += 1

    # 3. 名称变更检测
    for s in fresh:
        code = s["code"]
        if code in cached:
            old_name = cached[code].get("name", "")
            new_name = s.get("name", "")
            if old_name and new_name and old_name != new_name:
                cached[code]["name"] = new_name
                cached[code]["updated_at"] = _now_iso()
                renamed += 1

    save_cache(cached)
    print(f"[StockCache] 同步完成: 新增{added} 退市{delisted} 更名{renamed} 总数{len(cached)}")
    return {"added": added, "delisted": delisted, "renamed": renamed, "total": len(cached)}


def get_stock_pool(min_mktcap: float = 50, max_pe: float = 200,
                   exclude_st: bool = True) -> list[dict]:
    """
    从缓存 + Sina 实时数据获取选股候选池。
    缓存提供基础信息（code/name），实时数据提供 PE/PB/市值。
    返回: [{code, name, pe, pb, mktcap, changepercent, ...}, ...]
    """
    # 确保缓存可用
    if needs_sync():
        sync()

    listed = get_listed_stocks()
    if not listed:
        return []

    # 尝试获取实时 PE/PB（优先 Sina）
    fresh = _fetch_sina_stock_list()
    realtime = {s["code"]: s for s in fresh} if fresh else {}

    results = []
    for s in listed:
        code = s["code"]
        rt = realtime.get(code, {})
        pe = rt.get("pe", 0)
        mktcap = rt.get("mktcap", 0)
        name = s.get("name", "")

        if mktcap < min_mktcap:
            continue
        if pe <= 0 or pe > max_pe:
            continue
        if exclude_st and ("ST" in name or "退市" in name):
            continue

        results.append({
            "code": code,
            "name": name,
            "pe": pe,
            "pb": rt.get("pb", 0),
            "mktcap": mktcap,
            "nmc": rt.get("nmc", 0),
            "changepercent": rt.get("changepercent", 0),
            "turnoverratio": rt.get("turnoverratio", 0),
        })

    results.sort(key=lambda x: x["mktcap"], reverse=True)
    return results
