from __future__ import annotations

import json
from typing import Tuple
from contextlib import AsyncExitStack

from fastmcp import Client
from fastmcp.client import SSETransport, StreamableHttpTransport
from fastmcp.client.messages import MessageHandler
import mcp.types as types
import httpx

JsonStrPair = Tuple[str, str]

# Global client state
_client_session: Client | None = None
_client_exit_stack: AsyncExitStack | None = None
_notifications: list[dict] = []
_roots: list[str] = []
_active_headers: dict[str, str] = {}

class InspectorMessageHandler(MessageHandler):
    async def _add_notification(self, method: str, params: dict | None = None):
        _notifications.insert(0, {
            "method": method,
            "params": params or {}
        })

    async def on_notification(self, notification: types.ServerNotification) -> None:
        # Generic notification handler
        params = notification.params.model_dump(mode='json') if notification.params else {}
        await self._add_notification(notification.method, params)

    async def on_tool_list_changed(self, notification: types.ToolListChangedNotification) -> None:
        await self._add_notification("notifications/tools/list_changed")

    async def on_resource_list_changed(self, notification: types.ResourceListChangedNotification) -> None:
        await self._add_notification("notifications/resources/list_changed")

    async def on_prompt_list_changed(self, notification: types.PromptListChangedNotification) -> None:
        await self._add_notification("notifications/prompts/list_changed")
        
    async def on_progress(self, notification: types.ProgressNotification) -> None:
        params = notification.model_dump(mode='json')
        await self._add_notification("notifications/progress", params)
        
    async def on_logging_message(self, notification: types.LoggingMessageNotification) -> None:
        params = notification.model_dump(mode='json')
        await self._add_notification("notifications/message", params)



async def roots_handler(context=None) -> list[str]:
    """Callback for providing roots to the server."""
    return _roots

def set_roots(roots: list[str]):
    """Update the available roots."""
    global _roots
    _roots = roots

async def connect(base_url: str, timeout_seconds: float, transport_type: str, sampling_handler=None, auth=None, headers: dict[str, str] | None = None):
    global _client_session, _client_exit_stack, _active_headers
    await disconnect()
    
    _client_exit_stack = AsyncExitStack()
    _active_headers = {}
    if headers:
        _active_headers = headers.copy()
    if isinstance(auth, str) and "Authorization" not in _active_headers:
        _active_headers["Authorization"] = f"Bearer {auth}"
    
    transport_kwargs = {}
    if headers:
        transport_kwargs["headers"] = headers
    
    if transport_type == "Streamable HTTP":
        transport = StreamableHttpTransport(base_url, **transport_kwargs)
    else:
        # Default to SSE
        transport = SSETransport(base_url, **transport_kwargs)
        
    client = Client(
        transport=transport, 
        timeout=timeout_seconds, 
        sampling_handler=sampling_handler, 
        auth=auth,
        message_handler=InspectorMessageHandler(),
        roots=roots_handler
    )
    # Enter the async context to establish connection
    _client_session = await _client_exit_stack.enter_async_context(client)
    return _client_session


def get_notifications() -> list[dict]:
    return _notifications

def clear_notifications():
    global _notifications
    _notifications = []

async def disconnect():
    global _client_session, _client_exit_stack, _active_headers
    if _client_exit_stack:
        await _client_exit_stack.aclose()
    _client_session = None
    _client_exit_stack = None
    _active_headers = {}


def _get_client() -> Client:
    if _client_session is None:
        raise RuntimeError("Client not connected. Please connect first.")
    return _client_session


async def list_resources(base_url: str, timeout_seconds: float, sampling_handler=None) -> tuple[str, str, list[str]]:
    try:
        client = _get_client()
        result = await client.session.list_resources()
        resources = result.resources
        # Convert Pydantic models to list of dicts then to formatted JSON
        resources_data = [r.model_dump(mode='json') for r in resources]
        request_json = json.dumps({"method": "resources/list", "params": {}}, indent=2)
        response_json = json.dumps(resources_data, indent=2)
        return request_json, response_json, resources_data
    except Exception as e:
        return "Error", str(e), []


async def list_resource_templates(base_url: str, timeout_seconds: float, sampling_handler=None) -> tuple[str, str, list[str]]:
    try:
        client = _get_client()
        result = await client.session.list_resource_templates()
        templates = result.resourceTemplates
        templates_data = [t.model_dump(mode='json') for t in templates]
        request_json = json.dumps({"method": "resources/templates/list", "params": {}}, indent=2)
        response_json = json.dumps(templates_data, indent=2)
        return request_json, response_json, templates_data
    except Exception as e:
        return "Error", str(e), []


