"""
Agent 分析服务层 — 封装 Orchestrator 的调用，提供统一接口
"""

from ..agents.orchestrator import AgentOrchestrator
from ..config import Config


def analyze_with_agents(code: str, deep: bool = False) -> dict:
    """
    使用多 Agent 系统深度分析一只股票

    :param code: 6 位股票代码
    :param deep: 是否使用深度模式（Pro 模型 + 5 轮辩论）
    :return: 结构化分析结果，含 error 字段表示失败
    """
    # 验证代码格式
    if not code or not code.isdigit() or len(code) != 6:
        return {"error": f"无效的股票代码: {code}，请输入6位数字代码"}

    # 验证 API 配置
    if not Config.DEEPSEEK_API_KEY:
        return {
            "error": (
                "❌ 未配置 DeepSeek API Key。\n"
                "请在 .env 文件中添加：\n"
                "  DEEPSEEK_API_KEY=sk-xxx"
            )
        }

    try:
        orch = AgentOrchestrator(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
        )
        result = orch.analyze(code, deep=deep)
        return result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Agent 分析异常: {str(e)}"}
