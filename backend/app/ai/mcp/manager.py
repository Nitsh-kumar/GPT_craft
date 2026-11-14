"""
Model Context Protocol (MCP) Client Manager.
Provides an extensible manager for external MCP servers via stdio and sse transports,
handling process lifecycles, JSON-RPC 2.0 message exchange, timeouts, and tool federation.
"""
import os
import sys
import json
import time
import queue
import atexit
import shutil
import logging
import threading
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool

from app.ai.mcp.adapter import mcp_tool_to_structured_tool
from app.ai.tools.workspace import get_workspace_root

logger = logging.getLogger(__name__)

DEFAULT_RPC_TIMEOUT_SECONDS = 10.0


class MCPError(Exception):
    """Base exception for all MCP-related failures."""
    pass


class MCPTimeoutError(MCPError, TimeoutError):
    """Raised when an MCP JSON-RPC call exceeds its configured timeout."""
    pass


class MCPConnectionError(MCPError, ConnectionError):
    """Raised when communication with an MCP server subprocess or endpoint fails."""
    pass


def get_backend_dir() -> Path:
    """Resolves the backend directory to ensure clean subprocess imports."""
    ws = get_workspace_root()
    if (ws / "backend").exists() and (ws / "backend").is_dir():
        return (ws / "backend").resolve()
    if (ws / "app").exists() and (ws / "app").is_dir():
        return ws.resolve()
    # Fallback to current file hierarchy
    file_dir = Path(__file__).resolve()
    if len(file_dir.parents) >= 4:
        return file_dir.parents[3].resolve()
    return Path.cwd().resolve()


