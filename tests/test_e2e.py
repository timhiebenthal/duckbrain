"""End-to-end tests for the duckbrain MCP server.

Launches the server as a subprocess and tests all 3 tools against a temp vault
using the MCP JSON-RPC protocol over stdio.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _mcp_request_line(
    server_proc: subprocess.Popen, method: str, params: dict | None = None
) -> dict:
    """Send a JSON-RPC request to the MCP server via stdio and return the response.

    Uses a static incrementing request ID.
    """
    # Use a simple counter via function attribute
    if not hasattr(_mcp_request_line, "_req_id"):
        _mcp_request_line._req_id = 0
    _mcp_request_line._req_id += 1
    req_id = _mcp_request_line._req_id

    request = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {},
    }
    req_line = json.dumps(request) + "\n"
    server_proc.stdin.write(req_line)
    server_proc.stdin.flush()
    # Read response line(s)
    resp_line = server_proc.stdout.readline()
    if not resp_line:
        raise RuntimeError("No response from server")
    return json.loads(resp_line)


def _initialize_server(server_proc: subprocess.Popen) -> None:
    """Perform the MCP initialize handshake."""
    init_resp = _mcp_request_line(server_proc, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0.1.0"},
    })
    if "error" in init_resp:
        raise RuntimeError(f"Initialize failed: {init_resp['error']}")

    # Send initialized notification (no response expected)
    init_notify = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
    server_proc.stdin.write(init_notify)
    server_proc.stdin.flush()


def _call_tool(server_proc: subprocess.Popen, name: str, arguments: dict | None = None) -> dict:
    """Call an MCP tool and return the result dict."""
    resp = _mcp_request_line(server_proc, "tools/call", {
        "name": name,
        "arguments": arguments or {},
    })
    if "error" in resp:
        raise RuntimeError(f"Tool call failed: {resp['error']}")
    return resp.get("result", {})


def _start_server(vault_path: Path) -> subprocess.Popen:
    """Start the duckbrain MCP server as a subprocess."""
    env = os.environ.copy()
    env["VAULT_PATH"] = str(vault_path)

    return subprocess.Popen(
        [sys.executable, "-m", "duckbrain.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )


def _stop_server(server_proc: subprocess.Popen) -> None:
    """Terminate the server subprocess."""
    try:
        server_proc.terminate()
        server_proc.wait(timeout=5)
    except Exception:
        server_proc.kill()


def test_e2e_vault_info(temp_vault: Path) -> None:
    """Fetch vault info and verify counts match the temp vault."""
    server_proc = _start_server(temp_vault)
    try:
        time.sleep(0.5)
        _initialize_server(server_proc)

        # Call vault_info
        result = _call_tool(server_proc, "vault_info")
        # FastMCP returns: {"content": [{"type": "text", "text": "{...json...}"}], "isError": false}
        content_list = result.get("content", [])
        assert len(content_list) >= 1, f"No content in result: {result}"
        text = content_list[0].get("text", "{}")
        info = json.loads(text)

        assert info["entities"] == 1
        assert info["concepts"] == 2
        assert "ai" in info.get("available_tags", [])
    finally:
        _stop_server(server_proc)


def test_e2e_vault_search(temp_vault: Path) -> None:
    """Search the vault and verify results."""
    server_proc = _start_server(temp_vault)
    try:
        time.sleep(0.5)
        _initialize_server(server_proc)

        # Search for "memory"
        result = _call_tool(server_proc, "vault_search", {"query": "memory"})
        content_list = result.get("content", [])
        assert len(content_list) > 0, f"No content in result: {result}"

        # Each content item is a TextContent with a text field containing a JSON object
        # The response may also have structuredContent with the full results array
        # Extract titles from all content items
        titles = []
        for item in content_list:
            text = item.get("text", "{}")
            try:
                item_data = json.loads(text)
                if isinstance(item_data, dict) and "title" in item_data:
                    titles.append(item_data["title"])
                elif isinstance(item_data, list):
                    titles.extend(r.get("title", "") for r in item_data)
            except json.JSONDecodeError:
                pass

        assert len(titles) > 0, f"No titles extracted from content: {content_list}"
        # "memory" appears in "Claude Mem" body and "Agent Memory Systems" body
        assert "Claude Mem" in titles or "Agent Memory Systems" in titles, (
            f"Expected 'Claude Mem' or 'Agent Memory Systems' in {titles}"
        )
    finally:
        _stop_server(server_proc)


def test_e2e_vault_write_and_search(temp_vault: Path) -> None:
    """Write a new page, then verify it appears on disk and in index+log."""
    server_proc = _start_server(temp_vault)
    try:
        time.sleep(0.5)
        _initialize_server(server_proc)

        # Write a new page
        result = _call_tool(server_proc, "vault_write", {
            "kind": "concept",
            "title": "E2E Test Concept",
            "content": "# E2E Test\n\nThis is an e2e test page with unique keyword xylophone42.",
            "tags": ["e2e", "test"],
        })
        content_list = result.get("content", [])
        assert len(content_list) >= 1, f"No content in result: {result}"
        text = content_list[0].get("text", "{}")
        write_output = json.loads(text)
        assert write_output.get("success") is True, f"Write failed: {write_output}"

        # Verify file exists on disk
        page_path = temp_vault / "wiki" / "concepts" / "e2e-test-concept.md"
        assert page_path.exists(), f"Page not created at {page_path}"

        # Verify index.md was updated
        index_content = (temp_vault / "wiki" / "index.md").read_text()
        assert "[[E2E Test Concept]]" in index_content, f"Index not updated: {index_content}"
        assert "E2E Test Concept" in index_content

        # Verify log.md was updated
        log_content = (temp_vault / "wiki" / "log.md").read_text()
        assert "E2E Test Concept" in log_content, f"Log not updated: {log_content}"
    finally:
        _stop_server(server_proc)
