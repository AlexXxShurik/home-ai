import os
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import tinytuya
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Home AI API")

allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMMAND_LOG: deque[dict] = deque(maxlen=50)
ws_clients: set[WebSocket] = set()

TUYA_ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
TUYA_ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET")
TUYA_REGION = os.getenv("TUYA_REGION", "eu")

DEVICES = {
    "corridor": {
        "id": os.getenv("TUYA_DEVICE_CORRIDOR"),
        "name": "Коридор",
        "room": "Коридор",
        "channels": [{"code": "switch_1", "label": "Свет"}],
    },
    "bathroom_toilet": {
        "id": os.getenv("TUYA_DEVICE_BATHROOM"),
        "name": "Туалет",
        "room": "Ванная",
        "channels": [{"code": "switch_2", "label": "Свет"}],
    },
    "bathroom_bath": {
        "id": os.getenv("TUYA_DEVICE_BATHROOM"),
        "name": "Ванна",
        "room": "Ванная",
        "channels": [{"code": "switch_1", "label": "Свет"}],
    },
    "bedroom_light": {
        "id": os.getenv("TUYA_DEVICE_SPALNYA"),
        "name": "Подсветка",
        "room": "Спальня",
        "channels": [{"code": "switch_1", "label": "Подсветка"}],
    },
    "bedroom_backlight": {
        "id": os.getenv("TUYA_DEVICE_SPALNYA"),
        "name": "Свет",
        "room": "Спальня",
        "channels": [{"code": "switch_2", "label": "Свет"}],
    },
}


def get_cloud():
    return tinytuya.Cloud(
        apiKey=TUYA_ACCESS_ID,
        apiSecret=TUYA_ACCESS_SECRET,
        apiRegion=TUYA_REGION,
    )


class ToggleRequest(BaseModel):
    state: bool


@app.get("/api/devices")
def list_devices():
    cloud = get_cloud()
    result = []
    for key, device in DEVICES.items():
        try:
            status = cloud.getstatus(device["id"])
            is_on = False
            if status.get("success") and status.get("result"):
                for item in status["result"]:
                    if item["code"] == device["channels"][0]["code"]:
                        is_on = item["value"]
                        break
            result.append({
                "key": key,
                "name": device["name"],
                "online": True,
                "is_on": is_on,
            })
        except Exception:
            result.append({
                "key": key,
                "name": device["name"],
                "online": False,
                "is_on": False,
            })
    return result


@app.post("/api/devices/{device_key}/toggle")
def toggle_device(device_key: str, req: ToggleRequest):
    if device_key not in DEVICES:
        raise HTTPException(status_code=404, detail="Device not found")

    device = DEVICES[device_key]
    cloud = get_cloud()

    try:
        result = cloud.sendcommand(
            device["id"],
            {"commands": [{"code": device["channels"][0]["code"], "value": req.state}]},
        )
        if not result.get("success"):
            raise HTTPException(status_code=502, detail=result.get("Error", "Tuya API error"))
        return {"success": True, "state": req.state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/devices/{device_key}/status")
def device_status(device_key: str):
    if device_key not in DEVICES:
        raise HTTPException(status_code=404, detail="Device not found")

    device = DEVICES[device_key]
    cloud = get_cloud()

    try:
        status = cloud.getstatus(device["id"])
        is_on = False
        if status.get("success") and status.get("result"):
            for item in status["result"]:
                if item["code"] == device["channels"][0]["code"]:
                    is_on = item["value"]
                    break
        return {"key": device_key, "name": device["name"], "is_on": is_on, "online": True}
    except Exception:
        return {"key": device_key, "name": device["name"], "is_on": False, "online": False}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI Backend!", "status": "success"}


@app.get("/api/devices/full")
def list_devices_full():
    cloud = get_cloud()
    result = []
    for key, device in DEVICES.items():
        try:
            status = cloud.getstatus(device["id"])
            is_on = False
            if status.get("success") and status.get("result"):
                for item in status["result"]:
                    if item["code"] == device["channels"][0]["code"]:
                        is_on = item["value"]
                        break
            result.append({
                "key": key,
                "name": device["name"],
                "room": device.get("room", ""),
                "channels": device["channels"],
                "tuya_id": device["id"],
                "online": True,
                "is_on": is_on,
            })
        except Exception:
            result.append({
                "key": key,
                "name": device["name"],
                "room": device.get("room", ""),
                "channels": device["channels"],
                "tuya_id": device["id"],
                "online": False,
                "is_on": False,
            })
    return result


@app.get("/api/commands")
def get_commands():
    return list(COMMAND_LOG)


@app.post("/api/commands")
def log_command(cmd: dict):
    entry = {"text": cmd.get("text", ""), "tool": cmd.get("tool", ""), "result": cmd.get("result", ""), "ts": time.time()}
    COMMAND_LOG.appendleft(entry)
    return {"ok": True}


async def broadcast_status():
    if not ws_clients:
        return
    cloud = get_cloud()
    statuses = []
    for key, device in DEVICES.items():
        try:
            status = cloud.getstatus(device["id"])
            is_on = False
            if status.get("success") and status.get("result"):
                for item in status["result"]:
                    if item["code"] == device["channels"][0]["code"]:
                        is_on = item["value"]
                        break
            statuses.append({"key": key, "is_on": is_on, "online": True})
        except Exception:
            statuses.append({"key": key, "is_on": False, "online": False})
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json({"type": "status", "devices": statuses})
        except Exception:
            dead.add(ws)
    ws_clients -= dead


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(ws)


@app.post("/api/devices/toggle_all")
def toggle_all(req: ToggleRequest):
    cloud = get_cloud()

    def send_cmd(key, device):
        try:
            cloud.sendcommand(
                device["id"],
                {"commands": [{"code": device["channels"][0]["code"], "value": req.state}]},
            )
            return {"key": key, "success": True}
        except Exception as e:
            return {"key": key, "success": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda item: send_cmd(*item), DEVICES.items()))

    return {"state": req.state, "results": results}
