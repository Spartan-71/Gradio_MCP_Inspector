from __future__ import annotations

import gradio as gr
import json
import asyncio
import uuid
import time
from typing import Any
from fastmcp.client.sampling import SamplingMessage, SamplingParams, RequestContext

from mcp_client import (
    connect as mcp_connect,
    disconnect as mcp_disconnect,
    invoke_prompt,
    invoke_tool,
    list_prompts,
    list_resources,
    list_resource_templates,
    list_tools,
    ping_server,
    read_resource,
    send_custom_request,
    get_notifications,
    clear_notifications,
    set_roots,
)


def _render_history(history: list[dict]) -> str:
    if not history:
        return "_No calls yet_"

    html_parts = []
    total_items = len(history)
    for idx, entry in enumerate(history):
        display_num = total_items - idx
        
        if "role" in entry:
            # Render chat message (e.g. from OAuth flow)
            role = entry["role"]
            content = entry["content"]
            # Simple styling for chat messages
            bg_color = "#2b2b2b" if role == "assistant" else "#333333"
            border_color = "#444444"
            icon = "🤖" if role == "assistant" else "👤"
            
            html = f"""
            <div style="margin-bottom: 10px; padding: 10px; border-radius: 4px; background: {bg_color}; border: 1px solid {border_color}; color: #fff;">
                <strong>{icon} {role.title()}:</strong> {content}
            </div>
            """
            html_parts.append(html)
            continue
            
        method = entry.get("method", "Unknown")
        request = entry.get("request", "")
        response = entry.get("response", "")
        
        # Create an accordion-style HTML using details/summary
        html = f"""
                <details style="margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; padding: 10px;">
                    <summary style="cursor: pointer; font-weight: bold; user-select: none;">
                        {display_num}. {method}
                    </summary>
                    <div style="margin-top: 10px;">
                        <div style="margin-bottom: 10px;">
                            <strong>Request:</strong>
                            <pre style="background: #333333; color: #ffffff; padding: 10px; border-radius: 4px; overflow-x: auto; max-height: 300px;">{request}</pre>
                        </div>
                        <div>
                            <strong>Response:</strong>
                            <pre style="background: #333333; color: #ffffff; padding: 10px; border-radius: 4px; overflow-x: auto; max-height: 300px;">{response}</pre>
                        </div>
                    </div>
                </details>
                """
        html_parts.append(html)
    
    return "\n".join(html_parts)


def _update_history(history: list[dict] | None, method: str, request: str, response: str):
    history = history or []
    history.insert(
        0,
        {
            "method": method,
            "request": request,
            "response": response,
        },
    )
    return history, _render_history(history)


