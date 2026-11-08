"""
API Key authentication middleware.
Supports both X-API-Key (direct) and X-RapidAPI-Key (RapidAPI marketplace).
"""
import hashlib
from fastapi import Header, HTTPException
from app.usage import get_db, get_usage, TIER_LIMITS


async def verify_api_key(
    x_api_key: str = Header(None, alias="X-API-Key", description="Your AgentTools API key"),
    x_rapidapi_key: str = Header(None, alias="X-RapidAPI-Key", description="RapidAPI key (if using RapidAPI marketplace)"),
) -> dict:
    """
    Validate the API key and enforce daily rate limits.
    Returns auth context dict with key_id, tier, and masked key.
    """
    raw_key = x_api_key or x_rapidapi_key

    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Pass it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, tier, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    key_id = row["id"]
    tier = row["tier"]
    is_active = row["is_active"]

    if not is_active:
        raise HTTPException(status_code=403, detail="This API key has been disabled.")

    # Enforce daily call limit
    usage = await get_usage(key_id)
    daily_limit = TIER_LIMITS.get(tier, 100)

    if usage["daily_calls"] >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily call limit of {daily_limit:,} reached for the '{tier}' tier. "
                "Upgrade your plan to continue."
            ),
        )

    return {
        "key_id": key_id,
        "tier": tier,
        "masked_key": raw_key[:8] + "..." + raw_key[-4:],
    }
