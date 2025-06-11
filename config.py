"""
配置管理模块
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# JWT配置
JWT_SECRET = os.getenv('JWT_SECRET', 'default-secret-key')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

# MCP服务器配置
MCP_URL = os.getenv('MCP_URL', 'http://localhost:3000/sse')

# 连接管理配置
KEEPALIVE_INTERVAL = int(os.getenv('KEEPALIVE_INTERVAL', 300))  # 保活检查间隔（秒）
CONNECTION_TIMEOUT = int(os.getenv('CONNECTION_TIMEOUT', 5))   # 连接超时时间（秒）

# 服务器配置
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO') 