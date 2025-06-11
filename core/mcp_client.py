"""
MCP客户端模块
"""
import logging
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from utils.exceptions import MCPConnectionError, ToolNotFoundError, APIError

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP客户端类"""
    
    def __init__(self, server_url: str):
        """初始化MCP客户端"""
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[str] = []

    async def connect(self):
        """连接到MCP服务器"""
        try:
            logger.info(f"正在连接到MCP服务器: {self.server_url}")
            read, write = await self.exit_stack.enter_async_context(
                sse_client(url=self.server_url)
            )
            self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            
            # 获取可用工具列表
            response = await self.session.list_tools()
            self.available_tools = [tool.name for tool in response.tools]
            logger.info(f"MCP服务器已连接，可用工具: {self.available_tools}")
            
        except Exception as e:
            logger.error(f"MCP服务器连接失败: {str(e)}", exc_info=True)
            # 清理已分配的资源
            await self.cleanup()
            raise MCPConnectionError(f"连接失败: {str(e)}")

    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]):
        """调用MCP工具"""
        if tool_name not in self.available_tools:
            raise ToolNotFoundError(tool_name)
        
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            return result
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
            raise APIError(f"调用工具失败: {str(e)}")

    async def list_tools(self):
        """获取工具列表"""
        try:
            return await self.session.list_tools()
        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}")
            raise APIError(f"获取工具列表失败: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()
        except Exception as e:
            logger.error(f"清理MCP客户端资源时出错: {str(e)}")

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.session is not None

    @property
    def tools_count(self) -> int:
        """获取可用工具数量"""
        return len(self.available_tools) 