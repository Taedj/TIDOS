"""Run the TIDOS MCP server on stdio: python -I tidos_mcp/__main__.py

Register it (the user runs this; agents may not change their own configuration):
  Claude Code : claude mcp add tidos -- python -I "<TIDOS>/tidos_mcp/__main__.py"
  OpenCode    : opencode.json -> "mcp": {"tidos": {"type": "local", "command": ["python", "-I", "<TIDOS>/tidos_mcp/__main__.py"]}}
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