class BaseMCPClient:
    """Abstract base class for MCP transport clients."""

    def __init__(self, server_name: str, timeout: float = DEFAULT_RPC_TIMEOUT_SECONDS):
        self.server_name = server_name
        self.timeout = timeout

    def connect(self) -> None:
        raise NotImplementedError

    def initialize(self) -> Dict[str, Any]:
        raise NotImplementedError

    def list_tools(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        raise NotImplementedError

    def is_alive(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class StdioMCPClient(BaseMCPClient):
    """
    Spawns and manages a local MCP server subprocess communicating via JSON-RPC 2.0 over stdio.
    Enforces atomic thread-safe requests, background line reading, and per-call timeouts.
    """

    def __init__(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path | str] = None,
        timeout: float = DEFAULT_RPC_TIMEOUT_SECONDS,
    ):
        super().__init__(server_name=server_name, timeout=timeout)
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.cwd = cwd

        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._queue: queue.Queue = queue.Queue()
        self._request_id = 0
        self._lock = threading.Lock()
        self._is_initialized = False
        self._server_info: Dict[str, Any] = {}
        self._capabilities: Dict[str, Any] = {}

    def _resolve_command(self) -> str:
        """Resolves the executable path, using the active Python environment if 'python' is requested."""
        cmd = self.command.strip()
        if cmd in ("python", "python3", "python.exe") and sys.executable:
            return sys.executable
        resolved = shutil.which(cmd)
        return resolved if resolved else cmd

    def connect(self) -> None:
        """Spawns the local MCP stdio subprocess and begins background stdout capture."""
        if self._process and self.is_alive():
            return

        cmd = self._resolve_command()
        full_cmd = [cmd] + self.args

        # Set up environment with backend on PYTHONPATH
        backend_dir = get_backend_dir()
        process_env = os.environ.copy()
        process_env.update(self.env)
        process_env["PYTHONUNBUFFERED"] = "1"
        process_env["PYTHONPATH"] = (
            f"{backend_dir}{os.pathsep}{process_env.get('PYTHONPATH', '')}"
        )

        resolved_cwd = Path(self.cwd).resolve() if self.cwd else backend_dir

        try:
            self._process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(resolved_cwd),
                env=process_env,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            raise MCPConnectionError(
                f"Failed to spawn MCP server '{self.server_name}' with command '{cmd}': {exc}"
            ) from exc

        # Flush queue and start background reader thread
        self._queue = queue.Queue()
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name=f"mcp-stdio-{self.server_name}",
            daemon=True,
        )
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        """Reads newline-delimited JSON-RPC messages from subprocess stdout into the message queue."""
        proc = self._process
        if not proc or not proc.stdout:
            self._queue.put(None)
            return

        try:
            for line in proc.stdout:
                if line:
                    self._queue.put(line)
        except Exception as exc:
            self._queue.put(exc)
        finally:
            self._queue.put(None)

    def is_alive(self) -> bool:
        """Checks if the subprocess is currently running."""
        return self._process is not None and self._process.poll() is None

    def _send_rpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Sends a JSON-RPC 2.0 request and synchronously blocks for the response
        up to the specified timeout.
        """
        if not self.is_alive():
            raise MCPConnectionError(
                f"MCP server '{self.server_name}' process is not running."
            )

        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params if params is not None else {},
            }
            raw_payload = json.dumps(payload) + "\n"

            try:
                assert self._process and self._process.stdin
                self._process.stdin.write(raw_payload)
                self._process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise MCPConnectionError(
                    f"Failed writing to MCP server '{self.server_name}' stdin: {exc}"
                ) from exc

            # Read from queue until matching response arrives or timeout occurs
            call_timeout = timeout if timeout is not None else self.timeout
            deadline = time.time() + call_timeout

            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise MCPTimeoutError(
                        f"Request '{method}' to MCP server '{self.server_name}' timed out after {call_timeout} seconds"
                    )

                try:
                    item = self._queue.get(timeout=max(0.01, remaining))
                except queue.Empty:
                    raise MCPTimeoutError(
                        f"Request '{method}' to MCP server '{self.server_name}' timed out after {call_timeout} seconds"
                    )

                if item is None:
                    # Subprocess closed pipe or exited
                    stderr_msg = ""
                    if self._process and self._process.stderr:
                        try:
                            stderr_msg = self._process.stderr.read().strip()
                        except Exception:
                            pass
                    err_info = f" STDERR: {stderr_msg}" if stderr_msg else ""
                    raise MCPConnectionError(
                        f"MCP server '{self.server_name}' process closed stdout unexpectedly.{err_info}"
                    )

                if isinstance(item, Exception):
                    raise MCPConnectionError(
                        f"Error reading from MCP server '{self.server_name}': {item}"
                    ) from item

                line = str(item).strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # Ignore non-JSON log lines from subprocess stdout
                    continue

                if isinstance(data, dict):
                    # Check for response matching current request id
                    if data.get("id") == req_id:
                        if "error" in data:
                            err_obj = data["error"]
                            err_msg = (
                                err_obj.get("message", str(err_obj))
                                if isinstance(err_obj, dict)
                                else str(err_obj)
                            )
                            raise MCPError(f"MCP server error: {err_msg}")
                        return data.get("result", {})

    def initialize(self) -> Dict[str, Any]:
        """Performs MCP initialize handshake and sends initialized notification."""
        if not self.is_alive():
            self.connect()

        result = self._send_rpc(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gptcraft", "version": "1.0.0"},
            },
        )
        self._is_initialized = True
        self._server_info = result.get("serverInfo", {})
        self._capabilities = result.get("capabilities", {})

        # Send notifications/initialized (no response expected)
        try:
            if self.is_alive() and self._process and self._process.stdin:
                notif = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
                self._process.stdin.write(json.dumps(notif) + "\n")
                self._process.stdin.flush()
        except Exception:
            pass

        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """Queries the MCP server for available tool schemas via tools/list."""
        if not self._is_initialized:
            self.initialize()
        result = self._send_rpc(method="tools/list", params={})
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Invokes an MCP tool on the server via tools/call."""
        if not self._is_initialized:
            self.initialize()
        return self._send_rpc(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments or {}},
        )

    def close(self) -> None:
        """Gracefully terminates the subprocess and closes all streams."""
        proc = self._process
        self._process = None
        self._is_initialized = False

        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)
            except Exception:
                pass
        if proc:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass


