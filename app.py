"""
MCP Proxy API 主应用
"""
import logging

from quart import Quart, jsonify
from config import PORT, DEBUG, LOG_LEVEL, MCP_URL
from utils.exceptions import APIError
from core.mcp_client import MCPClient
from api.routes import api_bp, set_mcp_client

# 配置日志
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# 全局MCP客户端
mcp_client = None

def create_app():
    """创建Quart应用"""
    app = Quart(__name__)
    
    # 注册蓝图
    app.register_blueprint(api_bp)
    
    # 注册错误处理器
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """处理API错误"""
        response = {
            "error": {
                "message": error.message,
                "code": error.status_code
            }
        }
        return jsonify(response), error.status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """处理未预期的错误"""
        logger.error(f"未预期的错误: {str(error)}", exc_info=True)
        response = {
            "error": {
                "message": "内部服务器错误",
                "code": 500
            }
        }
        return jsonify(response), 500

    # 应用生命周期钩子
    @app.before_serving
    async def startup():
        """应用启动前的初始化"""
        await init_mcp_client()

    @app.after_serving
    async def shutdown():
        """应用关闭时的清理"""
        await cleanup_mcp_client()
    
    return app

async def init_mcp_client():
    """初始化MCP客户端"""
    global mcp_client
    try:
        mcp_client = MCPClient(MCP_URL)
        await mcp_client.connect()
        # 设置路由模块中的客户端引用
        set_mcp_client(mcp_client)
        logger.info("MCP客户端初始化成功")
    except Exception as e:
        logger.error(f"MCP客户端初始化失败: {str(e)}")
        raise

async def cleanup_mcp_client():
    """清理MCP客户端"""
    global mcp_client
    if mcp_client:
        try:
            await mcp_client.cleanup()
            logger.info("MCP客户端已清理")
        except Exception as e:
            logger.error(f"清理MCP客户端时出错: {str(e)}")
        finally:
            mcp_client = None

def main():
    """主函数"""
    app = create_app()
    logger.info(f"启动MCP Proxy API服务器，端口: {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

if __name__ == "__main__":
    main() 