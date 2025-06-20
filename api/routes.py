"""
API路由模块
"""
import logging
from datetime import datetime, timezone

from quart import Blueprint, request, jsonify
from core.auth import validate_request_auth
from utils.exceptions import APIError, ValidationError
from utils.helpers import serialize_mcp_content, serialize_tool, log_request_response

logger = logging.getLogger(__name__)

# 创建蓝图
api_bp = Blueprint('api', __name__)

# 全局MCP客户端管理器引用（在app.py中设置）
mcp_client_manager = None

def set_mcp_client_manager(manager):
    """设置MCP客户端管理器引用"""
    global mcp_client_manager
    mcp_client_manager = manager

@api_bp.route('/tools', methods=['POST'])
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
        user_payload = validate_request_auth()
        
        # 验证请求格式
        method = request_data.get('method')
        args = request_data.get('args', {})
        preferred_server = request_data.get('server')  # 可选的优先服务器
        
        if not method:
            raise ValidationError("缺少必需的 'method' 字段")
        
        if not isinstance(args, dict):
            raise ValidationError("'args' 字段必须是对象类型")
        
        # 调用MCP工具
        result = await mcp_client_manager.call_tool(method, args, preferred_server)
        
        # 序列化响应数据
        response_data = serialize_mcp_content(result)
        
    except APIError as e:
        status_code = e.status_code
        response_data = {
            "error": {
                "message": e.message,
                "code": e.status_code
            }
        }
    except Exception as e:
        status_code = 500
        response_data = {
            "error": {
                "message": "内部服务器错误",
                "code": 500
            }
        }
        logger.error(f"未预期的错误: {str(e)}", exc_info=True)
    
    finally:
        # 记录日志
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        log_request_response(request_data, response_data, status_code, execution_time, remote_addr, user_agent)
    
    return jsonify(response_data), status_code

@api_bp.route('/tools/list', methods=['GET'])
async def list_tools():
    """列出所有可用的MCP工具"""
    start_time = datetime.now(timezone.utc)
    request_data = {}
    response_data = {}
    status_code = 200
    
    try:
        # 验证JWT令牌
        user_payload = validate_request_auth()
        logger.info(f"用户 {user_payload.get('user_id', 'unknown')} 请求工具列表")
        
        # 获取查询参数
        server_url = request.args.get('server')  # 可选的服务器筛选
        
        # 获取工具列表
        response = await mcp_client_manager.list_tools(server_url)
        logger.info(f"从MCP服务器获取到 {len(response.tools)} 个工具")
        
        # 序列化工具列表
        tools_data = []
        for i, tool in enumerate(response.tools):
            try:
                serialized_tool = serialize_tool(tool)
                # 添加服务器信息（如果有）
                if hasattr(tool, 'available_servers'):
                    serialized_tool['available_servers'] = tool.available_servers
                    serialized_tool['server_count'] = tool.server_count
                tools_data.append(serialized_tool)
                logger.debug(f"成功序列化工具 {i+1}: {serialized_tool.get('name', 'unknown')}")
            except Exception as e:
                logger.error(f"序列化工具 {i+1} 时出错: {str(e)}")
                # 添加错误工具的占位符
                tools_data.append({
                    "name": f"tool_{i+1}",
                    "description": f"序列化失败: {str(e)}",
                    "error": True
                })
        
        response_data = {"tools": tools_data}
        logger.info(f"成功返回 {len(tools_data)} 个工具的信息")
        
    except APIError as e:
        status_code = e.status_code
        response_data = {
            "error": {
                "message": e.message,
                "code": e.status_code
            }
        }
        logger.error(f"API错误: {e.message}")
        
    except Exception as e:
        status_code = 500
        response_data = {
            "error": {
                "message": "获取工具列表失败",
                "code": 500
            }
        }
        logger.error(f"获取工具列表时发生未预期错误: {str(e)}", exc_info=True)
    
    finally:
        # 记录日志
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        log_request_response(request_data, response_data, status_code, execution_time, remote_addr, user_agent)
    
    return jsonify(response_data), status_code

@api_bp.route('/servers', methods=['GET'])
async def list_servers():
    """列出所有MCP服务器状态"""
    start_time = datetime.now(timezone.utc)
    request_data = {}
    response_data = {}
    status_code = 200
    
    try:
        # 验证JWT令牌
        user_payload = validate_request_auth()
        logger.info(f"用户 {user_payload.get('user_id', 'unknown')} 请求服务器列表")
        
        # 获取服务器状态
        server_status = await mcp_client_manager.get_server_status()
        
        response_data = {
            "servers": server_status,
            "summary": {
                "total_servers": len(server_status),
                "connected_servers": len([s for s in server_status.values() if s.get('connected', False)]),
                "total_tools": mcp_client_manager.total_tools_count
            }
        }
        
    except APIError as e:
        status_code = e.status_code
        response_data = {
            "error": {
                "message": e.message,
                "code": e.status_code
            }
        }
    except Exception as e:
        status_code = 500
        response_data = {
            "error": {
                "message": "获取服务器列表失败",
                "code": 500
            }
        }
        logger.error(f"获取服务器列表时发生未预期错误: {str(e)}", exc_info=True)
    
    finally:
        # 记录日志
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        log_request_response(request_data, response_data, status_code, execution_time, remote_addr, user_agent)
    
    return jsonify(response_data), status_code

@api_bp.route('/health', methods=['GET'])
async def health_check():
    """健康检查端点"""
    server_status = {}
    total_tools = 0
    connected_servers = 0
    
    if mcp_client_manager:
        try:
            server_status = await mcp_client_manager.get_server_status()
            total_tools = mcp_client_manager.total_tools_count
            connected_servers = mcp_client_manager.connected_servers_count
        except Exception as e:
            logger.warning(f"健康检查时发生错误: {str(e)}")
    
    return jsonify({
        "status": "healthy",
        "servers": {
            "total": len(server_status),
            "connected": connected_servers,
            "status": server_status
        },
        "tools": {
            "total": total_tools
        }
    })

# 保持向后兼容的别名
def set_mcp_client(client):
    """保持向后兼容的函数别名"""
    logger.warning("set_mcp_client 已废弃，请使用 set_mcp_client_manager")
    # 这里可以根据需要处理向后兼容逻辑 