class SSEMCPClient(BaseMCPClient):
    """
    Connects to a remote MCP server via HTTP / Server-Sent Events (SSE).
    """

    def __init__(
        self,
        server_name: str,
        url: str,
        timeout: float = DEFAULT_RPC_TIMEOUT_SECONDS,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(server_name=server_name, timeout=timeout)
        self.url = url
        self.headers = dict(headers or {})
        self._request_id = 0
        self._is_initialized = False
        self._client: Optional[Any] = None

    def connect(self) -> None:
        import httpx
        self._client = httpx.Client(timeout=self.timeout, headers=self.headers)

    def is_alive(self) -> bool:
        return self._client is not None

    def _send_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        import httpx

        if self._client is None:
            self.connect()

        self._request_id += 1
        req_id = self._request_id
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }

        try:
            resp = self._client.post(self.url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise MCPTimeoutError(
                f"HTTP request to MCP server '{self.server_name}' timed out after {self.timeout}s"
            ) from exc
        except Exception as exc:
            raise MCPConnectionError(
                f"HTTP error communicating with MCP server '{self.server_name}': {exc}"
            ) from exc

        if isinstance(data, dict):
            if "error" in data:
                err_obj = data["error"]
                err_msg = (
                    err_obj.get("message", str(err_obj))
                    if isinstance(err_obj, dict)
                    else str(err_obj)
                )
                raise MCPError(f"MCP server error: {err_msg}")
            return data.get("result", {})

        return {}

    def initialize(self) -> Dict[str, Any]:
        result = self._send_rpc(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gptcraft", "version": "1.0.0"},
            },
        )
        self._is_initialized = True
        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        if not self._is_initialized:
            self.initialize()
        result = self._send_rpc(method="tools/list", params={})
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if not self._is_initialized:
            self.initialize()
        return self._send_rpc(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments or {}},
        )

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._is_initialized = False


