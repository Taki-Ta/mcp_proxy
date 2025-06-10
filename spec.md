使用Flask 实现一个api。该api接收一个JSON格式的请求体。
``` json
{
    "method":"tool name",
    "args":{
        "param1":"value1",
        "param2":"value2",
        ...
    }
}

```
- 1. 定义常用的错误类型
- 2. 读取.env中的MCP_URL值，作为sse的url。第一次启动后，列出所有的mcp工具
- 3. 根据请求体中的method值，检查是否存在对应的mcp工具，如果不存在，返回错误。
- 4. 支持在header 中传递Authorization信息，采用jwt token，默认使用HS256算法，格式为Bearer token，如果header中不存在Authorization信息，则查看url中是否存在，如果不存在，则返回错误。 
- 5. 支持使用.env配置jwt token的算法和密钥，默认使用HS256算法。
- 5. 记录收到的request 和发送的request、response的日志，日志格式为JSON，包含请求体、响应体、状态码、时间戳等信息。
- 4. 如果存在，调用对应的mcp工具，并将params作为参数传递给该工具。
- 5. 返回工具执行的结果，格式为JSON。
- 6. 编写Dockerfile，默认使用ubuntu amd64镜像，安装Python3和Flask，并将代码复制到容器中。
- 7. 使用uv管理python

