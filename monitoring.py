import logging
import time
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_start_time = None
_COUNTERS = {
    "bookings_created": 0,
    "bookings_cancelled": 0,
    "reminders_sent": 0,
    "backup_success": 0,
    "backup_failed": 0,
}


def increment_counter(name: str, amount: int = 1) -> None:
    _COUNTERS[name] = _COUNTERS.get(name, 0) + amount


def get_metrics() -> dict:
    return dict(_COUNTERS)


def log_event(logger_obj, event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger_obj.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def log_payment_placeholder(action: str = "not_implemented", **fields) -> None:
    log_event(logger, "payment_placeholder", action=action, **fields)


def start_monitoring():
    global _start_time
    _start_time = time.time()
    logger.info("Monitoring started")


def get_uptime() -> float:
    if _start_time:
        return time.time() - _start_time
    return 0


async def check_db_health() -> bool:
    """Check if database is accessible."""
    try:
        import db as _db
        async with _db.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False


async def check_storage_health() -> bool:
    """HIGH-05 FIX: Actually check the FSM storage (FileStorage or Redis)."""
    try:
        import os
        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            # M-3 FIX: guard aioredis import in case package is not installed
            try:
                import aioredis
            except ImportError:
                logger.warning("aioredis not installed: skipping Redis health check")
                return True
            r = await aioredis.from_url(redis_url, socket_connect_timeout=3)
            await r.ping()
            await r.close()
        else:
            # Test FileStorage JSON file is readable/writable
            import config as _cfg
            from pathlib import Path
            fsm_file = Path(_cfg.DB_PATH).parent / "fsm_state.json"
            parent = fsm_file.parent
            parent.mkdir(parents=True, exist_ok=True)
            if fsm_file.exists():
                with open(fsm_file, "r", encoding="utf-8") as f:
                    import json
                    json.load(f)
        return True
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return False


async def check_scheduler_health() -> bool:
    """Check if scheduler is running."""
    try:
        from scheduler import scheduler
        return scheduler.running
    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
        return False


async def check_scheduler_lock_status() -> dict:
    try:
        import storage
        return await storage.get_scheduler_lock_status("scheduler")
    except Exception as e:
        logger.error(f"Scheduler lock status check failed: {e}")
        return {"lock_name": "scheduler", "locked": False, "status": "error", "error": str(e)}


async def get_health_status() -> dict:
    """Get comprehensive health status with real checks."""
    uptime = get_uptime()
    db_ok = await check_db_health()
    storage_ok = await check_storage_health()
    scheduler_ok = await check_scheduler_health()
    scheduler_lock = await check_scheduler_lock_status()
    lock_ok = scheduler_lock.get("status") != "error"
    all_ok = db_ok and storage_ok and scheduler_ok and lock_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "uptime_seconds": round(uptime, 2),
        "uptime_human": format_uptime(uptime),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": get_metrics(),
        "checks": {
            "database": "ok" if db_ok else "error",
            "storage": "ok" if storage_ok else "error",
            "scheduler": "ok" if scheduler_ok else "error",
            "scheduler_lock": scheduler_lock,
        }
    }


def format_uptime(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
