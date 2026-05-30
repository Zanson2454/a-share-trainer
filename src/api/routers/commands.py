"""GET /api/commands — 命令列表"""

from fastapi import APIRouter

router = APIRouter(tags=["commands"])


@router.get("/api/commands")
def list_commands():
    return {
        "commands": [
            {"name": "/帮助", "slug": "help", "description": "显示命令列表和使用说明", "example": "/帮助"},
            {"name": "/学习", "slug": "learning", "description": "每日学习主题 + 教练提问", "example": "/学习"},
            {"name": "/盘前", "slug": "premarket", "description": "盘前环境分析", "example": "/盘前"},
            {"name": "/选股", "slug": "screening", "description": "五维评分筛选候选股", "example": "/选股"},
            {"name": "/个股", "slug": "stock-analysis", "description": "单只股票深度分析", "example": "/个股 600519"},
            {"name": "/复盘", "slug": "review", "description": "每日复盘模板", "example": "/复盘"},
            {"name": "/策略", "slug": "strategy", "description": "策略库管理", "example": "/策略"},
            {"name": "/回测", "slug": "backtest", "description": "策略历史回测", "example": "/回测 均线金叉 2024-01-01 2024-12-31"},
        ],
        "disclaimer": "所有输出仅用于学习研究，不构成投资建议",
    }
