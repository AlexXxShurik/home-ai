import json
import logging

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — умный дом ассистент. Выполняй голосовые команды через инструменты.

Доступные инструменты:
- toggle_device(device_key, state) — включить/выключить одно устройство
- toggle_all(state) — выключить/включить ВСЕ устройства сразу
- get_device_status(device_key) — статус устройства
- list_devices() — список всех устройств

Ключи устройств:
- corridor — Коридор (свет)
- bathroom_toilet — Туалет (свет)
- bathroom_bath — Ванна (свет)
- bedroom_light — Спальня (подсветка)
- bedroom_backlight — Спальня (свет)

Отвечай ТОЛЬКО JSON в формате:
{"tool": "название_инструмента", "args": {"параметр": "значение"}}

Примеры:
- "включи свет в коридоре" → {"tool": "toggle_device", "args": {"device_key": "corridor", "state": true}}
- "выключи ванну" → {"tool": "toggle_device", "args": {"device_key": "bathroom_bath", "state": false}}
- "выключи всё" → {"tool": "toggle_all", "args": {"state": false}}
- "что включено?" → {"tool": "list_devices", "args": {}}

Отвечай кратко, только JSON без пояснений."""


def map_to_mcp_tools(llm_output: dict | list) -> list[tuple[str, dict]]:
    if isinstance(llm_output, list):
        results = []
        for item in llm_output:
            tool = item.get("tool")
            args = item.get("args", {})
            if tool:
                results.append((tool, args))
        return results
    tool = llm_output.get("tool")
    args = llm_output.get("args", {})
    if tool:
        return [(tool, args)]
    return []


class LLMClient:
    def __init__(self, base_url: str = "http://ollama:11434", model: str = "qwen2.5:3b"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.Client(base_url=base_url, timeout=30.0)

    def query(self, text: str) -> dict | None:
        payload = {
            "model": self.model,
            "prompt": text,
            "system": SYSTEM_PROMPT,
            "stream": False,
        }

        try:
            resp = self.client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "").strip()
            logger.info(f"LLM raw response: {raw}")

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass

            objects = []
            depth = 0
            start = -1
            for i, ch in enumerate(raw):
                if ch == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and start >= 0:
                        try:
                            objects.append(json.loads(raw[start:i + 1]))
                        except json.JSONDecodeError:
                            pass
                        start = -1

            if len(objects) == 1:
                return objects[0]
            elif len(objects) > 1:
                return objects
            else:
                logger.error(f"LLM returned non-JSON: {raw}")
                return None
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return None
