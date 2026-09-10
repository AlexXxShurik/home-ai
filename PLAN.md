# Home AI — План проекта

## Архитектура

```
[Микрофон] → [openWakeWord] → [STT] → [Ollama qwen2.5:3b] → [MCP Server] → [FastAPI Backend] → [Tuya Devices]
```

## Сервисы

| Сервис | Описание | Стек |
|--------|----------|------|
| Frontend | Веб-интерфейс управления | Node.js + Express |
| Backend | API управления устройствами | FastAPI + Tuya Cloud |
| Voice | Wake word + STT | openWakeWord + Vosk |
| LLM | Генерация ответов и команд | Ollama + qwen2.5:3b |
| MCP | Мост между LLM и Backend | Python MCP Server |

## Этапы

### 1. Voice Service (Raspberry Pi 5)

#### Wake Word
- openWakeWord + кастомная модель `пиздюк.onnx`
- PyAudio — захват аудио с микрофона
- ONNX Runtime — инференс модели
- NumPy — обработка аудио-данных
- **Авто-определение микрофона** при старте

#### Speech-to-Text: Vosk
Почему Vosk, а не WhisperX:
- **Vosk**:轻量ный (~50MB модель), работает в реальном времени на Pi 5, отличная поддержка русского
- **WhisperX medium**: тяжёлый (~5-10с инференс), требует GPU/много RAM
- **Vosk**: модель `vosk-model-ru-0.42` (~45MB) — точность ~95% для русского

Установка:
```bash
pip install vosk sounddevice
# Модель скачивается автоматически при первом запуске
```

### 2. LLM Service (Ollama) ✅
- **Модель**: qwen2.5:3b
- Ollama в Docker (`ollama/ollama`), volume `ollama-data`
- System prompt (русский) с описанием устройств и формата команд
- Вызов через HTTP API `/api/generate` из `voice/llm.py`

### 3. MCP Server ✅
- `mcp_server/server.py` — FastMCP, stdio транспорт
- Инструменты:
  - `toggle_device(device_key, state)` — вкл/выкл устройство
  - `get_device_status(device_key)` — статус устройства
  - `list_devices()` — список всех устройств
- Интеграция с FastAPI backend через HTTP
- `voice/mcp_client.py` — синхронный клиент, подключается к MCP серверу через subprocess

### 4. Backend (модификация существующего) ✅
- `GET /api/devices/full` — список устройств с описаниями, комнатами, каналами
- `POST /api/commands` + `GET /api/commands` — логирование и история голосовых команд
- `WebSocket /ws` — реалтайм статус устройств
- `POST /api/devices/toggle_all` — выключить/включить все устройства параллельно

### 5. Frontend (модификация существующего) ✅
- Виджет голосового ассистента (индикация: слушаю/обрабатываю/ожидание)
- История последних команд
- Статус подключения Pi5 (WebSocket)
- Реалтайм обновление статуса устройств через WebSocket

---

## Зависимости (Pi 5)

```
# Voice Service
openwakeword
onnxruntime
pyaudio
numpy
vosk
sounddevice
httpx

# MCP
mcp
httpx

# Ollama
ollama/ollama (Docker image)
```

## Структура проекта

```
home-ai/
├── backend/           # FastAPI (существующий)
├── frontend/          # Node.js (существующий)
├── voice/             # Wake word + STT + LLM + MCP клиент
│   ├── main.py        # Основной цикл
│   ├── wake_word.py   # Детекция wake word
│   ├── stt.py         # Vosk STT
│   ├── llm.py         # Ollama клиент
│   ├── mcp_client.py  # MCP клиент (stdio)
│   ├── audio_manager.py
│   └── models/
│       └── пиздюк.onnx
├── mcp_server/        # MCP Server ✅
│   ├── server.py
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
├── docker-compose.yml
├── deploy.sh
└── PLAN.md
```

---

## Голосовые команды (примеры)

| Команда | Действие |
|---------|----------|
| "Пиздюк, включи свет в коридоре" | toggle corridor on |
| "Пиздюк, выключи всё" | toggle_all off |
| "Пиздюк, свет в спальне" | toggle bedroom_light on |
| "Пиздюк, выключи ванну" | toggle bathroom_bath off |
| "Пиздюк, подсветка в спальне" | toggle bedroom_backlight on |

---

## Порядок разработки

1. **Voice Service** — wake word + Vosk STT (тест на Pi5)
2. **Ollama** — установка + тест qwen2.5:3b
3. **MCP Server** — интеграция voice → LLM → backend
4. **Backend** — дополнительные эндпоинты
5. **Frontend** — виджет ассистента
6. **Оптимизация** — тестирование и доработка

---

## Docker

### Запуск всех сервисов

```bash
docker compose up -d --build
```

### Voice Service в Docker

Сервис требует доступа к аудиоустройству. На Linux (Pi5) работает с `devices` mapping:

```yaml
voice:
  build: ./voice
  container_name: simple_voice
  restart: unless-stopped
  devices:
    - "/dev/snd:/dev/snd"
  volumes:
    - ./model:/app/model
    - vosk-cache:/root/.cache/vosk
  environment:
    - OLLAMA_URL=http://ollama:11434
    - OLLAMA_MODEL=qwen2.5:3b
  depends_on:
    - ollama
```

На macOS Docker **не имеет доступа к микрофону** — voice service нужно запускать нативно:

```bash
cd voice && OLLAMA_URL=http://localhost:11434 python main.py
```

### Структура запуска

| Сервис | Запуск | Где |
|--------|--------|-----|
| Backend | `docker compose up backend` | Docker |
| Frontend | `docker compose up frontend` | Docker |
| Nginx | `docker compose up nginx` | Docker |
| Ollama | `docker compose up ollama` | Docker |
| Voice | `python voice/main.py` | Нативно (Mac/Pi5) |

### Ollama

Контейнер `ollama/ollama` с volume `ollama-data`. Модель скачивается автоматически при первом запросе или вручную:

```bash
docker exec -it simple_ollama ollama pull qwen2.5:3b
```
