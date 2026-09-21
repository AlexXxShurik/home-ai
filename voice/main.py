import sys
import signal
import logging
import os
from pathlib import Path

import httpx

from audio_manager import AudioManager, find_microphone
from wake_word import WakeWordDetector
from stt import SpeechToText
from llm import LLMClient, map_to_mcp_tools
from mcp_client import MCPClient

try:
    from openwakeword.utils import download_models
except ImportError:
    download_models = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WAKE_WORD_MODEL = Path(__file__).parent.parent / "model" / "wakeword.onnx"
WAKE_WORD_THRESHOLD = 0.3
CONSECUTIVE_DETECTIONS = 2
STT_MODEL = "vosk-model-small-ru-0.22"
MAX_SPEECH_DURATION = 10.0


def main():
    if not WAKE_WORD_MODEL.exists():
        logger.error(f"Wake word model not found: {WAKE_WORD_MODEL}")
        sys.exit(1)

    logger.info("Downloading openwakeword models if needed...")
    if download_models:
        download_models()

    device_index = find_microphone()
    if device_index is None:
        logger.error("No microphone found!")
        sys.exit(1)

    audio = AudioManager(device_index)
    audio.open()

    wake_word = WakeWordDetector(str(WAKE_WORD_MODEL), audio, WAKE_WORD_THRESHOLD)
    stt = SpeechToText(STT_MODEL, audio)

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    llm = LLMClient(base_url=ollama_url, model=ollama_model)

    mcp_server_path = os.getenv("MCP_SERVER_PATH", str(Path(__file__).parent.parent / "mcp_server" / "server.py"))
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    mcp_env = {**os.environ, "BACKEND_URL": backend_url}
    mcp = MCPClient(server_path=mcp_server_path, env=mcp_env)
    http = httpx.Client(timeout=5.0)
    try:
        mcp.start()
        logger.info("MCP client started")
    except Exception as e:
        logger.error(f"Failed to start MCP client: {e}")
        sys.exit(1)

    running = True

    def shutdown(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    skip_wake = os.getenv("SKIP_WAKE_WORD", "0") == "1"

    if skip_wake:
        logger.info("Wake word skipped — listening for commands directly...")
    else:
        logger.info("Listening for wake word...")

    consecutive = 0

    def handle_command(text):
        logger.info(f"Transcribed: {text}")
        result = llm.query(text)
        if result:
            logger.info(f"LLM output: {result}")
            tools = map_to_mcp_tools(result)
            if tools:
                for tool_name, tool_args in tools:
                    logger.info(f"MCP call: {tool_name}({tool_args})")
                    mcp_result = mcp.call_tool(tool_name, tool_args)
                    logger.info(f"MCP result: {mcp_result}")
                    print(f"RESULT:{mcp_result}", flush=True)
                    try:
                        http.post(f"{backend_url}/api/commands", json={
                            "text": text, "tool": tool_name, "result": mcp_result or "",
                        })
                    except Exception:
                        pass
            else:
                logger.warning(f"Could not map to MCP tools: {result}")
        else:
            logger.warning("LLM returned no valid output")

    try:
        if skip_wake:
            while running:
                print("Speak...", flush=True)
                text = stt.transcribe(MAX_SPEECH_DURATION)
                if text:
                    handle_command(text)
        else:
            tick = 0
            while running:
                detected, score = wake_word.listen()
                tick += 1
                if tick % 10 == 0:
                    logger.info(f"Wake word: score={score:.4f} threshold={WAKE_WORD_THRESHOLD} consecutive={consecutive}")
                if detected:
                    consecutive += 1
                    logger.info(f"Wake word DETECTED! score={score:.4f} consecutive={consecutive}/{CONSECUTIVE_DETECTIONS}")
                    if consecutive >= CONSECUTIVE_DETECTIONS:
                        consecutive = 0
                        wake_word.reset()
                        print("Speak...", flush=True)
                        text = stt.transcribe(MAX_SPEECH_DURATION)
                        if text:
                            handle_command(text)
                        else:
                            logger.info("No speech detected after wake word")
                else:
                    consecutive = 0
    finally:
        mcp.stop()
        audio.close()


if __name__ == "__main__":
    main()
