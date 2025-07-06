import socket
import struct
import threading

# === 服务器监听的 IP 和端口 ===
HOST = '0.0.0.0'  # 监听所有可用网卡地址
PORT = 12345      # 服务器使用的 TCP 端口

# === 客户端处理函数 ===
def handle_client(conn, addr):
    print(f"Connected by {addr}")  # 打印新连接的客户端地址

    try:
        # === 收 Initialization 报文 ===
        data = conn.recv(6)  # 从连接中读取 6 字节 (2 bytes Type + 4 bytes Block num)
        msg_type, block_num = struct.unpack('!HI', data)  # 使用网络字节序解包成 Type 和块数量
        print(f"Received Initialization: Type={msg_type}, Block num={block_num}")  # 打印收到的信息

        # === 回复 agree 报文 ===
        conn.sendall(struct.pack('!H', 2))  # 使用网络字节序打包 Type=2 并发送，表示同意
        print("Sent agree: Type=2")  # 打印确认信息

        # === 循环接收每个块 ===
        for idx in range(block_num):  # 根据客户端声明的块数循环处理
            # === 收块的 Type ===
            recv_type = struct.unpack('!H', conn.recv(2))[0]  # 先读 2 字节 Type 并解包

            # === 收块的长度 ===
            recv_len = struct.unpack('!I', conn.recv(4))[0]  # 再读 4 字节长度并解包

            # === 收块的数据 ===
            chunk = b''  # 初始化空字节串，存放接收的数据
            while len(chunk) < recv_len:  # 循环，直到收够 recv_len 个字节
                chunk += conn.recv(recv_len - len(chunk))  # 一次可能收不完，所以循环累加

            print(f"Received reverseRequest: Type={recv_type}, Length={recv_len}")  # 打印收到的块信息
            print(f"Original chunk: {chunk.decode('utf-8', errors='ignore')}")  # 尝试以 UTF-8 解码原文，方便看内容

            # === 反转块内容 ===
            reversed_chunk = chunk[::-1]  # 用切片语法把字节串反转
            print(f"Reversed chunk: {reversed_chunk.decode('utf-8', errors='ignore')}")  # 打印反转后的结果

            # === 发送 reverseAnswer 报文 ===
            conn.sendall(struct.pack('!H', 4))  # 先发 Type=4 (2 bytes)，表示反转应答
            conn.sendall(struct.pack('!I', len(reversed_chunk)))  # 再发长度 (4 bytes)
            conn.sendall(reversed_chunk)  # 最后发反转后的实际数据

            print(f"Sent reverseAnswer {idx+1}")  # 打印发送成功

    except Exception as e:
        print(f"Error handling client {addr}: {e}")  # 捕获异常并打印错误信息

    finally:
        conn.close()  # 无论是否异常，都要关闭与客户端的连接
        print(f"Connection with {addr} closed.")  # 打印连接关闭信息

# === 服务器主函数 ===
def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # 创建 TCP socket
        s.bind((HOST, PORT))  # 绑定 IP 和端口
        s.listen()  # 开始监听，接收连接
        print(f"Server listening on {HOST}:{PORT}")  # 打印监听状态

        while True:
            conn, addr = s.accept()  # 阻塞等待新连接，返回连接和客户端地址
            # === 为新客户端创建并启动线程 ===
            t = threading.Thread(target=handle_client, args=(conn, addr))  # 用线程处理新连接
            t.start()  # 启动线程

# === 程序入口 ===
if __name__ == '__main__':
    main()  # 调用主函数，启动服务器
