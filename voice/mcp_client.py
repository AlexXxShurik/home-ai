import json
import logging
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)

MCP_SERVER_SCRIPT = "server.py"


class MCPClient:
    def __init__(self, server_path: str = None, env: dict[str, str] = None):
        if server_path is None:
            server_path = str(__import__("pathlib").Path(__file__).parent.parent / "mcp_server" / "server.py")
        self.server_path = server_path
        self.env = env
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._request_id = 0

    def start(self):
        self._proc = subprocess.Popen(
            [sys.executable, self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            text=True,
        )
        self._initialize()

    def _send(self, msg: dict):
        raw = json.dumps(msg)
        self._proc.stdin.write(f"{raw}\n")
        self._proc.stdin.flush()

    def _recv(self) -> dict | None:
        line = self._proc.stdout.readline()
        if not line:
            return None
        return json.loads(line.strip())

    def _initialize(self):
        self._request_id += 1
        self._send({
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "home-ai-voice", "version": "1.0.0"},
            },
        })
        resp = self._recv()

        self._send({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })

        logger.info("MCP server initialized")

    def call_tool(self, name: str, arguments: dict) -> str | None:
        if not self._proc or self._proc.poll() is not None:
            logger.error("MCP server not running")
            return None

        with self._lock:
            try:
                self._request_id += 1
                self._send({
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                })
                resp = self._recv()
                if resp and "result" in resp:
                    content = resp["result"].get("content", [])
                    if content:
                        return content[0].get("text", "")
                logger.error(f"MCP error: {resp}")
                return None
            except Exception as e:
                logger.error(f"MCP call failed: {e}")
                return None

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
