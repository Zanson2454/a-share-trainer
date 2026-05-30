"""
/个股 股票代码 — 单只股票深度分析（不给买卖结论）
"""
from ..data.akshare_client import AKShareClient
from ..scorer import TechnicalScorer
from ..obsidian_sync import ObsidianSync


def execute(args: list = None) -> str:
    """执行 /个股 命令"""
    if not args or len(args) < 1:
        return "❌ 请提供股票代码。示例：`/个股 600519`"

    code = args[0].strip()
    if not code.isdigit() or len(code) != 6:
        return "❌ 无效的股票代码: " + code + "。请输入6位数字代码。"

    if not AKShareClient.check_available():
        return "❌ AKShare 未安装。请运行：`" + AKShareClient.install_guide() + "`"

    lines = []
    lines.append("## 🔬 个股分析 — " + code)
    lines.append("")

    try:
        kline = AKShareClient.get_daily_kline(code)
        if kline is None or kline.empty:
            return "❌ 无法获取 " + code + " 的K线数据"

        kline["ma5"] = kline["close"].rolling(5).mean()
        kline["ma20"] = kline["close"].rolling(20).mean()
        kline["ma60"] = kline["close"].rolling(60).mean()
        latest = kline.iloc[-1]
        prev = kline.iloc[-2] if len(kline) > 1 else latest

        # 趋势
        lines.append("### 一、趋势")
        lines.append("")
        ma20_val = latest.get("ma20", 0)
        ma60_val = latest.get("ma60", 0)
        trend = "上升" if latest["close"] > ma20_val else ("震荡" if latest["close"] > ma60_val else "下降")
        lines.append("- 当前趋势: **" + trend + "**")
        lines.append("- 收盘价 {:.2f} | MA20 {:.2f} | MA60 {:.2f}".format(latest["close"], ma20_val, ma60_val))
        lines.append("")

        # 均线
        lines.append("### 二、均线系统")
        lines.append("")
        lines.append("| 均线 | 数值 | 方向 |")
        lines.append("|------|------|------|")
        for m_label, m_key in [("MA5", "ma5"), ("MA20", "ma20"), ("MA60", "ma60")]:
            val = latest.get(m_key, 0)
            prev_val = prev.get(m_key, val)
            direction = "↑" if val >= prev_val else "↓"
            lines.append("| {} | {:.2f} | {} |".format(m_label, val, direction))
        lines.append("")

        # 成交量
        lines.append("### 三、成交量")
        lines.append("")
        avg_vol_20 = kline["volume"].tail(20).mean()
        vol_ratio = latest["volume"] / avg_vol_20 if avg_vol_20 > 0 else 1
        vol_label = "（放量）" if vol_ratio > 1.5 else ("（缩量）" if vol_ratio < 0.5 else "（正常）")
        lines.append("- 当日成交量: {:.0f}手".format(latest["volume"]))
        lines.append("- 20日均量: {:.0f}手".format(avg_vol_20))
        lines.append("- 量比: {:.2f} {}".format(vol_ratio, vol_label))
        lines.append("")

        # 支撑压力
        lines.append("### 四、支撑与压力")
        lines.append("")
        recent_low = kline["low"].tail(20).min()
        recent_high = kline["high"].tail(20).max()
        lines.append("| 类型 | 位置 | 来源 |")
        lines.append("|------|------|------|")
        lines.append("| 支撑1 | {:.2f} | 20日最低价 |".format(recent_low))
        lines.append("| 支撑2 | {:.2f} | 60日均线 |".format(ma60_val))
        lines.append("| 压力1 | {:.2f} | 20日最高价 |".format(recent_high))
        lines.append("| 压力2 | {:.2f} | 20日均线（若价格在其下） |".format(ma20_val))
        lines.append("")

        # 财务质量
        lines.append("### 五、财务质量")
        lines.append("")
        fin = AKShareClient.get_financial_data(code)
        if fin:
            is_sina = fin.get("_sina_source", False)
            is_ts = fin.get("_ts_source", False)
            name_hint = fin.get("_name", "")
            mktcap_hint = fin.get("_mktcap", 0)
            report_date = fin.get("_report_date", "")

            pe_val = fin.get("pe", None)
            pe_label = "合理" if (isinstance(pe_val, (int, float)) and pe_val < 30) else ("偏高" if isinstance(pe_val, (int, float)) else "N/A")
            pb_val = fin.get("pb", None)
            roe_val = fin.get("roe", None)
            roe_label = "优秀" if (isinstance(roe_val, (int, float)) and roe_val > 15) else ("一般" if isinstance(roe_val, (int, float)) else "N/A")
            debt_val = fin.get("debt_ratio", None)
            debt_label = "安全" if (isinstance(debt_val, (int, float)) and debt_val < 50) else ("高杠杆" if isinstance(debt_val, (int, float)) and debt_val >= 50 else "N/A")
            rev_g = fin.get("revenue_growth", None)
            rev_label = "增长" if (isinstance(rev_g, (int, float)) and rev_g > 0) else ("下滑" if isinstance(rev_g, (int, float)) else "N/A")
            profit_g = fin.get("profit_growth", None)
            profit_label = "增长" if (isinstance(profit_g, (int, float)) and profit_g > 0) else ("下滑" if isinstance(profit_g, (int, float)) else "N/A")

            if name_hint:
                lines.append(f"- 名称: **{name_hint}**")
            if mktcap_hint > 0:
                lines.append(f"- 总市值: **{mktcap_hint:.0f}亿**")
            lines.append("")
            lines.append("| 指标 | 数值 | 评价 |")
            lines.append("|------|------|------|")
            pe_display = f"{pe_val:.1f}" if isinstance(pe_val, (int, float)) else "N/A"
            lines.append(f"| PE(TTM) | {pe_display} | {pe_label} |")
            pb_display = f"{pb_val:.2f}" if isinstance(pb_val, (int, float)) else "N/A"
            lines.append(f"| PB | {pb_display} | |")
            roe_display = f"{roe_val:.1f}%" if isinstance(roe_val, (int, float)) else "N/A"
            lines.append(f"| ROE | {roe_display} | {roe_label} |")
            debt_display = f"{debt_val:.1f}%" if isinstance(debt_val, (int, float)) else "N/A"
            lines.append(f"| 负债率 | {debt_display} | {debt_label} |")
            rev_display = f"{rev_g:+.1f}%" if isinstance(rev_g, (int, float)) else "N/A"
            lines.append(f"| 营收增速 | {rev_display} | {rev_label} |")
            profit_display = f"{profit_g:+.1f}%" if isinstance(profit_g, (int, float)) else "N/A"
            lines.append(f"| 利润增速 | {profit_display} | {profit_label} |")
            lines.append("")
            # 数据来源说明
            sources = []
            if is_sina:
                sources.append("Sina(PE/PB/市值)")
            if is_ts:
                sources.append(f"Tushare(ROE/负债/增速, {report_date})")
            if sources:
                lines.append(f"> 📊 数据来源: {' + '.join(sources)}")
                lines.append("")
        else:
            lines.append("⚠️ 财务数据获取失败")
            lines.append("")

        tech = TechnicalScorer.score(kline)

        # 风险点
        lines.append("### 六、风险点")
        lines.append("")
        lines.append("- [ ] 大盘系统性下跌风险")
        lines.append("- [ ] 行业政策变动风险")
        lines.append("- [ ] 个股流动性风险（日成交额是否过小）")
        lines.append("- [ ] 业绩暴雷风险（财报发布窗口期）")
        lines.append("")

        # 观察信号
        lines.append("### 七、接下来需要观察的信号")
        lines.append("")
        lines.append("- [ ] 能否站稳 MA20 上方（趋势确认）")
        lines.append("- [ ] 成交量是否持续放大（资金进场）")
        lines.append("- [ ] 同板块是否有共振效应")
        lines.append("- [ ] 是否有突破20日高点压力位的尝试")
        lines.append("")

        lines.append("> 🔬 技术面评分: {}/25 — {}".format(tech["score"], tech["desc"]))
        lines.append("> ⚠️ 以上分析仅用于学习研究，不构成投资建议")

        name = "股票" + code
        ObsidianSync.save_stock_analysis(code, name, "\n".join(lines))

    except Exception as e:
        lines.append("❌ 分析出错: " + str(e))

    return "\n".join(lines)