async def connect(transport: str, url: str, header_name: str, token: str, request_timeout: float, reset_timeout: str, max_timeout: float, roots: list[str] | None = None):
    cleaned_url = url.strip()
    if not cleaned_url:
        return (
            "",
            "**Status:** ⚠️ Provide a server URL.",
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    header_name = (header_name or "").strip()
    token = (token or "").strip()
    auth_value = None
    custom_headers = None
    if token:
        if not header_name or header_name.lower() == "authorization":
            auth_value = token
        else:
            custom_headers = {header_name: token}

    try:
        # Convert ms to seconds for the client
        timeout_sec = float(request_timeout) / 1000.0 if request_timeout else 10.0
        
        # Update roots if provided
        if roots is not None:
            valid_roots = [r for r in roots if r and r.strip()]
            set_roots(valid_roots)
            
        # Establish persistent connection
        await mcp_connect(cleaned_url, timeout_sec, transport, sampling_handler, auth=auth_value, headers=custom_headers)
    except Exception as e:
        return (
            cleaned_url,
            f"**Status:** 🔴 Connection failed: {str(e)}",
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    badge = f"**Status:** 🟢 Connected via {transport}."
    if token:
        badge += " (bearer token applied)"
    elif header_name:
        badge += f" ({header_name} header applied)"
    return (
        cleaned_url,
        badge,
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
    )


async def disconnect():
    await mcp_disconnect()
    return (
        "",
        "**Status:** 🔴 Disconnected.",
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
    )


async def custom_request_with_history(base_url, method, params, timeout, history):
    request, response = await send_custom_request(base_url, method, params, timeout)
    history, rendered = _update_history(history, method or "custom", request, response)
    return request, response, history, rendered


async def list_tools_with_history(base_url, timeout, history):
    request, response, tools_data = await list_tools(base_url, timeout, sampling_handler)
    names = [t["name"] for t in tools_data]
    update = gr.update(choices=names, value=None, visible=bool(names))
    empty_msg_update = gr.update(visible=not names)
    history, rendered = _update_history(history, "tools/list", request, response)
    return request, response, update, empty_msg_update, tools_data, history, rendered


async def invoke_tool_with_history(base_url, timeout, tool_name, args, history):
    request, response = await invoke_tool(base_url, timeout, tool_name, args, sampling_handler)
    history, rendered = _update_history(history, "tools/call", request, response)
    return request, response, history, rendered


async def list_prompts_with_history(base_url, timeout, history):
    request, response, prompts_data = await list_prompts(base_url, timeout, sampling_handler)
    names = [p["name"] for p in prompts_data]
    update = gr.update(choices=names, value=None, visible=bool(names))
    empty_msg_update = gr.update(visible=not names)
    history, rendered = _update_history(history, "prompts/list", request, response)
    return request, response, update, empty_msg_update, prompts_data, history, rendered


async def invoke_prompt_with_history(base_url, timeout, prompt_name, args, history):
    request, response = await invoke_prompt(base_url, timeout, prompt_name, args, sampling_handler)
    history, rendered = _update_history(history, "prompts/invoke", request, response)
    return request, response, history, rendered


async def list_resources_with_history(base_url, timeout, history):
    request, response, resources_data = await list_resources(base_url, timeout, sampling_handler)
    # Extract names for display (fallback to URI if no name)
    names = [r.get("name", r.get("uri", "Unknown")) for r in resources_data]
    update = gr.update(choices=names, value=None, visible=bool(names))
    empty_msg_update = gr.update(visible=not names)
    history, rendered = _update_history(history, "resources/list", request, response)
    return request, response, update, empty_msg_update, resources_data, history, rendered


async def list_resource_templates_with_history(base_url, timeout, history):
    request, response, templates_data = await list_resource_templates(base_url, timeout, sampling_handler)
    names = [t.get("name", t.get("uriTemplate", "Unknown")) for t in templates_data]
    update = gr.update(choices=names, value=None, visible=bool(names))
    empty_msg_update = gr.update(visible=not names)
    history, rendered = _update_history(history, "resources/templates/list", request, response)
    return request, response, update, empty_msg_update, templates_data, history, rendered


async def read_resource_with_history(base_url, timeout, resource_uri, history):
    request, response = await read_resource(base_url, timeout, resource_uri, sampling_handler)
    history, rendered = _update_history(history, "resources/list", request, response)
    return request, response, history, rendered


async def ping_with_history(base_url, timeout, history):
    request, response = await ping_server(base_url, timeout, sampling_handler)
    history, rendered = _update_history(history, "ping", request, response)
    return history, rendered


# Sampling handler that will be set dynamically
sampling_log = []
pending_sampling_requests = {}


async def sampling_handler(
    messages: list[SamplingMessage], params: SamplingParams, context: RequestContext
) -> str:
    """Interactive sampling handler that waits for user input."""
    request_id = str(uuid.uuid4())
    future = asyncio.Future()
    
    # Extract message content for display
    conversation = []
    for message in messages:
        content = (
            message.content.text
            if hasattr(message.content, "text")
            else str(message.content)
        )
        conversation.append({"role": message.role, "content": content})

    req_data = {
        "id": request_id,
        "messages": conversation,
        "system_prompt": params.systemPrompt if hasattr(params, "systemPrompt") else None,
        "temperature": params.temperature if hasattr(params, "temperature") else None,
        "max_tokens": params.maxTokens if hasattr(params, "maxTokens") else None,
        "future": future,
        "timestamp": time.time()
    }
    
    # Add to pending and log
    pending_sampling_requests[request_id] = req_data
    sampling_log.insert(0, req_data)

    try:
        # Wait for user response via UI
        # We set a long timeout (e.g. 5 minutes) to avoid hanging forever if user is away
        response_text = await asyncio.wait_for(future, timeout=300.0)
        return response_text
    except asyncio.TimeoutError:
        return "Error: Sampling request timed out waiting for user input."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if request_id in pending_sampling_requests:
            del pending_sampling_requests[request_id]


def get_pending_sampling_requests():
    """Get list of pending sampling requests for the UI."""
    # Return serializable data (exclude future object)
    return [
        {k: v for k, v in r.items() if k != "future"}
        for r in pending_sampling_requests.values()
    ]


def submit_sampling_response(request_id: str, response_text: str):
    """Submit a response to a pending sampling request."""
    if request_id in pending_sampling_requests:
        future = pending_sampling_requests[request_id]["future"]
        if not future.done():
            future.set_result(response_text)
        return "Response sent."
    return "Request not found or already handled."


def get_sampling_log():
    """Get the current sampling log."""
    if not sampling_log:
        return "No sampling requests yet."
    
    log_text = []
    for idx, entry in enumerate(sampling_log[:10], 1):  # Show last 10 entries
        status = " (Pending)" if entry["id"] in pending_sampling_requests else " (Completed)"
        log_text.append(f"### Request {idx}{status}")
        log_text.append("**Messages:**")
        for msg in entry["messages"]:
            log_text.append(f"- **{msg['role']}**: {msg['content']}")
        if entry["system_prompt"]:
            log_text.append(f"**System Prompt:** {entry['system_prompt']}")
        log_text.append("---")
    
    return "\n".join(log_text)

async def on_resource_select(base_url, timeout, resource_name, resources, history):
    print(f"DEBUG: on_resource_select called with name='{resource_name}'")
    if not resource_name or not resources:
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            history,
            _render_history(history)
        )
    
    # Find the resource by name and get its URI
    resource = next((r for r in resources if r.get("name") == resource_name), None)
    if not resource or "uri" not in resource:
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            history,
            _render_history(history)
        )
    
    resource_uri = resource["uri"]
    request, response = await read_resource(base_url, timeout, resource_uri, sampling_handler)
    # Parse response to extract text for display
    display_text = response
    try:
        data = json.loads(response)
        if "contents" in data and len(data["contents"]) > 0:
            content = data["contents"][0]
            if "text" in content:
                display_text = content["text"]
    except Exception:
        pass

    history, rendered = _update_history(history, "resources/read", request, response)

    print(f"DEBUG: on_resource_select finishing. Response length: {len(response)}")
    # Return 5 outputs: read_request, read_response, content_display_state, history, history_panel
    return (
        gr.update(value=request, visible=True),
        gr.update(value=response, visible=True),
        display_text,
        history,
        rendered
    )


