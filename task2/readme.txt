一. 运行环境
Python 版本：Python 3.12
操作系统：Windows 11
依赖库：无额外依赖，使用 Python 标准库（socket、struct、random、time）

二. 配置选项说明
serverIP: 服务器 IP 地址（127.0.0.1）
serverPort: 服务器端口号（9999）
totalPackets: 要发送的数据块总数（50）
运行示例：
python udpclient.py 127.0.0.1 9999 50

三. 程序功能
udpserver.py：UDP 服务器端，功能：
udpclient.py：UDP 客户端，功能：
四. 运行方式
1. 先运行服务器：
   python udpserver.py
2. 再运行客户端：
   python udpclient.py 127.0.0.1 9999 50
