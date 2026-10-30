"""Run the TIDOS MCP server on stdio: python -I tidos_mcp/__main__.py

Registered automatically: START TIDOS wires it into OpenCode and Gemini CLI (tidos_session/wire.py); Claude Code
gets it from the TIDOS plugin. By hand: claude mcp add tidos -- python -I "<TIDOS>/tidos_mcp/__main__.py"
"""
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_mcp.server import serve  # noqa: E402

for stream in (sys.stdin, sys.stdout):
    try:
        stream.reconfigure(encoding="utf-8", newline="\n")
    except (AttributeError, ValueError):
        pass
serve()
