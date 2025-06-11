"""
数据处理工具模块
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)

def serialize_mcp_content(obj) -> Any:
    """
    序列化MCP响应内容，确保可以JSON序列化
    
    Args:
        obj: MCP响应对象
        
    Returns:
        可序列化的数据
    """
    if hasattr(obj, 'content'):
        if isinstance(obj.content, list):
            serialized_list = [serialize_mcp_content(item) for item in obj.content]
            # 如果列表只有一个元素且是JSON字符串，尝试解析它
            if len(serialized_list) == 1 and isinstance(serialized_list[0], str):
                try:
                    return json.loads(serialized_list[0])
                except (json.JSONDecodeError, ValueError):
                    return serialized_list[0]
            return serialized_list
        elif hasattr(obj.content, 'text'):
            text = obj.content.text
            # 尝试解析JSON字符串
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError):
                return text
        elif hasattr(obj.content, 'to_dict'):
            return obj.content.to_dict()
        else:
            return str(obj.content)
    elif hasattr(obj, 'text'):
        text = obj.text
        # 尝试解析JSON字符串
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif isinstance(obj, (dict, list, str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

def serialize_tool(tool) -> Dict[str, Any]:
    """
    序列化MCP工具对象
    
    Args:
        tool: MCP工具对象
        
    Returns:
        序列化后的工具信息
    """
    try:
        # 优先尝试使用to_dict方法
        if hasattr(tool, 'to_dict') and callable(getattr(tool, 'to_dict')):
            return tool.to_dict()
        
        # 如果是Tool对象，手动序列化其属性
        if hasattr(tool, 'name'):
            result = {}
            
            # 提取基本属性
            if hasattr(tool, 'name'):
                result['name'] = tool.name
            if hasattr(tool, 'description'):
                result['description'] = tool.description
            if hasattr(tool, 'inputSchema'):
                result['inputSchema'] = tool.inputSchema
            if hasattr(tool, 'annotations'):
                result['annotations'] = tool.annotations
                
            return result
        
        # 如果有__dict__属性，使用字典形式
        elif hasattr(tool, '__dict__'):
            result = {}
            for key, value in tool.__dict__.items():
                if not key.startswith('_'):
                    # 递归序列化复杂对象
                    if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict)):
                        result[key] = serialize_tool(value)
                    else:
                        result[key] = value
            return result
        
        # 如果是字典，直接返回
        elif isinstance(tool, dict):
            return tool
        
        # 其他情况转换为字符串
        else:
            return {"name": str(tool), "description": "Unknown tool type"}
            
    except Exception as e:
        logger.warning(f"序列化工具时发生错误: {str(e)}")
        # 容错处理：返回基本信息
        return {
            "name": getattr(tool, 'name', 'unknown'),
            "description": getattr(tool, 'description', f'Error serializing tool: {str(e)}'),
            "error": str(e)
        }

def log_request_response(request_data: dict, response_data: dict, status_code: int, 
                        execution_time: float, remote_addr: str = None, user_agent: str = None):
    """
    记录请求和响应日志
    
    Args:
        request_data: 请求数据
        response_data: 响应数据  
        status_code: HTTP状态码
        execution_time: 执行时间（秒）
        remote_addr: 客户端地址
        user_agent: 用户代理
    """
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