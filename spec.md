使用Quart 实现一个MCP代理API。该API接收一个JSON格式的请求体。

## 🔧 工具调用API
``` json
{
    "method":"tool name",
    "args":{
        "param1":"value1",
        "param2":"value2",
        ...
    },
    "server":"http://optional-preferred-server:8999/sse"  // 可选的优先服务器
}
```

## 📋 功能需求

### 🌐 多服务器支持
- 1. 支持单个MCP服务器配置（MCP_URL）- 向后兼容
- 2. 支持多个MCP服务器配置（MCP_URLS），使用逗号分隔多个URL
- 3. 系统启动时并行连接所有配置的服务器
- 4. 构建工具注册表，记录每个工具在哪些服务器上可用
- 5. 实现负载均衡和故障转移机制

### 🔍 错误处理
- 1. 定义常用的错误类型
- 2. 支持部分服务器连接失败的容错机制

### 🛠️ 工具管理
- 3. 列出所有MCP工具，显示每个工具的可用服务器
- 4. 根据请求体中的method值，检查是否存在对应的mcp工具
- 5. 支持指定优先服务器调用工具
- 6. 当指定服务器失败时，自动切换到其他可用服务器

### 🔐 认证机制
- 4. 支持在header中传递Authorization信息，采用JWT token，默认使用HS256算法，格式为Bearer token
- 5. 如果header中不存在Authorization信息，则查看URL中是否存在token参数
- 6. 支持使用.env配置JWT token的算法和密钥，默认使用HS256算法
- 7. 强制验证JWT的exp字段，确保令牌有效性

### 📊 日志记录
- 5. 记录收到的request和发送的request、response的日志
- 6. 日志格式为JSON，包含请求体、响应体、状态码、执行时间、客户端IP等信息

### 🌐 API端点
- `/tools` - POST: 调用MCP工具
- `/tools/list` - GET: 获取工具列表（支持?server=URL参数筛选）
- `/servers` - GET: 获取所有服务器状态
- `/health` - GET: 健康检查，显示所有服务器连接状态

### 🐳 部署支持
- 7. 编写Dockerfile，支持pip和uv两种包管理方式
- 8. 提供docker-compose配置文件
- 9. 支持多种部署环境（开发/生产）

