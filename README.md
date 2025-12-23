
# 🔍 Gradio MCP Inspector
<div align="center">

**A powerful, interactive GUI for testing and debugging Remote Model Context Protocol (MCP) servers**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Gradio](https://img.shields.io/badge/Gradio-6.0.1-orange)](https://gradio.app/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io/)

</div>

---

## 🎯 Overview

The **Gradio MCP Inspector** is a comprehensive web-based tool designed for developers working with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Built with [Gradio](https://gradio.app/) and [FastMCP](https://github.com/jlowin/fastmcp), it provides an intuitive interface for exploring, testing, and debugging MCP servers in real-time.


## ✨ Key Features

- **🔌 Transport Support**: Streamable HTTP and SSE with configurable timeouts
- **📂 Resources**: Browse resources and templates with dynamic parameter forms
- **💬 Prompts**: List and execute prompts with auto-generated input forms
- **🛠️ Tools**: Discover and run tools with schema-based inputs (strings, numbers, booleans, enums, JSON)
- **🔐 Authentication**: Bearer tokens, custom headers, and OAuth 2.0 flow support
- **📡 Notifications**: Real-time monitoring of server events (tool/resource/prompt changes, progress, logs)
- **🤖 Sampling**: Interactive LLM sampling request handling with approval queue
- **📁 Roots**: Configure filesystem root directories for server access
- **🕵️ Debugging**: Complete JSON-RPC request/response visibility and call history
- **🎨 Modern UI**: Light/dark themes, responsive design, and organized tabbed interface

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Spartan-71/Gradio_MCP_Inspector.git
   cd gradio-mcp-inspector
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://127.0.0.1:7860`

## 📖 Usage Guide

### Connecting to an MCP Server

1. **Select Transport Type**: Choose between "Streamable HTTP" or "SSE"
2. **Enter Server URL**: Input your MCP server endpoint (e.g., `https://your-server.com/mcp`)
3. **Configure Authentication** (optional):
   - Expand the "Authentication" accordion
   - Enter your bearer token or custom header
4. **Adjust Configuration** (optional):
   - Set request timeout (default: 10000ms)
   - Configure timeout reset behavior
   - Set maximum total timeout
5. **Click "Connect"**: Establish connection to the server


## 🏗️ Architecture

The inspector is built with a clean, modular architecture:

- **`app.py`**: Main Gradio interface and UI layout
- **`handlers.py`**: Backend handlers for MCP operations and state management
- **`mcp_client.py`**: MCP client wrapper with notification and roots support
- **`theme.py`**: Custom Gradio theme configuration

### Key Technologies

- **[Gradio 6.0.1](https://gradio.app/)**: Web UI framework
- **[FastMCP](https://github.com/jlowin/fastmcp)**: MCP client library
- **[httpx](https://www.python-httpx.org/)**: Async HTTP client
- **Python 3.13**: Modern Python with type hints

## 🎨 Features in Detail


### Request/Response Debugging

Every MCP operation shows:
- **Request**: The exact JSON-RPC request sent to the server
- **Response**: The complete server response
- **Formatted Output**: Human-readable display of results

### History Tracking

All interactions are logged with:
- Timestamp
- Operation type (method name)
- Request/response preview
- Expandable details

## 🔧 Configuration

### Timeout Settings

- **Request Timeout**: Maximum time for a single request (milliseconds)
- **Reset Timeout on Progress**: Whether to reset timeout when progress is reported
- **Maximum Total Timeout**: Absolute maximum time for any operation (milliseconds)

### Authentication Options

- **Bearer Token**: Standard OAuth/JWT token authentication
- **Custom Headers**: Support for any authentication scheme (API keys, etc.)

## 🙏 Acknowledgments

- Built for the [MCP 1st Birthday Hackathon](https://modelcontextprotocol.io/)
- Powered by [Gradio](https://gradio.app/) and [FastMCP](https://github.com/jlowin/fastmcp)
- Inspired by the MCP community's amazing work
