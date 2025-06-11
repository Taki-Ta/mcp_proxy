"""
MCP客户端模块
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from utils.exceptions import MCPConnectionError, ToolNotFoundError, APIError
from config import CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP客户端类"""
    
    def __init__(self, server_url: str):
        """初始化MCP客户端"""
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[str] = []
        self._connection_lock = asyncio.Lock()

    async def connect(self):
        """连接到MCP服务器"""
        async with self._connection_lock:
            try:
                # 如果已经连接，先清理
                if self.session:
                    await self._cleanup_session()
                
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
                await self._cleanup_session()
                raise MCPConnectionError(f"连接失败: {str(e)}")

    async def _cleanup_session(self):
        """清理当前会话"""
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()
                # 重新创建exit_stack用于下次连接
                self.exit_stack = AsyncExitStack()
            self.session = None
            self.available_tools = []
        except Exception as e:
            logger.error(f"清理会话时出错: {str(e)}")

    async def _ensure_connected(self):
        """确保连接可用，如果断开则重连"""
        if not await self._check_connection_health():
            logger.warning("检测到连接断开，尝试重连...")
            await self.connect()

    async def _check_connection_health(self) -> bool:
        """检查连接健康状态"""
        if not self.session:
            return False
        
        try:
            # 尝试调用一个简单的方法来检查连接是否活跃
            await asyncio.wait_for(self.session.list_tools(), timeout=CONNECTION_TIMEOUT)
            return True
        except Exception as e:
            logger.warning(f"连接健康检查失败: {str(e)}")
            return False

    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]):
        """调用MCP工具"""
        # 确保连接可用
        await self._ensure_connected()
        
        if tool_name not in self.available_tools:
            raise ToolNotFoundError(tool_name)
        
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            return result
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
            # 如果是连接相关错误，尝试重连后再次调用
            if "connection" in str(e).lower() or "sse" in str(e).lower():
                logger.warning("检测到可能的连接错误，尝试重连后重试...")
                try:
                    await self.connect()
                    result = await self.session.call_tool(tool_name, tool_args)
                    return result
                except Exception as retry_e:
                    logger.error(f"重连后重试仍然失败: {str(retry_e)}")
                    raise APIError(f"调用工具失败: {str(retry_e)}")
            else:
                raise APIError(f"调用工具失败: {str(e)}")

    async def list_tools(self):
        """获取工具列表"""
        # 确保连接可用
        await self._ensure_connected()
        
        try:
            return await self.session.list_tools()
        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}")
            # 如果是连接相关错误，尝试重连后再次调用
            if "connection" in str(e).lower() or "sse" in str(e).lower():
                logger.warning("检测到可能的连接错误，尝试重连后重试...")
                try:
                    await self.connect()
                    return await self.session.list_tools()
                except Exception as retry_e:
                    logger.error(f"重连后重试仍然失败: {str(retry_e)}")
                    raise APIError(f"获取工具列表失败: {str(retry_e)}")
            else:
                raise APIError(f"获取工具列表失败: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        async with self._connection_lock:
            await self._cleanup_session()

    @property
    def is_connected(self) -> bool:
        """检查是否已连接（基础检查）"""
        return self.session is not None

    @property
    def tools_count(self) -> int:
        """获取可用工具数量"""
        return len(self.available_tools) 