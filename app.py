"""
MCP Proxy API 主应用
"""
import asyncio
import logging

from quart import Quart, jsonify
from config import PORT, DEBUG, LOG_LEVEL, MCP_URLS, KEEPALIVE_INTERVAL
from utils.exceptions import APIError
from core.mcp_client_manager import MCPClientManager
from api.routes import api_bp, set_mcp_client_manager

# 配置日志
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# 全局MCP客户端管理器
mcp_client_manager = None
# 保活任务
keepalive_task = None

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
        await init_mcp_client_manager()

    @app.after_serving
    async def shutdown():
        """应用关闭时的清理"""
        await cleanup_mcp_client_manager()
    
    return app

async def init_mcp_client_manager():
    """初始化MCP客户端管理器"""
    global mcp_client_manager, keepalive_task
    try:
        logger.info(f"初始化MCP客户端管理器，配置的服务器: {MCP_URLS}")
        mcp_client_manager = MCPClientManager(MCP_URLS)
        await mcp_client_manager.connect_all()
        
        # 设置路由模块中的客户端管理器引用
        set_mcp_client_manager(mcp_client_manager)
        
        # 启动保活任务
        keepalive_task = asyncio.create_task(keepalive_loop())
        logger.info(f"MCP客户端管理器初始化成功，已连接 {mcp_client_manager.connected_servers_count} 个服务器，保活任务已启动")
    except Exception as e:
        logger.error(f"MCP客户端管理器初始化失败: {str(e)}")
        raise

async def keepalive_loop():
    """MCP连接保活循环"""
    global mcp_client_manager
    while True:
        try:
            # 根据配置的间隔检查连接状态
            await asyncio.sleep(KEEPALIVE_INTERVAL)
            
            if mcp_client_manager:
                logger.debug("执行MCP连接保活检查...")
                try:
                    # 确保所有连接都健康
                    await mcp_client_manager._ensure_all_connected()
                    logger.debug(f"MCP连接保活检查完成，当前连接服务器数: {mcp_client_manager.connected_servers_count}")
                except Exception as e:
                    logger.warning(f"保活检查失败: {str(e)}")
            
        except asyncio.CancelledError:
            logger.info("保活任务被取消")
            break
        except Exception as e:
            logger.error(f"保活循环出错: {str(e)}")

async def cleanup_mcp_client_manager():
    """清理MCP客户端管理器"""
    global mcp_client_manager, keepalive_task
    
    # 停止保活任务
    if keepalive_task and not keepalive_task.done():
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass
        logger.info("保活任务已停止")
    
    if mcp_client_manager:
        try:
            await mcp_client_manager.cleanup()
            logger.info("MCP客户端管理器已清理")
        except Exception as e:
            logger.error(f"清理MCP客户端管理器时出错: {str(e)}")
        finally:
            mcp_client_manager = None

def main():
    """主函数"""
    app = create_app()
    logger.info(f"启动MCP Proxy API服务器，端口: {PORT}")
    logger.info(f"配置的MCP服务器: {MCP_URLS}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

if __name__ == "__main__":
    main() 