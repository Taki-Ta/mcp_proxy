"""
JWT认证模块
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import jwt

from quart import request
from config import JWT_SECRET, JWT_ALGORITHM
from utils.exceptions import AuthenticationError, JWTValidationError

logger = logging.getLogger(__name__)

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """验证JWT令牌"""
    try:
        # 解码令牌
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # 验证必须的字段
        if 'exp' not in payload:
            raise JWTValidationError("JWT令牌缺少exp字段")
        
        # 验证过期时间
        exp_timestamp = payload['exp']
        current_timestamp = datetime.now(timezone.utc).timestamp()
        
        if exp_timestamp <= current_timestamp:
            raise JWTValidationError("JWT令牌已过期")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise JWTValidationError("JWT令牌已过期")
    except jwt.InvalidTokenError as e:
        raise JWTValidationError(f"JWT令牌无效: {str(e)}")
    except Exception as e:
        logger.error(f"JWT令牌验证失败: {str(e)}")
        raise JWTValidationError("JWT令牌验证失败")

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

def validate_request_auth():
    """验证请求的认证信息"""
    token = get_token_from_request()
    payload = verify_jwt_token(token)
    return payload 