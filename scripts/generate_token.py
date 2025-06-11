#!/usr/bin/env python3
"""
JWT令牌生成脚本
用于生成测试用的JWT令牌
"""

import jwt
import os
from datetime import datetime, timedelta, timezone

# 支持直接运行和模块运行
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass

# 加载环境变量
load_dotenv()

def generate_token(user_id: str = "test_user", expires_in_hours: int = 24):
    """生成JWT令牌
    
    Args:
        user_id: 用户ID
        expires_in_hours: 令牌有效期（小时）
    
    Returns:
        str: JWT令牌
        
    Note:
        exp字段是必须的，API会强制验证过期时间
    """
    secret = os.getenv('JWT_SECRET', 'default-secret-key')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
    
    # 构建payload - exp字段是必须的
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'iat': now,  # 签发时间
        'exp': now + timedelta(hours=expires_in_hours),  # 过期时间（必须）
        'iss': 'mcp-proxy',  # 签发者
    }
    
    # 生成令牌
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token

def main():
    """主函数"""
    print("MCP Proxy JWT令牌生成器")
    print("=" * 30)
    
    # 获取用户输入
    user_id = input("请输入用户ID (默认: test_user): ").strip()
    if not user_id:
        user_id = "test_user"
    
    try:
        hours = input("请输入令牌有效期（小时，默认: 24): ").strip()
        hours = int(hours) if hours else 24
    except ValueError:
        hours = 24
    
    # 生成令牌
    try:
        token = generate_token(user_id, hours)
        
        print(f"\n生成成功！")
        print(f"用户ID: {user_id}")
        print(f"有效期: {hours}小时")
        print(f"JWT令牌:")
        print(f"{token}")
        
        print(f"\n使用方法:")
        print(f"1. Header认证: Authorization: Bearer {token}")
        print(f"2. URL参数认证: ?token={token}")
        
    except Exception as e:
        print(f"生成失败: {str(e)}")

if __name__ == "__main__":
    main() 