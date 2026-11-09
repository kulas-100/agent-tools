"""
API Key authentication middleware.
Supports both direct X-API-Key and RapidAPI marketplace (X-RapidAPI-Key).
Auto-registers RapidAPI subscribers and test console callers.
"""
import hashlib
from typing import Optional
from fastapi import Header, HTTPException
from app.usage import get_db, get_usage, TIER_LIMITS


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Your AgentTools API key"),
    x_rapidapi_key: Optional[str] = Header(None, alias="X-RapidAPI-Key", description="RapidAPI key"),
    x_rapidapi_user: Optional[str] = Header(None, alias="X-RapidAPI-User", description="RapidAPI username"),
    x_rapidapi_proxy_secret: Optional[str] = Header(None, alias="X-RapidAPI-Proxy-Secret", description="RapidAPI gateway secret"),
) -> dict:
    """
    Validate the API key and enforce daily rate limits.
    RapidAPI requests are automatically provisioned and tracked.
    Returns auth context dict with key_id, tier, and masked key.
    """
    raw_key = x_rapidapi_key or x_api_key

    # Check if request originated from RapidAPI proxy
    is_rapidapi = bool(x_rapidapi_key or x_rapidapi_proxy_secret)

    if not raw_key and not is_rapidapi:
        raise HTTPException(
            status_code=401,
            detail="API key required. Pass it in the X-API-Key or X-RapidAPI-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use a default identifier if raw_key wasn't passed but proxy secret was
    effective_key = raw_key or (f"rapidapi-proxy-{x_rapidapi_proxy_secret[:12]}" if x_rapidapi_proxy_secret else "anonymous")
    key_hash = hashlib.sha256(effective_key.encode()).hexdigest()

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, tier, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        )
        row = await cursor.fetchone()

        if not row:
            if is_rapidapi:
                # Auto-provision RapidAPI caller in the database
                user_label = f"rapidapi:{x_rapidapi_user or 'subscriber'}"
                cursor = await db.execute(
                    "INSERT INTO api_keys (key_hash, name, tier, is_active) VALUES (?, ?, 'pro', 1)",
                    (key_hash, user_label),
                )
                await db.commit()
                key_id = cursor.lastrowid
                tier = "pro"
                is_active = 1
            else:
                raise HTTPException(status_code=401, detail="Invalid API key.")
        else:
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

    masked = effective_key[:4] + "..." + effective_key[-4:] if len(effective_key) > 8 else "***"

    return {
        "key_id": key_id,
        "tier": tier,
        "masked_key": masked,
    }
