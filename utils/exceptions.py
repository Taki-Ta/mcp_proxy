"""
自定义异常类
"""

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

class JWTValidationError(APIError):
    """JWT验证错误"""
    def __init__(self, message: str = "JWT令牌验证失败"):
        super().__init__(message, 401) 