async def start_oauth_flow(base_url, timeout, transport_type, history, roots=None):
    try:
        from fastmcp.client.auth import OAuth
    except ImportError:
        history.append({"role": "assistant", "content": "Error: fastmcp not installed or OAuth not available."})
        return (
            [],
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            history,
            _render_history(history),
            gr.update(),
            "**Status:** 🔴 Error: fastmcp missing.",
            gr.update(),
            gr.update(),
            gr.update()
        )

    class InspectableOAuth(OAuth):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._flow_artifacts: dict[str, Any] = {
                "authorization_url": None,
                "authorization_code": None,
                "state": None,
            }

        async def redirect_handler(self, authorization_url: str) -> None:
            self._flow_artifacts["authorization_url"] = authorization_url
            await super().redirect_handler(authorization_url)

        async def callback_handler(self) -> tuple[str, str | None]:
            code, state = await super().callback_handler()
            self._flow_artifacts["authorization_code"] = code
            self._flow_artifacts["state"] = state
            return code, state

        def get_summary(self) -> dict[str, Any]:
            token_endpoint = None
            if (
                self.context.oauth_metadata
                and self.context.oauth_metadata.token_endpoint
            ):
                token_endpoint = str(self.context.oauth_metadata.token_endpoint)
            else:
                token_endpoint = f"{self.server_base_url}/token"

            tokens = None
            if self.context.current_tokens:
                tokens = self.context.current_tokens.model_dump(mode="json")

            return {
                "authorization_url": self._flow_artifacts.get("authorization_url"),
                "authorization_code": self._flow_artifacts.get("authorization_code"),
                "token_endpoint": token_endpoint,
                "tokens": tokens,
            }

    # Update history
    history.append({"role": "user", "content": f"Starting OAuth flow for {base_url}..."})
    
    try:
        # Create OAuth instance
        # Note: mcp_url is required.
        oauth = InspectableOAuth(mcp_url=base_url)
        
        # Convert timeout
        # Enforce minimum 120s for OAuth flow to allow user interaction
        input_timeout_sec = float(timeout) / 1000.0 if timeout else 30.0
        timeout_sec = max(input_timeout_sec, 120.0)
        
        # Update roots if provided
        if roots is not None:
            valid_roots = [r for r in roots if r and r.strip()]
            set_roots(valid_roots)
        
        # Connect
        await mcp_connect(base_url, timeout_sec, transport_type, auth=oauth)
        
        history.append({"role": "assistant", "content": "OAuth Authentication Successful! Connected."})
        
        # Return progress update and history
        all_steps = [
            "Metadata Discovery",
            "Client Registration",
            "Preparing Authorization",
            "Request Authorization and acquire authorization code",
            "Token Request",
            "Authentication Complete"
        ]
        
        badge = "**Status:** 🟢 Connected via OAuth."
        
        summary = oauth.get_summary()
        auth_url = summary.get("authorization_url") or "Authorization URL unavailable (flow exited early)."
        auth_code = summary.get("authorization_code") or "Authorization code unavailable."
        token_endpoint = summary.get("token_endpoint") or "Token endpoint unavailable."
        tokens_payload = summary.get("tokens")
        token_text = (
            json.dumps(tokens_payload, indent=2)
            if tokens_payload
            else "No token payload captured."
        )

        return (
            all_steps,
            gr.update(value=auth_url, visible=True),
            gr.update(value=auth_code, visible=True),
            gr.update(value=token_endpoint, visible=True),
            gr.update(value=token_text, visible=True),
            history,
            _render_history(history),
            base_url,
            badge,
            gr.update(visible=False), # initial_connect_btn
            gr.update(visible=True),  # reconnect_btn
            gr.update(visible=True)   # disconnect_btn
        )
        
    except Exception as e:
        history.append({"role": "assistant", "content": f"OAuth Failed: {str(e)}"})
        return (
            [],
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(value=str(e), visible=True),
            history,
            _render_history(history),
            gr.update(),
            f"**Status:** 🔴 OAuth Failed: {str(e)}",
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False)
        )


