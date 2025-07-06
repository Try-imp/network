一.运行环境
Python 版本：Python 3.13
操作系统：Windows 11
依赖库：无额外依赖，使用 Python 标准库（socket、struct、random）

二.配置选项说明
serverIP: 服务器 IP 地址（127.0.0.1）
serverPort: 服务器端口号（12345）
Lmin: 拆块的最小长度（5）
Lmax: 拆块的最大长度（10）

   python reverseTCPClient.py 127.0.0.1 12345 5 10

三.程序功能
reverseTCPServer.py：接收文本块，反转后返回
reverseTCPClient.py：读取 source.txt，随机拆块发送，输出结果到 result.txt

四.运行方式
先运行服务器：python reverseTCPServer.py
再运行客户端：python reverseTCPClient.py