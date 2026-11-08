"""
IP Info Tool — Returns geolocation and metadata for any IP address.
Uses ip-api.com (free, 45 req/min, no API key required).
"""
import httpx
from app.models import IPInfoResponse


async def get_ip_info(ip: str = None, client_host: str = None) -> IPInfoResponse:
    """
    Look up geolocation and ISP info for an IP address.
    If ip is None or empty, uses the provided client_host (request origin IP).
    """
    target_ip = ip if ip and ip.strip() else (client_host or "")

    # ip-api.com fields we want
    fields = "status,query,country,countryCode,regionName,city,lat,lon,timezone,isp"

    url = f"http://ip-api.com/json/{target_ip}" if target_ip else "http://ip-api.com/json"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params={"fields": fields})
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") == "fail":
        message = data.get("message", "Unknown error")
        raise ValueError(f"IP lookup failed: {message}")

    return IPInfoResponse(
        ip=data.get("query", target_ip or "unknown"),
        city=data.get("city"),
        region=data.get("regionName"),
        country=data.get("country"),
        country_code=data.get("countryCode"),
        latitude=data.get("lat"),
        longitude=data.get("lon"),
        timezone=data.get("timezone"),
        isp=data.get("isp"),
    )