async def read_resource(base_url: str, timeout_seconds: float, resource_uri: str, sampling_handler=None) -> JsonStrPair:
    if not resource_uri:
        return "", "Select a resource first."
    try:
        client = _get_client()
        result = await client.session.read_resource(uri=resource_uri)
        # The result has a contents field which is a list
        contents_data = [c.model_dump(mode='json') for c in result.contents]
        request_json = json.dumps({"method": "resources/list", "params": {"uri": resource_uri}}, indent=2)
        response_json = json.dumps({"contents": contents_data}, indent=2)
        return request_json, response_json
    except Exception as e:
        return "Error", str(e)


async def list_prompts(base_url: str, timeout_seconds: float, sampling_handler=None) -> tuple[str, str, list[str]]:
    try:
        client = _get_client()
        prompts = await client.list_prompts()
        prompts_data = [p.model_dump() for p in prompts]
        return "list_prompts()", json.dumps(prompts_data, indent=2), prompts_data
    except Exception as e:
        return "Error", str(e), []


async def invoke_prompt(
    base_url: str, timeout_seconds: float, prompt_name: str, arguments_text: str, sampling_handler=None
) -> JsonStrPair:
    if not prompt_name:
        return "", "Select a prompt first."
    try:
        args = json.loads(arguments_text) if arguments_text.strip() else {}
    except ValueError as exc:
        return "", f"Invalid JSON arguments: {exc}"

    try:
        client = _get_client()
        # Use manual request to ensure empty arguments dict is sent (workaround for potential fastmcp/mcp issue)
        result = await client.session.send_request(
            types.GetPromptRequest(
                method="prompts/get",
                params=types.GetPromptRequestParams(
                    name=prompt_name,
                    arguments=args
                )
            ),
            types.GetPromptResult
        )
        # Extract text from messages
        messages_text = []
        if hasattr(result, "messages"):
            for msg in result.messages:
                if hasattr(msg, "content"):
                    content = msg.content
                    if hasattr(content, "text"):
                        messages_text.append(content.text)
                    elif isinstance(content, dict) and "text" in content:
                        messages_text.append(content["text"])
        
        final_result = "\n\n".join(messages_text) if messages_text else "No text content found in prompt result."
        return f"get_prompt({prompt_name})", final_result
    except Exception as e:
        return "Error", str(e)


async def list_tools(base_url: str, timeout_seconds: float, sampling_handler=None) -> tuple[str, str, list[dict]]:
    try:
        client = _get_client()
        tools = await client.list_tools()
        # Return list of tool dictionaries (including schema)
        tools_data = [t.model_dump() for t in tools]
        return "list_tools()", json.dumps(tools_data, indent=2), tools_data
    except Exception as e:
        return "Error", str(e), []


async def invoke_tool(
    base_url: str, timeout_seconds: float, tool_name: str, arguments_text: str, sampling_handler=None
) -> JsonStrPair:
    if not tool_name:
        return "", "Select a tool first."
    try:
        args = json.loads(arguments_text) if arguments_text.strip() else {}
    except ValueError as exc:
        return "", f"Invalid JSON arguments: {exc}"

    try:
        client = _get_client()
        result = await client.call_tool(tool_name, arguments=args)
        
        # Extract content from the result
        content = []
        if hasattr(result, "content"):
            for item in result.content:
                if hasattr(item, "text"):
                    content.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    content.append(item["text"])
                else:
                    content.append(str(item))
        
        final_result = "\n".join(content) if content else "No content returned."
        return f"call_tool({tool_name})", final_result
    except Exception as e:
        return "Error", str(e)


async def ping_server(base_url: str, timeout_seconds: float, sampling_handler=None) -> JsonStrPair:
    try:
        client = _get_client()
        await client.ping()
        return "ping()", json.dumps({"status": "Pong"}, indent=2)
    except Exception as e:
        return "Error", str(e)


async def send_custom_request(
    base_url: str, method: str, params_text: str, timeout_seconds: float
) -> JsonStrPair:
    # Fallback to manual httpx for custom requests since FastMCP Client is high-level
    try:
        params = json.loads(params_text) if params_text.strip() else {}
    except ValueError as exc:
        return "", f"Invalid JSON params: {exc}"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    
    try:
        headers = _active_headers.copy() if _active_headers else None
        async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
            response = await client.post(base_url, json=payload)
            response.raise_for_status()
            return json.dumps(payload, indent=2), json.dumps(response.json(), indent=2)
    except Exception as exc:
        return json.dumps(payload, indent=2), f"Error: {exc}"
