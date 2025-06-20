"""
MCP客户端管理器模块
管理多个MCP服务器连接
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from core.mcp_client import MCPClient
from utils.exceptions import MCPConnectionError, ToolNotFoundError, APIError

logger = logging.getLogger(__name__)

class MCPClientManager:
    """MCP客户端管理器，管理多个MCP服务器连接"""
    
    def __init__(self, server_urls: List[str]):
        """初始化MCP客户端管理器"""
        self.server_urls = server_urls
        self.clients: Dict[str, MCPClient] = {}
        self.tool_registry: Dict[str, List[str]] = {}  # 工具名 -> 服务器URL列表
        self._connection_lock = asyncio.Lock()

    async def connect_all(self):
        """连接到所有MCP服务器"""
        async with self._connection_lock:
            logger.info(f"正在连接到 {len(self.server_urls)} 个MCP服务器...")
            
            # 并行连接所有服务器
            tasks = []
            for url in self.server_urls:
                client = MCPClient(url)
                self.clients[url] = client
                tasks.append(self._connect_single_client(url, client))
            
            # 等待所有连接完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查连接结果
            connected_count = 0
            for i, result in enumerate(results):
                url = self.server_urls[i]
                if isinstance(result, Exception):
                    logger.error(f"连接到 {url} 失败: {str(result)}")
                    # 从客户端字典中移除失败的客户端
                    if url in self.clients:
                        del self.clients[url]
                else:
                    connected_count += 1
            
            if connected_count == 0:
                raise MCPConnectionError("所有MCP服务器连接失败")
            
            logger.info(f"成功连接到 {connected_count}/{len(self.server_urls)} 个MCP服务器")
            
            # 构建工具注册表
            await self._build_tool_registry()

    async def _connect_single_client(self, url: str, client: MCPClient):
        """连接单个MCP客户端"""
        try:
            await client.connect()
            logger.info(f"成功连接到MCP服务器: {url}")
        except Exception as e:
            logger.error(f"连接到MCP服务器 {url} 失败: {str(e)}")
            raise

    async def _build_tool_registry(self):
        """构建工具注册表，记录每个工具可用的服务器"""
        self.tool_registry = {}
        
        for url, client in self.clients.items():
            try:
                for tool_name in client.available_tools:
                    if tool_name not in self.tool_registry:
                        self.tool_registry[tool_name] = []
                    self.tool_registry[tool_name].append(url)
            except Exception as e:
                logger.error(f"获取服务器 {url} 工具列表失败: {str(e)}")
        
        logger.info(f"工具注册表构建完成，共注册 {len(self.tool_registry)} 个工具")

    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any], preferred_server: Optional[str] = None):
        """调用MCP工具，支持指定优先服务器"""
        if tool_name not in self.tool_registry:
            raise ToolNotFoundError(tool_name)
        
        available_servers = self.tool_registry[tool_name]
        
        # 如果指定了优先服务器且该服务器可用，优先使用
        if preferred_server and preferred_server in available_servers:
            try:
                client = self.clients[preferred_server]
                return await client.call_tool(tool_name, tool_args)
            except Exception as e:
                logger.warning(f"使用优先服务器 {preferred_server} 调用工具失败: {str(e)}")
                # 失败后继续尝试其他服务器
        
        # 尝试所有可用的服务器
        last_error = None
        for server_url in available_servers:
            if server_url == preferred_server:
                continue  # 已经尝试过了
            
            try:
                client = self.clients[server_url]
                result = await client.call_tool(tool_name, tool_args)
                logger.info(f"成功使用服务器 {server_url} 调用工具 {tool_name}")
                return result
            except Exception as e:
                logger.warning(f"服务器 {server_url} 调用工具 {tool_name} 失败: {str(e)}")
                last_error = e
                continue
        
        # 所有服务器都失败了
        if last_error:
            raise APIError(f"调用工具 {tool_name} 失败，所有服务器都不可用: {str(last_error)}")
        else:
            raise APIError(f"调用工具 {tool_name} 失败，没有可用的服务器")

    async def list_tools(self, server_url: Optional[str] = None):
        """获取工具列表，可指定特定服务器"""
        if server_url:
            # 获取特定服务器的工具列表
            if server_url not in self.clients:
                raise APIError(f"服务器 {server_url} 不存在或未连接")
            
            client = self.clients[server_url]
            return await client.list_tools()
        else:
            # 获取所有服务器的工具列表合并
            all_tools = {}
            tool_servers = {}  # 记录每个工具来自哪些服务器
            
            for url, client in self.clients.items():
                try:
                    response = await client.list_tools()
                    for tool in response.tools:
                        tool_name = tool.name
                        if tool_name not in all_tools:
                            all_tools[tool_name] = tool
                            tool_servers[tool_name] = []
                        tool_servers[tool_name].append(url)
                except Exception as e:
                    logger.error(f"获取服务器 {url} 工具列表失败: {str(e)}")
            
            # 创建响应对象
            class ToolsResponse:
                def __init__(self, tools):
                    self.tools = tools
            
            # 为每个工具添加服务器信息
            tools_with_servers = []
            for tool_name, tool in all_tools.items():
                tool_dict = tool.__dict__.copy() if hasattr(tool, '__dict__') else {}
                tool_dict['available_servers'] = tool_servers.get(tool_name, [])
                tool_dict['server_count'] = len(tool_dict['available_servers'])
                
                # 创建工具对象
                class ToolWithServers:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                
                tools_with_servers.append(ToolWithServers(**tool_dict))
            
            return ToolsResponse(tools_with_servers)

    async def get_server_status(self):
        """获取所有服务器状态"""
        status = {}
        for url, client in self.clients.items():
            try:
                is_healthy = await client._check_connection_health()
                status[url] = {
                    "connected": is_healthy,
                    "tools_count": client.tools_count,
                    "available_tools": client.available_tools
                }
            except Exception as e:
                status[url] = {
                    "connected": False,
                    "error": str(e),
                    "tools_count": 0,
                    "available_tools": []
                }
        
        return status

    async def _ensure_all_connected(self):
        """确保所有客户端连接可用，断开的会重连"""
        for url, client in list(self.clients.items()):
            try:
                if not await client._check_connection_health():
                    logger.warning(f"检测到服务器 {url} 连接断开，尝试重连...")
                    await client.connect()
            except Exception as e:
                logger.error(f"重连服务器 {url} 失败: {str(e)}")

    async def cleanup(self):
        """清理所有客户端连接"""
        async with self._connection_lock:
            logger.info("正在清理所有MCP客户端连接...")
            cleanup_tasks = []
            
            for url, client in self.clients.items():
                cleanup_tasks.append(self._cleanup_single_client(url, client))
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self.clients.clear()
            self.tool_registry.clear()
            logger.info("所有MCP客户端连接已清理")

    async def _cleanup_single_client(self, url: str, client: MCPClient):
        """清理单个客户端连接"""
        try:
            await client.cleanup()
            logger.info(f"成功清理服务器 {url} 的连接")
        except Exception as e:
            logger.error(f"清理服务器 {url} 连接时出错: {str(e)}")

    @property
    def total_tools_count(self) -> int:
        """获取所有服务器的工具总数"""
        return len(self.tool_registry)

    @property
    def connected_servers_count(self) -> int:
        """获取已连接的服务器数量"""
        return len(self.clients)

    @property
    def available_servers(self) -> List[str]:
        """获取可用服务器列表"""
        return list(self.clients.keys()) 