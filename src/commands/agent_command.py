"""
/agent 股票代码 [--deep] — AI 多 Agent 深度研判

4 个 AI 分析师（基本面/技术面/情绪面/风控）并行分析 →
多空辩论 → PM 综合决策 → 完整推理链输出
"""

import time
from ..services.agent_service import analyze_with_agents


def execute(args: list = None) -> str:
    """执行 /agent 命令"""
    if not args:
        return (
            "❌ 请提供股票代码。\n"
            "用法：`/agent 600519`        快速分析（Flash 模型，2 轮辩论）\n"
            "      `/agent 600519 --deep`  深度分析（Pro 模型，5 轮辩论）"
        )

    # 解析参数
    code = args[0].strip()
    deep_mode = "--deep" in args

    if not code.isdigit() or len(code) != 6:
        return f"❌ 无效的股票代码: {code}。请输入6位数字代码。"

    # 执行分析
    lines = [f"🤖 AI Agent 深度研判 — {code}"]
    lines.append("")

    start = time.time()
    result = analyze_with_agents(code, deep=deep_mode)

    if "error" in result:
        return f"❌ {result['error']}"

    # 股票名称
    name = result.get("name", code)
    lines[0] = f"🤖 AI Agent 深度研判 — {code} {name}"

    # 分析师报告
    reports = result.get("analyst_reports", {})
    labels = {
        "fundamental": ("📊 基本面分析师", "═" * 50),
        "technical": ("📈 技术面分析师", "═" * 50),
        "sentiment": ("💬 情绪面分析师", "═" * 50),
        "risk": ("🛡️ 风控分析师", "═" * 50),
    }

    for key, (label, sep) in labels.items():
        report = reports.get(key, "")
        if report:
            lines.append(sep)
            lines.append(label)
            lines.append(sep)
            lines.append(report)
            lines.append("")

    # 辩论记录
    debate = result.get("debate", [])
    if debate:
        lines.append("═" * 50)
        lines.append("🐂🦅 多空辩论")
        lines.append("═" * 50)
        lines.append("")

        for entry in debate:
            r = entry["round"]
            etype = entry.get("type", "debate")
            lines.append(f"── 第 {r} 轮{'（开场陈述）' if etype == 'opening' else ''} ──")
            lines.append("")
            lines.append(f"🐂 多头：")
            lines.append(entry.get("bull", "")[:500])
            lines.append("")
            lines.append(f"🐻 空头：")
            lines.append(entry.get("bear", "")[:500])
            lines.append("")

    # PM 决策
    lines.append("═" * 50)
    lines.append("🎯 PM 决策")
    lines.append("═" * 50)
    lines.append("")
    lines.append(f"决策：{result.get('decision', 'N/A')}")
    lines.append(f"置信度：{result.get('confidence_level', 'N/A')} "
                 f"({int(result.get('confidence', 0) * 100)}%)")
    lines.append(f"核心理由：{result.get('core_reason', 'N/A')}")
    lines.append(f"关键风险：{result.get('key_risk', 'N/A')}")
    lines.append("")

    # 统计
    token_info = result.get("token_usage", {})
    elapsed = result.get("elapsed_seconds", 0)
    lines.append(f"📊 本次消耗：{token_info.get('total', 0):,} token "
                 f"≈ ¥{token_info.get('estimated_cost_rmb', 0):.3f} | "
                 f"耗时 {elapsed}s | 模型 {result.get('model', '')}")
    lines.append("")
    lines.append(result.get("disclaimer", ""))

    return "\n".join(lines)
