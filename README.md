# MCP Proxy API

这是一个基于Quart框架的MCP（Model Context Protocol）代理API服务器，提供RESTful接口来调用MCP工具。

## 功能特性

- 🔐 JWT令牌认证
- 🛠️ MCP工具代理调用
- 📝 详细的JSON格式日志记录
- 🚀 异步请求处理
- ⚡ SSE连接支持
- 🐳 Docker容器化部署

## 快速开始

### 环境配置

1. 复制配置文件并修改：
```bash
cp env.example .env
```

2. 编辑`.env`文件，配置你的设置：
```env
# MCP服务器配置
MCP_URL=http://localhost:8005/sse

# JWT配置
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256

# 服务器配置
PORT=5000
DEBUG=false
```

### 使用uv安装依赖

```bash
# 安装uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv pip install -e .
```

### 运行服务

```bash
python main.py
```

## API接口

### 1. 调用MCP工具

**POST** `/tools`

请求体：
```json
{
    "method": "tool_name",
    "args": {
        "param1": "value1",
        "param2": "value2"
    }
}
```

认证：在Header中添加 `Authorization: Bearer <jwt_token>` 或在URL参数中添加 `?token=<jwt_token>`

响应：
```json
{
    "success": true,
    "result": "工具执行结果",
    "method": "tool_name"
}
```

### 2. 列出可用工具

**GET** `/tools/list`

认证：同上

响应：
```json
{
    "success": true,
    "tools": ["tool1", "tool2", "tool3"]
}
```

### 3. 健康检查

**GET** `/health`

响应：
```json
{
    "success": true,
    "status": "healthy",
    "mcp_connected": true,
    "available_tools_count": 3
}
```

## 错误处理

API使用标准的HTTP状态码和以下错误格式：

```json
{
    "success": false,
    "error": {
        "message": "错误描述",
        "code": 400
    }
}
```

常见错误码：
- `400` - 请求参数无效
- `401` - 认证失败
- `404` - 工具不存在
- `503` - MCP服务器连接失败

## Docker部署

### 构建镜像

```bash
docker build -t mcp-proxy .
```

### 运行容器

```bash
docker run -d \
  --name mcp-proxy \
  -p 5000:5000 \
  -e MCP_URL=http://your-mcp-server:8005/sse \
  -e JWT_SECRET=your-secret-key \
  mcp-proxy
```

## 开发

### 项目结构

```
mcp_proxy/
├── main.py           # 主应用文件
├── pyproject.toml    # 项目配置
├── Dockerfile        # Docker配置
├── env.example       # 环境变量示例
└── README.md         # 使用说明
```

### 日志格式

应用会输出详细的JSON格式日志：

```json
{
    "timestamp": "2023-12-01T10:00:00.000Z",
    "request": {"method": "get_time", "args": {}},
    "response": {"success": true, "result": "2023-12-01 10:00:00"},
    "status_code": 200,
    "execution_time_ms": 125.5,
    "remote_addr": "192.168.1.100",
    "user_agent": "curl/7.68.0"
}
```

## 许可证

MIT License
