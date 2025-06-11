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

# 全局MCP客户端引用（在app.py中设置）
mcp_client = None

def set_mcp_client(client):
    """设置MCP客户端引用"""
    global mcp_client
    mcp_client = client

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
        
        if not method:
            raise ValidationError("缺少必需的 'method' 字段")
        
        if not isinstance(args, dict):
            raise ValidationError("'args' 字段必须是对象类型")
        
        # 调用MCP工具
        result = await mcp_client.call_tool(method, args)
        
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
        
        # 获取工具列表
        response = await mcp_client.list_tools()
        logger.info(f"从MCP服务器获取到 {len(response.tools)} 个工具")
        
        # 序列化工具列表
        tools_data = []
        for i, tool in enumerate(response.tools):
            try:
                serialized_tool = serialize_tool(tool)
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

@api_bp.route('/health', methods=['GET'])
async def health_check():
    """健康检查端点"""
    mcp_connected = False
    available_tools_count = 0
    
    if mcp_client:
        try:
            # 使用更精确的连接健康检查
            mcp_connected = await mcp_client._check_connection_health()
            available_tools_count = mcp_client.tools_count
        except Exception as e:
            logger.warning(f"健康检查时发生错误: {str(e)}")
            mcp_connected = False
    
    return jsonify({
        "status": "healthy",
        "mcp_connected": mcp_connected,
        "available_tools_count": available_tools_count
    }) 