"""
AI-Powered Stock Market Screening & Analysis System
Entry point - run with:

    uvicorn main:app --reload

or simply:

    python main.py
"""
import asyncio
import contextlib
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from utils.config import CONFIG
from database import db
from broker.mock_feed import MockFeed, seed_ownership_data
from dashboard.manager import manager
from dashboard.screener import run_screen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="AI Stock Screener")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

_feed = None
_broadcast_task = None


def _on_tick(tick: dict):
    # tick already persisted by the feed itself; hook kept for extensibility
    pass


async def _broadcast_loop():
    interval = CONFIG.get("refresh_interval_seconds", 2)
    while True:
        try:
            payload = run_screen()
            await manager.broadcast(payload)
        except Exception as e:
            print("screen loop error:", e)
        await asyncio.sleep(interval)


@app.on_event("startup")
async def startup():
    global _feed, _broadcast_task

    db.init_db()
    seed_ownership_data()

    mode = CONFIG.get("mode", "SIMULATE")
    if mode == "LIVE":
        # See broker/angel_one.py for the full integration + where to add
        # your Angel One API credentials (in config.json, not in code).
        from broker import angel_one
        from utils.stock_universe import NSE_UNIVERSE

        creds = CONFIG["angel_one"]
        _, jwt_token, feed_token = angel_one.login(creds)
        tokens = [s["token"] for s in NSE_UNIVERSE]
        angel_one.start_feed(jwt_token, feed_token, creds, tokens, on_tick=_on_tick)
    else:
        _feed = MockFeed(on_tick=_on_tick, interval_seconds=1.5)
        _feed.start()

    # give the feed a moment to populate initial ticks before first screen
    await asyncio.sleep(2)
    _broadcast_task = asyncio.create_task(_broadcast_loop())


@app.on_event("shutdown")
async def shutdown():
    global _feed, _broadcast_task
    if _feed:
        _feed.stop()
    if _broadcast_task:
        _broadcast_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _broadcast_task


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/screen")
async def api_screen():
    """One-shot REST snapshot of the current screen (useful for debugging/tests)."""
    return JSONResponse(run_screen())


@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": CONFIG.get("mode", "SIMULATE")}


@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # send an immediate snapshot on connect
        await websocket.send_text(__import__("json").dumps(run_screen(), default=str))
        while True:
            # keep the connection alive; client doesn't need to send anything
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    server_cfg = CONFIG.get("server", {})
    uvicorn.run(
        "main:app",
        host=server_cfg.get("host", "127.0.0.1"),
        port=server_cfg.get("port", 8000),
        reload=False,
    )