async def clear_oauth_state(history):
    await mcp_disconnect()
    history.append({"role": "assistant", "content": "OAuth state cleared (Disconnected)."})
    hidden_box = gr.update(value="", visible=False)
    return (
        [],
        hidden_box,
        hidden_box,
        hidden_box,
        hidden_box,
        history, 
        _render_history(history),
        "**Status:** 🔴 Disconnected.",
        gr.update(visible=True),  # initial_connect_btn
        gr.update(visible=False), # reconnect_btn
        gr.update(visible=False)  # disconnect_btn
    )


def _render_notifications(notifications: list[dict]) -> str:
    if not notifications:
        return "_No notifications yet_"
    
    html_parts = []
    for idx, note in enumerate(notifications):
        method = note.get("method", "Unknown")
        params = note.get("params", {})
        
        # Format params as JSON
        params_json = json.dumps(params, indent=2)
        
        # Use a badge for the method
        html = f"""
        <div style="margin-bottom: 10px; border: 1px solid #444; border-radius: 4px; padding: 10px; background: #1e1e1e;">
            <div style="font-weight: bold; color: #66ccff; margin-bottom: 5px;">{method}</div>
            <pre style="background: #000; color: #ccc; padding: 5px; border-radius: 4px; overflow-x: auto; font-size: 0.9em; margin: 0;">{params_json}</pre>
        </div>
        """
        html_parts.append(html)
    
    return "\n".join(html_parts)


def get_server_notifications_handler():
    notes = get_notifications()
    return _render_notifications(notes)


def clear_server_notifications_handler():
    clear_notifications()
    return _render_notifications([])


def update_roots_handler(roots_list: list[str]):
    # Filter empty strings
    valid_roots = [r for r in roots_list if r and r.strip()]
    set_roots(valid_roots)
    return f"Updated {len(valid_roots)} roots."

