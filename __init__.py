"""
MCP Proxy API Package
"""

__version__ = "1.0.0"
__author__ = "MCP Proxy Team"
__description__ = "MCP (Model Context Protocol) Proxy API Server"

from .app import create_app, main
from .core import MCPClient
from .utils import APIError
from .api import api_bp

__all__ = ['create_app', 'main', 'MCPClient', 'APIError', 'api_bp'] 