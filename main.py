import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import AsyncExitStack
import jwt
from datetime import timezone
from quart import Quart, request, jsonify
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """API基础错误类"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(APIError):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, 401)

class ToolNotFoundError(APIError):
    """工具未找到错误"""
    def __init__(self, tool_name: str):
        super().__init__(f"工具 '{tool_name}' 不存在", 404)

class ValidationError(APIError):
    """请求参数验证错误"""
    def __init__(self, message: str = "请求参数无效"):
        super().__init__(message, 400)

class MCPConnectionError(APIError):
    """MCP连接错误"""
    def __init__(self, message: str = "MCP服务器连接失败"):
        super().__init__(message, 503)

class MCPClient:
    def __init__(self, server_url: str):
        """初始化MCP客户端"""
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools = []

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
            logger.error(f"MCP服务器连接失败: {str(e)}")
            raise MCPConnectionError(f"连接失败: {str(e)}")

    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """调用MCP工具"""
        if tool_name not in self.available_tools:
            raise ToolNotFoundError(tool_name)
        
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            tool_result = str(result.content) if hasattr(result, 'content') else str(result)
            return tool_result
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
            raise APIError(f"调用工具失败: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

# 创建Quart应用
app = Quart(__name__)

# 配置
JWT_SECRET = os.getenv('JWT_SECRET', 'default-secret-key')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
MCP_URL = os.getenv('MCP_URL', 'http://10.10.1.105:8005/sse')

# 全局MCP客户端
mcp_client = None

def log_request_response(request_data: dict, response_data: dict, status_code: int, execution_time: float, remote_addr: str = None, user_agent: str = None):
    """记录请求和响应日志"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": request_data,
        "response": response_data,
        "status_code": status_code,
        "execution_time_ms": round(execution_time * 1000, 2),
        "remote_addr": remote_addr,
        "user_agent": user_agent
    }
    logger.info(json.dumps(log_entry, ensure_ascii=False))

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        logger.error(f"令牌验证失败: {str(e)}")
        raise AuthenticationError("令牌验证失败")


def get_token_from_request():
    """从请求中获取JWT令牌"""
    # 首先检查Header中的Authorization
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # 移除 'Bearer ' 前缀
    
    # 然后检查URL参数中的token
    token = request.args.get('token')
    if token:
        return token
    
    raise AuthenticationError("缺少认证令牌")

@app.errorhandler(APIError)
def handle_api_error(error):
    """处理API错误"""
    response = {
        "success": False,
        "error": {
            "message": error.message,
            "code": error.status_code
        }
    }
    return jsonify(response), error.status_code

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """处理未预期的错误"""
    logger.error(f"未预期的错误: {str(error)}")
    response = {
        "success": False,
        "error": {
            "message": "内部服务器错误",
            "code": 500
        }
    }
    return jsonify(response), 500

@app.route('/tools', methods=['POST'])
async def call_tool():
    """调用MCP工具的API端点"""
    start_time = datetime.now(timezone.utc)
    request_data = {}
    response_data = {}
    status_code = 200
    
    try:
        # 获取请求数据
        request_data = await request.get_json()
        if not request_data:
            raise ValidationError("请求体不能为空")
        
        # 验证JWT令牌
        token = get_token_from_request()
        user_payload = verify_jwt_token(token)
        
        # 验证请求格式
        method = request_data.get('method')
        args = request_data.get('args', {})
        
        if not method:
            raise ValidationError("缺少必需的 'method' 字段")
        
        if not isinstance(args, dict):
            raise ValidationError("'args' 字段必须是对象类型")
        
        # 调用MCP工具
        result = await mcp_client.call_tool(method, args)
        
        response_data = {
            "success": True,
            "result": result,
            "method": method
        }
        
    except APIError as e:
        status_code = e.status_code
        response_data = {
            "success": False,
            "error": {
                "message": e.message,
                "code": e.status_code
            }
        }
    except Exception as e:
        status_code = 500
        response_data = {
            "success": False,
            "error": {
                "message": "内部服务器错误",
                "code": 500
            }
        }
        logger.error(f"未预期的错误: {str(e)}")
    
    finally:
        # 记录日志
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        log_request_response(request_data, response_data, status_code, execution_time, remote_addr, user_agent)
    
    return jsonify(response_data), status_code

@app.route('/tools/list', methods=['GET'])
async def list_tools():
    """列出所有可用的MCP工具"""
    try:
        # 验证JWT令牌
        token = get_token_from_request()
        user_payload = verify_jwt_token(token)
        
        response_data = {
            "success": True,
            "tools": mcp_client.available_tools
        }
        return jsonify(response_data)
        
    except APIError as e:
        response_data = {
            "success": False,
            "error": {
                "message": e.message,
                "code": e.status_code
            }
        }
        return jsonify(response_data), e.status_code

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "success": True,
        "status": "healthy",
        "mcp_connected": mcp_client is not None and mcp_client.session is not None,
        "available_tools_count": len(mcp_client.available_tools) if mcp_client else 0
    })

async def init_mcp_client():
    """初始化MCP客户端"""
    global mcp_client
    mcp_client = MCPClient(MCP_URL)
    await mcp_client.connect()

@app.before_serving
async def startup():
    """应用启动前的初始化"""
    await init_mcp_client()

def main():
    """主函数"""
    # 启动Quart应用
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"启动Quart应用，端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
