"""
MCP Tool Adapter.
Dynamically translates Model Context Protocol (MCP) tool schemas into
LangChain StructuredTool instances with fault-tolerant execution wrappers.
"""
import re
import json
import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import StructuredTool

from app.ai.tools.workspace import TOOL_CAPABILITY_TIERS

logger = logging.getLogger(__name__)

# JSON schema primitive type mapping to Python types
JSON_TYPE_TO_PYTHON: Dict[str, Type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def sanitize_model_name(name: str) -> str:
    """Creates a valid Python class identifier from a tool name."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    parts = [p.capitalize() for p in clean.split("_") if p]
    base = "".join(parts) or "McpTool"
    return f"{base}Args"


def json_schema_to_pydantic_model(
    tool_name: str, schema: Optional[Dict[str, Any]] = None
) -> Type[BaseModel]:
    """
    Dynamically constructs a Pydantic BaseModel representing the tool's inputSchema.
    Supports strings, numbers, integers, booleans, arrays, objects, and optional defaults.
    """
    model_name = sanitize_model_name(tool_name)

    if not schema or not isinstance(schema, dict):
        return create_model(model_name)

    properties: Dict[str, Any] = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    if not properties:
        return create_model(model_name)

    fields: Dict[str, Any] = {}

    for field_name, field_spec in properties.items():
        if not isinstance(field_spec, dict):
            field_spec = {}

        field_type_str = field_spec.get("type", "any")
        base_python_type = JSON_TYPE_TO_PYTHON.get(field_type_str, Any)
        description = field_spec.get("description", "")
        default_val = field_spec.get("default", None)

        is_required = field_name in required_fields

        if is_required:
            field_type = base_python_type
            field_default = Field(..., description=description)
        else:
            field_type = Optional[base_python_type]
            field_default = Field(default=default_val, description=description)

        fields[field_name] = (field_type, field_default)

    return create_model(model_name, **fields)


def format_mcp_content(result: Any) -> str:
    """
    Normalizes an MCP tool call result into a clean string representation.
    Extracts text from content blocks, handles errors, and parses JSON output.
    """
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        is_error = result.get("isError", False)
        content_list = result.get("content")

        if isinstance(content_list, list):
            text_parts = []
            for item in content_list:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "resource":
                        res = item.get("resource", {})
                        text_parts.append(res.get("text", str(res)))
                    else:
                        text_parts.append(json.dumps(item))
                else:
                    text_parts.append(str(item))

            joined = "\n".join(text_parts).strip()
            if is_error:
                raise RuntimeError(joined or "MCP tool returned error status")
            return joined

        if "text" in result:
            return str(result["text"])

        return json.dumps(result)

    return str(result)


def mcp_tool_to_structured_tool(
    client: Any,
    tool_info: Dict[str, Any],
    server_name: str,
    capability_tier: int = 1,
) -> StructuredTool:
    """
    Dynamically converts an MCP tool definition into a LangChain StructuredTool.
    Wraps execution with complete fault tolerance so network drops, timeouts,
    or process exits return a clean error string without crashing the agent.
    """
    name = tool_info.get("name", "unnamed_tool")
    description = tool_info.get("description") or f"MCP tool from server '{server_name}'"
    input_schema = tool_info.get("inputSchema", {})

    args_model = json_schema_to_pydantic_model(name, input_schema)

    def run_mcp_tool(**kwargs) -> str:
        """Invokes the underlying MCP tool with fault tolerance."""
        try:
            raw_result = client.call_tool(name, kwargs)
            return format_mcp_content(raw_result)
        except Exception as exc:
            err_msg = str(exc)
            logger.error(
                "Error executing MCP tool '%s' on server '%s': %s",
                name,
                server_name,
                err_msg,
            )
            return f"Error from MCP server '{server_name}': {err_msg}"

    run_mcp_tool.__doc__ = description

    structured_tool = StructuredTool.from_function(
        func=run_mcp_tool,
        name=name,
        description=description,
        args_schema=args_model,
    )

    # Register in GPTCraft tool capability tier map (Tier 1 read-only by default)
    TOOL_CAPABILITY_TIERS[name] = capability_tier

    return structured_tool
