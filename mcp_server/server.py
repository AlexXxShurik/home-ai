import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Home AI MCP")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


@mcp.tool()
def toggle_device(device_key: str, state: bool) -> str:
    """Включить или выключить устройство.

    Args:
        device_key: Ключ устройства (corridor, bathroom_toilet, bathroom_bath, bedroom_light, bedroom_backlight)
        state: true — включить, false — выключить
    """
    try:
        resp = httpx.post(
            f"{BACKEND_URL}/api/devices/{device_key}/toggle",
            json={"state": state},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_device_status(device_key: str) -> str:
    """Получить статус устройства.

    Args:
        device_key: Ключ устройства (corridor, bathroom_toilet, bathroom_bath, bedroom_light, bedroom_backlight)
    """
    try:
        resp = httpx.get(
            f"{BACKEND_URL}/api/devices/{device_key}/status",
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_devices() -> str:
    """Получить список всех устройств и их статусов."""
    try:
        resp = httpx.get(
            f"{BACKEND_URL}/api/devices",
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def toggle_all(state: bool) -> str:
    """Выключить или включить все устройства сразу.

    Args:
        state: true — включить все, false — выключить все
    """
    try:
        resp = httpx.post(
            f"{BACKEND_URL}/api/devices/toggle_all",
            json={"state": state},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
