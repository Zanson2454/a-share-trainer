"""
/盘前 — 盘前环境分析：大盘、道氏确认、政策、热点、风险
"""
from datetime import datetime
from ..data.akshare_client import AKShareClient
from ..scorer import MarketEnvScorer
from ..obsidian_sync import ObsidianSync
from ..services.premarket_service import check_dow_confirmation


def execute(args: list = None) -> str:
    """执行 /盘前 命令"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []

    # 标题
    lines.append("## 🌅 盘前分析 — " + today)
    lines.append("")

    # 1. 大盘环境
    lines.append("### 一、大盘环境")
    lines.append("")
    if AKShareClient.check_available():
        try:
            index_df = AKShareClient.get_index_data("000001", start_date="20260101")
            if index_df is not None and not index_df.empty:
                latest = index_df.iloc[-1]
                chg = (latest["close"] - latest["open"]) / latest["open"] * 100 if latest["open"] > 0 else 0
                trend = MarketEnvScorer.classify_market({
                    "price_above_ma20": latest["close"] > index_df["close"].tail(20).mean(),
                    "price_above_ma60": latest["close"] > index_df["close"].tail(60).mean(),
                })
                advice = "进攻 80%" if trend == "进攻" else ("震荡 50%" if trend == "震荡" else "防守 30%以下")
                lines.append("- 上证指数: {:.2f}（当日变化 {:+.2f}%）".format(latest["close"], chg))
                lines.append("- **大盘判断: " + trend + "**（仓位建议：" + advice + "）")
                lines.append("")
            else:
                lines.append("⚠️ 无法获取指数数据，请检查 AKShare 安装")
                lines.append("")
        except Exception as e:
            lines.append("⚠️ 获取大盘数据失败: " + str(e))
            lines.append("")
    else:
        lines.append("⚠️ AKShare 未安装。安装：`" + AKShareClient.install_guide() + "`")
        lines.append("")

    # 1.5 道氏确认
    lines.append("### 一之补充：道氏确认（指数相互验证）")
    lines.append("")
    try:
        dow = check_dow_confirmation()
        lines.append("**" + dow["overall"] + "**")
        lines.append("")
        lines.append("| 对照组 | 经济含义 | 信号 | 详情 |")
        lines.append("|--------|----------|------|------|")
        for pair in dow.get("pairs", []):
            lines.append("| {} | {} | {} | {} |".format(
                pair["name"], pair["desc"], pair["signal"], pair.get("detail", "")
            ))
        lines.append("")
    except Exception as e:
        lines.append("⚠️ 道氏确认获取失败: " + str(e))
        lines.append("")

    # 2. 政策方向
    lines.append("### 二、政策方向")
    lines.append("")
    lines.append("| 层级 | 内容 | 影响行业 | 状态 |")
    lines.append("|------|------|----------|------|")
    lines.append("| 长期政策 | （待补充 — 请查阅近期国务院/证监会文件） | | |")
    lines.append("| 短期催化 | （待补充 — 降准降息/行业补贴等） | | |")
    lines.append("| 小作文 | ⚠️ 不参与未经证实的传言 | — | — |")
    lines.append("")

    # 3. 热点板块
    lines.append("### 三、热点板块")
    lines.append("")
    if AKShareClient.check_available():
        sectors = AKShareClient.get_hot_sectors()
        if sectors:
            lines.append("| 板块 | 涨跌幅 | 分类 |")
            lines.append("|------|--------|------|")
            for s in sectors:
                lines.append("| {} | {:+.2f}% | {} |".format(s["name"], s["change"], s["category"]))
            lines.append("")
            main_lines = [s for s in sectors if s["category"] == "主线"]
            if main_lines:
                names = ", ".join(s["name"] for s in main_lines)
                lines.append("**今日主线**: " + names)
                lines.append("")
        else:
            lines.append("⚠️ 无法获取板块数据")
            lines.append("")
    else:
        lines.append("⚠️ AKShare 未安装，无法获取板块数据")
        lines.append("")

    # 4. 风险事件
    lines.append("### 四、风险事件")
    lines.append("")
    lines.append("| 风险类型 | 事件 | 影响评估 |")
    lines.append("|----------|------|----------|")
    lines.append("| 政策风险 | （待补充） | |")
    lines.append("| 外部风险 | （待补充 — 地缘政治/汇率等） | |")
    lines.append("| 流动性风险 | （待补充） | |")
    lines.append("")

    # 5. 观察问题
    lines.append("### 五、今日观察问题")
    lines.append("")
    lines.append("> 请在开盘前回答以下问题，帮助自己形成判断：")
    lines.append("")
    lines.append("1. 今天的大盘环境适合进攻还是防守？你的仓位应该调整吗？")
    lines.append("2. 主线板块是否有持续性？支线是否会升级为主线？")
    lines.append("3. 有没有需要避开的风险事件？")
    lines.append("4. 你今天最关注的1-2只股票是什么？为什么？")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> ⚠️ 仅用于学习研究，不构成投资建议")

    text = "\n".join(lines)

    # 同步 Obsidian
    ObsidianSync.save_note("02_政策", "盘前_" + today + ".md", text)

    return text
