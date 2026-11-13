"""
Mock Model Context Protocol (MCP) Server.
Implements JSON-RPC 2.0 stdio transport protocol for testing and local development.
"""
import sys
import json
import time


def main():
    while True:
        try:
            line = sys.stdin.readline()
        except Exception:
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "mock-mcp-server",
                        "version": "1.0.0",
                    },
                },
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            # Initialized notification from client - no response required
            continue

        elif method == "tools/list":
            tools = [
                {
                    "name": "mock_echo",
                    "description": "Echoes back the provided message",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message to echo",
                            }
                        },
                        "required": ["message"],
                    },
                },
                {
                    "name": "mock_add",
                    "description": "Adds two numbers together",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"},
                        },
                        "required": ["a", "b"],
                    },
                },
                {
                    "name": "mock_fail",
                    "description": "Simulates a tool that returns an error",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Reason for failure",
                                "default": "Simulated tool execution error",
                            }
                        },
                    },
                },
                {
                    "name": "mock_slow",
                    "description": "Simulates a slow operation that sleeps",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "seconds": {
                                "type": "number",
                                "description": "Seconds to sleep",
                                "default": 2,
                            }
                        },
                    },
                },
            ]
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools},
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "mock_echo":
                msg = args.get("message", "")
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Echo: {msg}"}],
                        "isError": False,
                    },
                }
            elif name == "mock_add":
                try:
                    a = float(args.get("a", 0))
                    b = float(args.get("b", 0))
                    val = int(a + b) if (a.is_integer() and b.is_integer()) else (a + b)
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": str(val)}],
                            "isError": False,
                        },
                    }
                except Exception as exc:
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Calculation error: {exc}"}],
                            "isError": True,
                        },
                    }
            elif name == "mock_fail":
                reason = args.get("reason", "Simulated tool execution error")
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(reason)}],
                        "isError": True,
                    },
                }
            elif name == "mock_slow":
                sec = float(args.get("seconds", 2))
                time.sleep(sec)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Completed after {sec}s"}],
                        "isError": False,
                    },
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{name}' not found",
                    },
                }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        else:
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found",
                },
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
