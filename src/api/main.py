"""
A股训练系统 — FastAPI 入口
启动: uvicorn src.api.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    commands,
    learning,
    premarket,
    screening,
    analysis,
    review,
    strategy,
    backtest,
    agent,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    # 后台初始化股票缓存（不阻塞启动）
    import threading
    def _init_cache():
        try:
            from src.data.stock_cache import needs_sync, sync
            if needs_sync():
                sync()
        except Exception:
            pass
    threading.Thread(target=_init_cache, daemon=True).start()

    yield


app = FastAPI(
    title="A股训练系统 API",
    version="1.0.0",
    description="基于教练模型的A股学习训练系统，提供选股评分、回测、盘前分析等接口",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(commands.router)
app.include_router(learning.router)
app.include_router(premarket.router)
app.include_router(screening.router)
app.include_router(analysis.router)
app.include_router(review.router)
app.include_router(strategy.router)
app.include_router(backtest.router)
app.include_router(agent.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
