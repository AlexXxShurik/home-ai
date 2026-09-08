import os

import tinytuya
from fastapi import FastAPI, HTTPException
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

TUYA_ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
TUYA_ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET")
TUYA_REGION = os.getenv("TUYA_REGION", "eu")

DEVICES = {
    "corridor": {
        "id": os.getenv("TUYA_DEVICE_CORRIDOR"),
        "name": "Коридор",
        "channels": [{"code": "switch_1", "label": "Свет"}],
    },
    "bathroom_toilet": {
        "id": os.getenv("TUYA_DEVICE_BATHROOM"),
        "name": "Туалет",
        "channels": [{"code": "switch_2", "label": "Свет"}],
    },
    "bathroom_bath": {
        "id": os.getenv("TUYA_DEVICE_BATHROOM"),
        "name": "Ванна",
        "channels": [{"code": "switch_1", "label": "Свет"}],
    },
    "bedroom_light": {
        "id": os.getenv("TUYA_DEVICE_SPALNYA"),
        "name": "Подсветка",
        "channels": [{"code": "switch_1", "label": "Подсветка"}],
    },
    "bedroom_backlight": {
        "id": os.getenv("TUYA_DEVICE_SPALNYA"),
        "name": "Свет",
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