class MCPManager:
    """
    Orchestrates the lifecycle of configured Model Context Protocol (MCP) clients,
    dynamically converts their discovered schemas to LangChain StructuredTools,
    and isolates the agent runtime from external process crashes or timeouts.
    """

    def __init__(self, config_path: Optional[Path | str] = None):
        self.config_path = Path(config_path) if config_path else None
        self._clients: Dict[str, BaseMCPClient] = {}
        self._tools: Dict[str, StructuredTool] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def find_config_path(self) -> Optional[Path]:
        """Resolves the active mcp_servers.json path across common project locations."""
        if self.config_path and self.config_path.exists():
            return self.config_path

        env_path = os.getenv("MCP_SERVERS_CONFIG_PATH")
        if env_path:
            p = Path(env_path).resolve()
            if p.exists():
                return p

        # Check relative to backend dir
        backend_dir = get_backend_dir()
        candidate = backend_dir / "mcp_servers.json"
        if candidate.exists():
            return candidate

        # Check relative to cwd
        cwd_candidate = Path.cwd() / "mcp_servers.json"
        if cwd_candidate.exists():
            return cwd_candidate

        # Check relative to repo root
        ws = get_workspace_root()
        ws_candidate = ws / "backend" / "mcp_servers.json"
        if ws_candidate.exists():
            return ws_candidate

        return candidate  # Default expected target

    def load_config(self, path: Optional[Path | str] = None) -> Dict[str, Any]:
        """
        Parses mcp_servers.json into a dictionary of server configurations.
        Returns an empty server mapping if the configuration file is absent or empty.
        """
        target_path = Path(path) if path else self.find_config_path()
        if not target_path or not target_path.exists():
            return {"mcpServers": {}}

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {"mcpServers": {}}
                data = json.loads(content)
                if not isinstance(data, dict):
                    return {"mcpServers": {}}
                if "mcpServers" not in data:
                    data = {"mcpServers": data}
                return data
        except Exception as exc:
            logger.warning(
                "Failed to parse MCP server config from '%s': %s", target_path, exc
            )
            return {"mcpServers": {}}

    def register_server(
        self,
        name: str,
        config: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> List[StructuredTool]:
        """
        Instantiates, connects to, and adapts an individual MCP server definition.
        Returns the list of translated StructuredTool instances.
        """
        transport = config.get("transport", "stdio").lower()
        effective_timeout = (
            timeout
            if timeout is not None
            else config.get("timeout", DEFAULT_RPC_TIMEOUT_SECONDS)
        )
        tier = config.get("tier", 1)

        client: BaseMCPClient
        if transport == "stdio":
            command = config.get("command", "python")
            args = config.get("args", [])
            env = config.get("env", {})
            cwd = config.get("cwd")
            client = StdioMCPClient(
                server_name=name,
                command=command,
                args=args,
                env=env,
                cwd=cwd,
                timeout=effective_timeout,
            )
        elif transport == "sse":
            url = config.get("url", "")
            headers = config.get("headers", {})
            client = SSEMCPClient(
                server_name=name,
                url=url,
                timeout=effective_timeout,
                headers=headers,
            )
        else:
            logger.warning(
                "Unsupported MCP transport '%s' for server '%s'. Skipping.",
                transport,
                name,
            )
            return []

        # Connect and list tools with fault tolerance
        try:
            client.connect()
            tools_list = client.list_tools()
        except Exception as exc:
            logger.warning(
                "Failed to connect or discover tools from MCP server '%s': %s",
                name,
                exc,
            )
            client.close()
            return []

        discovered_tools: List[StructuredTool] = []
        for tool_info in tools_list:
            try:
                st = mcp_tool_to_structured_tool(
                    client=client,
                    tool_info=tool_info,
                    server_name=name,
                    capability_tier=tier,
                )
                self._tools[st.name] = st
                discovered_tools.append(st)
            except Exception as exc:
                logger.warning(
                    "Failed to adapt tool '%s' from MCP server '%s': %s",
                    tool_info.get("name"),
                    name,
                    exc,
                )

        self._clients[name] = client
        return discovered_tools

    def initialize_servers(
        self, config_path: Optional[Path | str] = None
    ) -> Dict[str, StructuredTool]:
        """Loads configuration and initializes all declared MCP servers."""
        with self._lock:
            config = self.load_config(config_path)
            servers = config.get("mcpServers", {})

            for name, s_config in servers.items():
                if not isinstance(s_config, dict) or s_config.get("disabled"):
                    continue
                if name not in self._clients:
                    self.register_server(name, s_config)

            self._initialized = True
            return self._tools

    def get_tools(self, force_reload: bool = False) -> List[StructuredTool]:
        """Returns the list of active LangChain StructuredTool instances from MCP."""
        if not self._initialized or force_reload:
            self.initialize_servers()
        return list(self._tools.values())

    def unregister_server(self, name: str) -> None:
        """Closes an active MCP server client and removes its registered tools."""
        with self._lock:
            client = self._clients.pop(name, None)
            if client:
                client.close()
            # Remove any tools belonging to this server (tools usually match or map)
            # Rebuilding tool map
            surviving_tools = {}
            for t_name, tool in self._tools.items():
                if f"from server '{name}'" not in tool.description:
                    surviving_tools[t_name] = tool
            self._tools = surviving_tools

    def close(self) -> None:
        """Closes all active MCP clients and releases resources."""
        with self._lock:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
            self._tools.clear()
            self._initialized = False


# Global singleton instance
mcp_manager = MCPManager()

# Ensure background subprocesses are terminated upon process exit
atexit.register(mcp_manager.close)
