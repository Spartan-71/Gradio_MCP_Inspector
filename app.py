from __future__ import annotations
from statistics import variance

import gradio as gr
import json

from handlers import (
    connect,
    disconnect,
    list_resources_with_history,
    list_resource_templates_with_history,
    on_resource_select,
    list_prompts_with_history,
    invoke_prompt_with_history,
    list_tools_with_history,
    invoke_tool_with_history,
    ping_with_history,
    get_sampling_log,
    start_oauth_flow,
    clear_oauth_state,
    get_server_notifications_handler,
    update_roots_handler,
    get_pending_sampling_requests,
    submit_sampling_response,
)

from theme import CustomTheme

css = """
.resource-content-display {
    background-color: #1e1e1e !important;
    padding: 15px !important;
    border-radius: 8px !important;
    border: 1px solid #333 !important;
    margin-top: 10px !important;
}
.resource-content-display .prose {
    background-color: transparent !important;
}
.resource-content-display pre {
.resource-placeholder {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.resource-placeholder p {
    background-color: transparent !important;
}
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
.oauth-progress-checkboxes {
    display: flex !important;
    flex-direction: column !important;
}
"""

with gr.Blocks(title="Gradio MCP Inspector") as app:

    gr.Markdown("# Gradio MCP Inspector")
    server_url_state = gr.State("")
    history_state = gr.State([])
    tools_state = gr.State([])
    resources_state = gr.State([])
    templates_state = gr.State([])
    prompts_state = gr.State([])
    roots_state = gr.State([]) # Default root

    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=320):
            transport_type = gr.Dropdown(
                ["Streamable HTTP","SSE"],
                label="Transport Type",
                value="Streamable HTTP",
            )
            base_url_input = gr.Textbox(
                label="URL",
                placeholder="https://your-mcp-server.example/mcp",
            )

            with gr.Accordion("Authentication", open=False):
                header_name = gr.Textbox(label="Header Name",value="Authorization")
                bearer_token = gr.Textbox(label="Bearer Token", placeholder="Bearer Token",type="password")

            with gr.Accordion("Configuration", open=False):
                request_timeout = gr.Number(label="Request Timeout", value=10000)
                reset_timeout_on_progress = gr.Dropdown(
                    label="Reset Timeout on Progress", 
                    choices=["True", "False"], 
                    value="True"
                )
                max_total_timeout = gr.Number(label="Maximum Total Timeout", value=60000)

            status_badge = gr.Markdown("🔴 Disconnected.")
            initial_connect_btn = gr.Button("Connect", variant="primary")
            reconnect_btn = gr.Button("Reconnect", variant="primary", visible=False)
            disconnect_btn = gr.Button("Disconnect", variant="stop", visible=False)

            initial_connect_btn.click(
                connect,
                inputs=[transport_type, base_url_input, header_name, bearer_token, request_timeout, reset_timeout_on_progress, max_total_timeout, roots_state],
                outputs=[server_url_state, status_badge, initial_connect_btn, reconnect_btn, disconnect_btn],
            )
            reconnect_btn.click(
                connect,
                inputs=[transport_type, base_url_input, header_name, bearer_token, request_timeout, reset_timeout_on_progress, max_total_timeout, roots_state],
                outputs=[server_url_state, status_badge, initial_connect_btn, reconnect_btn, disconnect_btn],
            )
            disconnect_btn.click(
                disconnect,
                outputs=[server_url_state, status_badge, initial_connect_btn, reconnect_btn, disconnect_btn],
            )

            # Add spacing
            gr.HTML("<div style='margin-top: 13em;'></div>")


            theme_selector = gr.Radio(
                ["Light", "Dark"],
                value="Light",
                label="Theme",
                interactive=True,
            )
            gr.Markdown("Connected indicator updates once you reconnect.")


        with gr.Column(scale=3, min_width=640):
            with gr.Tabs():
                with gr.Tab("Resources"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Resources")
                            list_resources_btn = gr.Button("List Resources",variant="primary")
                            clear_resources_btn = gr.Button("Clear")
                            resource_list = gr.Radio(label="Available Resources", choices=[], interactive=True)
                            resource_empty_msg = gr.Markdown("⚠️ No resources found.", visible=False)

                        with gr.Column():
                            gr.Markdown("### Resource Templates")
                            list_templates_btn = gr.Button("List Templates",variant="primary")
                            clear_templates_btn = gr.Button("Clear")
                            template_list = gr.Radio(label="Available Templates", choices=[], interactive=True)
                            template_empty_msg = gr.Markdown("⚠️ No templates found.", visible=False)

                        with gr.Column():
                            content_display_state = gr.State("")
                            
                            with gr.Group():
                                @gr.render(inputs=[resource_list, resources_state, template_list, templates_state, content_display_state])
                                def render_resource_or_template(resource_name, resources, template_name, templates, content_text):
                                    # ... (keep existing logic) ...
                                    # Show template form if a template is selected
                                    if template_name and templates:
                                        tmpl = next((t for t in templates if t.get("name") == template_name), None)
                                        if tmpl:
                                            gr.Markdown(f"### {tmpl.get('name', 'Template')}")
                                            gr.Markdown(tmpl.get("description", "No description provided."))
                                            
                                            # Parse URI template to extract parameters
                                            uri_template = tmpl.get("uriTemplate", "")
                                            import re
                                            path_params = re.findall(r'/\{([^}]+)\}', uri_template)
                                            query_match = re.search(r'\{\?([^}]+)\}', uri_template)
                                            query_params = query_match.group(1).split(',') if query_match else []
                                            
                                            inputs = {}
                                            
                                            with gr.Group():
                                                # Path parameters
                                                for param in path_params:
                                                    inputs[param] = gr.Textbox(
                                                        label=param,
                                                        placeholder=f"Enter {param}"
                                                    )
                                                
                                                # Query parameters
                                                for param in query_params:
                                                    inputs[param] = gr.Textbox(
                                                        label=param,
                                                        placeholder=f"Enter {param} (optional)"
                                                    )
                                                
                                                read_btn = gr.Button("Read Resource", variant="primary")
                                            
                                            async def wrapper(base_url, timeout, history, *form_values):
                                                # Build the URI from template and parameters
                                                uri = uri_template
                                                keys = list(inputs.keys())
                                                
                                                # Replace path parameters
                                                for i, key in enumerate(keys):
                                                    val = form_values[i]
                                                    if key in path_params and val:
                                                        uri = uri.replace(f"{{{key}}}", val)
                                                
                                                # Build query string from query parameters
                                                query_parts = []
                                                for i, key in enumerate(keys):
                                                    val = form_values[i]
                                                    if key in query_params and val:
                                                        query_parts.append(f"{key}={val}")
                                                
                                                if query_parts:
                                                    uri = uri.replace(f"{{?{','.join(query_params)}}}", f"?{'&'.join(query_parts)}")
                                                else:
                                                    uri = uri.replace(f"{{?{','.join(query_params)}}}", "")
                                                
                                                timeout_sec = float(timeout) / 1000.0 if timeout else 30.0
                                                from handlers import read_resource_with_history
                                                request, response, history, rendered = await read_resource_with_history(base_url, timeout_sec, uri, history)
                                                
                                                # Parse response to extract text
                                                display_text = response
                                                try:
                                                    import json
                                                    data = json.loads(response)
                                                    if "contents" in data and len(data["contents"]) > 0:
                                                        content = data["contents"][0]
                                                        if "text" in content:
                                                            display_text = content["text"]
                                                            # Try to pretty print if it's JSON
                                                            try:
                                                                parsed = json.loads(display_text)
                                                                display_text = json.dumps(parsed, indent=2)
                                                            except Exception:
                                                                pass
                                                except Exception:
                                                    pass
                                                    
                                                return (
                                                    gr.update(value=request, visible=True),
                                                    gr.update(value=response, visible=True),
                                                    display_text,
                                                    history,
                                                    rendered
                                                )
                                            
                                            read_btn.click(
                                                wrapper,
                                                inputs=[server_url_state, request_timeout, history_state] + list(inputs.values()),
                                                outputs=[template_read_request, template_read_response, content_display_state, history_state, history_panel]
                                            )
                                    
                                    # Show resource header if a resource is selected
                                    elif resource_name and resources:
                                        res = next((r for r in resources if r.get("name") == resource_name), None)
                                        if res:
                                            gr.Markdown(f"### {res.get('name', 'Resource')}")
                                    
                                    # Default state
                                    else:
                                        gr.Markdown(
                                            "### Select a resource or template",
                                            elem_classes=["resource-placeholder"],
                                        )
                                        gr.Markdown(
                                            "Select a resource or template from the list to view its contents",
                                            elem_classes=["resource-placeholder"],
                                        )
                                        
                                    if content_text:
                                        with gr.Blocks():
                                            gr.Markdown("### Output")
                                            # Try to pretty print if it's JSON
                                            display_text = content_text
                                            try:
                                                import json
                                                parsed = json.loads(content_text)
                                                display_text = json.dumps(parsed, indent=2)
                                            except Exception:
                                                pass
                                            gr.Markdown(f"```json\n{display_text}\n```")

                    with gr.Accordion("Debug Info", open=False):
                        resource_list_request = gr.Code(label="List Request", language="json")
                        resource_list_response = gr.Code(label="List Response", language="json")
                        resource_read_request = gr.Code(label="Read Request", language="json", visible=False)
                        resource_read_response = gr.Code(label="Read Response", language="json", visible=False)
                        resource_content_view = gr.Code(label="Resource Content", language="json", visible=False)
                        template_read_request = gr.Code(label="Template Read Request", language="json")
                        template_read_response = gr.Code(label="Template Read Response", language="json")

                with gr.Tab("Prompts"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Prompts")
                            list_prompts_btn = gr.Button("List Prompts",variant="primary")
                            clear_prompts_btn = gr.Button("Clear")
                            prompt_list = gr.Radio(label="Available Prompts", choices=[], interactive=True)
                            prompt_empty_msg = gr.Markdown("⚠️ No prompts found.", visible=False)

                        with gr.Column(scale=2):
                            @gr.render(inputs=[prompt_list, prompts_state])
                            def render_prompt_form(prompt_name, prompts):
                                if not prompt_name or not prompts:
                                    gr.Markdown("### Select a prompt")
                                    gr.Markdown("Select a prompt from the list to view its details and invoke it.")
                                    return
                                
                                prompt = next((p for p in prompts if p["name"] == prompt_name), None)
                                if not prompt:
                                    return

                                gr.Markdown(f"### {prompt['name']}")
                                gr.Markdown(prompt.get("description", "No description provided."))
                                
                                arguments = prompt.get("arguments", [])
                                inputs = {}
                                
                                with gr.Group():
                                    for arg in arguments:
                                        arg_name = arg["name"]
                                        label = arg_name + (" *" if arg.get("required") else "")
                                        desc = arg.get("description", "")
                                        # Prompts usually take string arguments
                                        inputs[arg_name] = gr.Textbox(label=label, placeholder=desc)

                                    run_btn = gr.Button("Get Prompt", variant="primary")
                                
                                async def wrapper(base_url, timeout, history, *form_values):
                                    args = {}
                                    keys = list(inputs.keys())
                                    for i, key in enumerate(keys):
                                        val = form_values[i]
                                        if val:
                                            args[key] = val
                                    # Convert timeout (ms) to seconds for the handler
                                    timeout_sec = float(timeout) / 1000.0 if timeout else 30.0
                                    request, response, history, rendered = await invoke_prompt_with_history(base_url, timeout_sec, prompt_name, json.dumps(args), history)
                                    return (
                                        gr.update(value=response, visible=True),
                                        history,
                                        rendered
                                    )

                                run_btn.click(
                                    wrapper,
                                    inputs=[server_url_state, request_timeout, history_state] + list(inputs.values()),
                                    outputs=[prompt_call_response, history_state, history_panel]
                                )

                            prompt_call_response = gr.Markdown(label="Result", visible=False)
                    
                    with gr.Accordion("Debug Info", open=False):
                        prompt_list_request = gr.Code(label="List Request", language="json")
                        prompt_list_response = gr.Code(label="List Response", language="json")
                        prompt_call_request = gr.Code(label="Invocation Request", language="json")
                with gr.Tab("Tools"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Tools")
                            list_tools_btn = gr.Button("List Tools",variant="primary")
                            clear_tools_btn = gr.Button("Clear")
                            tool_list = gr.Radio(label="Available Tools", choices=[], interactive=True)
                            tool_empty_msg = gr.Markdown("⚠️ No tools found.", visible=False)

                        with gr.Column(scale=2):
                            @gr.render(inputs=[tool_list, tools_state])
                            def render_tool_form(tool_name, tools):
                                if not tool_name or not tools:
                                    gr.Markdown("### Select a tool")
                                    gr.Markdown("Select a tool from the list to view its details and run it")
                                    return
                                
                                tool = next((t for t in tools if t["name"] == tool_name), None)
                                if not tool:
                                    return

                                gr.Markdown(f"### {tool['name']}")
                                gr.Markdown(tool.get("description", "No description provided."))
                                
                                schema = tool.get("inputSchema", {})
                                properties = schema.get("properties", {})
                                required = schema.get("required", [])
                                
                                inputs = {}
                                
                                with gr.Group():
                                    for prop_name, prop_schema in properties.items():
                                        label = prop_name + (" *" if prop_name in required else "")
                                        prop_type = prop_schema.get("type", "string")
                                        desc = prop_schema.get("description", "")
                                        default_val = prop_schema.get("default", None)
                                        enum_vals = prop_schema.get("enum", None)
                                        
                                        if enum_vals:
                                            inputs[prop_name] = gr.Dropdown(
                                                label=label, 
                                                choices=enum_vals, 
                                                value=default_val, 
                                                info=desc
                                            )
                                        elif prop_type == "string":
                                            inputs[prop_name] = gr.Textbox(
                                                label=label, 
                                                placeholder=desc, 
                                                value=default_val if default_val is not None else ""
                                            )
                                        elif prop_type == "integer" or prop_type == "number":
                                            inputs[prop_name] = gr.Number(
                                                label=label, 
                                                info=desc, 
                                                value=default_val
                                            )
                                        elif prop_type == "boolean":
                                            inputs[prop_name] = gr.Checkbox(
                                                label=label, 
                                                info=desc, 
                                                value=default_val if default_val is not None else False
                                            )
                                        else:
                                            # For arrays/objects, try to show default as JSON if exists
                                            def_json = json.dumps(default_val) if default_val is not None else "{}"
                                            inputs[prop_name] = gr.Code(
                                                label=label + " (JSON)", 
                                                language="json", 
                                                value=def_json
                                            )

                                    run_btn = gr.Button("Run Tool", variant="primary")
                                
                                async def wrapper(base_url, timeout, history, *form_values):
                                    args = {}
                                    keys = list(inputs.keys())
                                    for i, key in enumerate(keys):
                                        val = form_values[i]
                                        # Only include if it has a value or is required? 
                                        # For now, include if not None/Empty string to avoid sending empty strings for optional fields
                                        if val is not None and val != "":
                                            args[key] = val
                                    
                                    # Convert timeout (ms) to seconds
                                    timeout_sec = float(timeout) / 1000.0 if timeout else 30.0
                                    return await invoke_tool_with_history(base_url, timeout_sec, tool_name, json.dumps(args), history)

                                run_btn.click(
                                    wrapper,
                                    inputs=[server_url_state, request_timeout, history_state] + list(inputs.values()),
                                    outputs=[tool_call_request, tool_call_response, history_state, history_panel]
                                )
                            tool_call_response = gr.Markdown(label="Tool Result")
                    with gr.Accordion("Debug Info", open=False):
                        tool_list_request = gr.Code(label="List Request", language="json")
                        tool_list_response = gr.Code(label="List Response", language="json")
                        tool_call_request = gr.Code(label="Invocation Request", language="json") # Moved outside render block

                with gr.Tab("Ping"):
                    with gr.Row():
                        gr.Column(scale=1)
                        with gr.Column(scale=0, min_width=150):
                            ping_btn = gr.Button("Ping Server", variant="primary")
                        gr.Column(scale=1)
                with gr.Tab("Sampling"):
                    gr.Markdown("When the server requests LLM sampling, requests will appear here for approval.")
                    
                    pending_requests_state = gr.State([])
                    
                    # Timer to refresh pending requests
                    sampling_timer = gr.Timer(1.0)
                    
                    @gr.render(inputs=pending_requests_state)
                    def render_sampling_requests(requests):
                        if not requests:
                            gr.Markdown("No pending requests.")
                            # Show history if no pending
                            gr.Markdown("### Recent Requests Log")
                            gr.Markdown(get_sampling_log())
                            return
                            
                        for req in requests:
                            with gr.Group():
                                gr.Markdown(f"### Request {req['id'][:8]}")
                                # Display messages
                                for msg in req['messages']:
                                    gr.Markdown(f"**{msg['role']}**: {msg['content']}")
                                
                                response_input = gr.Textbox(label="Response", lines=3)
                                submit_btn = gr.Button("Send Response", variant="primary")
                                
                                # We need to capture req['id'] in the closure
                                submit_btn.click(
                                    submit_sampling_response,
                                    inputs=[gr.State(req['id']), response_input],
                                    outputs=[]
                                )
                    
                    sampling_timer.tick(
                        get_pending_sampling_requests,
                        outputs=[pending_requests_state]
                    )

                with gr.Tab("Roots"):
                    gr.Markdown("Configure the root directories that the server can access. These are provided to the server when it requests roots.")
                    
                    roots_list_container = gr.Column()
                    
                    @gr.render(inputs=roots_state)
                    def render_roots(roots):
                        roots = roots or []
                        
                        # Helper to update a specific root
                        def update_root(new_val, idx):
                            roots[idx] = new_val
                            return roots
                        
                        # Helper to remove a root
                        def remove_root(idx):
                            roots.pop(idx)
                            return roots

                        with gr.Column():
                            for i, root in enumerate(roots):
                                with gr.Row():
                                    t = gr.Textbox(value=root, show_label=False, container=True, scale=5, interactive=True)
                                    # We need to bind i immediately
                                    t.change(
                                        fn=lambda val, idx=i: update_root(val, idx),
                                        inputs=[t],
                                        outputs=[]
                                    )
                                    
                                    del_btn = gr.Button("⛔", scale=0, min_width=20, variant="stop")
                                    del_btn.click(
                                        fn=lambda idx=i: remove_root(idx),
                                        outputs=[roots_state]
                                    )

                    with gr.Row():
                        add_root_btn = gr.Button("+ Add Root", variant="secondary")
                        save_roots_btn = gr.Button("Save Changes", variant="primary")
                        roots_status = gr.Markdown("", visible=True)

                    add_root_btn.click(
                        lambda r: r + ["file://"],
                        inputs=[roots_state],
                        outputs=[roots_state]
                    )
                    
                    save_roots_btn.click(
                        update_roots_handler,
                        inputs=[roots_state],
                        outputs=[roots_status]
                    )

                with gr.Tab("Auth"):
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=4):
                            gr.Markdown("## Authentication Settings")
                        with gr.Column(scale=1):
                            back_to_connect_btn = gr.Button("Back to Connect")
                    
                    gr.Markdown("Configure authentication settings for your MCP server connection.")

                    gr.HTML("<div style='margin-top: 2em;'></div>")

                    
                    with gr.Blocks():
                        gr.Markdown("### OAuth Authentication")
                        gr.Markdown("Use OAuth to securely authenticate with the MCP server.")
                        
                        with gr.Row():
                            guided_flow_btn = gr.Button("Guided OAuth Flow")
                            quick_flow_btn = gr.Button("Quick OAuth Flow", variant="primary")
                            clear_state_btn = gr.Button("Clear OAuth State")
                            
                        gr.Markdown("Choose \"Guided\" for step-by-step instructions or \"Quick\" for the standard automatic flow.")
                    
                    gr.HTML("<div style='margin-top: 2em;'></div>")

                    with gr.Blocks():
                        gr.Markdown("### OAuth Flow Progress")
                        gr.Markdown("Follow these steps to complete OAuth authentication with the server.")
                        
                        oauth_progress = gr.CheckboxGroup(
                            choices=[
                                "Metadata Discovery",
                                "Client Registration",
                                "Preparing Authorization",
                                "Request Authorization and acquire authorization code",
                                "Token Request",
                                "Authentication Complete"
                            ],
                            value=[],
                            label="Progress",
                            show_label=False,
                            interactive=False,
                            elem_classes="oauth-progress-checkboxes"
                        )
                        
                        continue_btn = gr.Button("Continue", variant="primary")

                    gr.HTML("<div style='margin-top: 1.5em;'></div>")

                    with gr.Blocks():
                        gr.Markdown("### OAuth Session Details")
                        gr.Markdown("Captured values appear after a successful OAuth exchange.")
                        oauth_authorization_url = gr.Textbox(
                            label="Authorization URL",
                            lines=2,
                            interactive=False,
                            visible=False
                        )
                        oauth_authorization_code = gr.Textbox(
                            label="Authorization Code",
                            interactive=False,
                            visible=False
                        )
                        oauth_token_endpoint = gr.Textbox(
                            label="Token Endpoint",
                            interactive=False,
                            visible=False
                        )
                        oauth_token_payload = gr.Code(
                            label="Access / Refresh Tokens",
                            language="json",
                            visible=False
                        )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### History")
                    history_panel = gr.HTML(value="<p><em>No calls yet</em></p>")
                with gr.Column():
                    gr.Markdown("### Server Notifications")
                    notifications_panel = gr.HTML(value="<p><em>No notifications yet</em></p>")
                    
                    # Auto-refresh every 1 second
                    notification_timer = gr.Timer(1.0)
                    notification_timer.tick(
                        get_server_notifications_handler,
                        outputs=[notifications_panel]
                    )

    # Wiring (done after layout so every component is defined)
    list_resources_btn.click(
        list_resources_with_history,
        inputs=[server_url_state, request_timeout, history_state],
        outputs=[
            resource_list_request,
            resource_list_response,
            resource_list,
            resource_empty_msg,
            resources_state,
            history_state,
            history_panel,
        ],
    )

    list_templates_btn.click(
        list_resource_templates_with_history,
        inputs=[server_url_state, request_timeout, history_state],
        outputs=[
            resource_list_request,
            resource_list_response,
            template_list,
            template_empty_msg,
            templates_state,
            history_state,
            history_panel,
        ],
    )

    # Clear resource list when template is selected, and clear output
    template_list.select(
        lambda: (gr.update(value=None), ""),
        outputs=[resource_list, content_display_state]
    )

    # Clear template list when resource is selected
    resource_list.select(
        lambda: gr.update(value=None),
        outputs=[template_list]
    )

    resource_list.select(
        on_resource_select,
        inputs=[server_url_state, request_timeout, resource_list, resources_state, history_state],
        outputs=[
            resource_read_request,
            resource_read_response,
            content_display_state,
            history_state,
            history_panel,
        ],
    )

    clear_resources_btn.click(
        lambda: (gr.update(choices=[], value=None, visible=True), gr.update(value="", visible=False), gr.update(visible=False)),
        outputs=[resource_list, resource_content_view, resource_empty_msg]
    )

    clear_templates_btn.click(
        lambda: (gr.update(choices=[], value=None, visible=True), gr.update(visible=False)),
        outputs=[template_list, template_empty_msg]
    )

    list_prompts_btn.click(
        list_prompts_with_history,
        inputs=[server_url_state, request_timeout, history_state],
        outputs=[
            prompt_list_request,
            prompt_list_response,
            prompt_list,
            prompt_empty_msg,
            prompts_state,
            history_state,
            history_panel,
        ],
    )

    clear_prompts_btn.click(
        lambda: (gr.update(choices=[], value=None), gr.update(visible=False)),
        outputs=[prompt_list, prompt_empty_msg],
    )

    list_tools_btn.click(
        list_tools_with_history,
        inputs=[server_url_state, request_timeout, history_state],
        outputs=[
            tool_list_request,
            tool_list_response,
            tool_list,
            tool_empty_msg,
            tools_state,
            history_state,
            history_panel,
        ],
    )

    clear_tools_btn.click(
        lambda: (gr.update(choices=[], value=None), gr.update(visible=False)),
        outputs=[tool_list, tool_empty_msg],
    )

    ping_btn.click(
        ping_with_history,
        inputs=[server_url_state, request_timeout, history_state],
        outputs=[history_state, history_panel],
    )

    quick_flow_btn.click(
        start_oauth_flow,
        inputs=[server_url_state, request_timeout, transport_type, history_state, roots_state],
        outputs=[
            oauth_progress,
            oauth_authorization_url,
            oauth_authorization_code,
            oauth_token_endpoint,
            oauth_token_payload,
            history_state,
            history_panel,
            server_url_state,
            status_badge,
            initial_connect_btn,
            reconnect_btn,
            disconnect_btn
        ],
    )

    clear_state_btn.click(
        clear_oauth_state,
        inputs=[history_state],
        outputs=[
            oauth_progress,
            oauth_authorization_url,
            oauth_authorization_code,
            oauth_token_endpoint,
            oauth_token_payload,
            history_state,
            history_panel,
            status_badge,
            initial_connect_btn,
            reconnect_btn,
            disconnect_btn
        ],
    )

    theme_selector.change(
        None,
        inputs=theme_selector,
        js="""(theme) => {
            if (theme === "Dark") {
                document.body.classList.add('dark');
            } else {
                document.body.classList.remove('dark');
            }
        }"""
    )

    app.load(
        None,
        inputs=theme_selector,
        js="""(theme) => {
            if (theme === "Dark") {
                document.body.classList.add('dark');
            } else {
                document.body.classList.remove('dark');
            }
        }"""
    )

if __name__ == "__main__":
    app.launch(theme=CustomTheme(),css=css)