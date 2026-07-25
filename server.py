"""
Exam MCP server.

Exposes exactly one tool, `solve_challenge`. On every tools/call it reads the
challenge from the HTTP request headers (NOT the JSON body) and returns the first
16 lowercase hex chars of SHA-256("<challenge>:<normalizedEmail>").

Transport: Streamable HTTP (the modern MCP HTTP transport), served at /mcp.
"""

import hashlib
import os

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

# Registered exam email, trimmed and lowercased.
NORMALIZED_EMAIL = "24f1002465@ds.study.iitm.ac.in".strip().lower()

mcp = FastMCP("exam-challenge-server")


@mcp.tool
def solve_challenge() -> str:
    """Solve the exam challenge carried in the request headers.

    Input schema intentionally has no properties: the challenge is read from the
    X-Exam-Challenge HTTP header of this tool call, not from the arguments.
    """
    headers = get_http_headers()  # headers of the current tools/call request
    # Header names are normalized to lowercase by the transport.
    challenge = (
        headers.get("x-exam-challenge")
        or headers.get("X-Exam-Challenge")
        or ""
    ).strip()
    digest = hashlib.sha256(f"{challenge}:{NORMALIZED_EMAIL}".encode("utf-8")).hexdigest()
    return digest[:16]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # transport="http" is FastMCP's Streamable HTTP transport.
    # stateless_http=True  -> no Mcp-Session-Id continuity required (robust to any grader)
    # json_response=True   -> reply as plain JSON (not SSE), simplest for clients to parse
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        path="/mcp",
        stateless_http=True,
        json_response=True,
    )
