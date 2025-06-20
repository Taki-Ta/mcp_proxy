"""
MCP Proxy API Package
"""

__version__ = "0.1.0"
__author__ = "Taki"
__description__ = "Proxy sse mcp to restful api"

from .app import create_app, main
from .core import MCPClient
from .utils import APIError
from .api import api_bp

__all__ = ['create_app', 'main', 'MCPClient', 'APIError', 'api_bp'] 