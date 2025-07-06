import socket
import struct
import sys
import random

# === 读取命令行参数 ===
# 用法示例: python reverseTCPClient.py 127.0.0.1 12345 5 10
server_ip = sys.argv[1]          # 读入第 1 个参数，服务器 IP
server_port = int(sys.argv[2])   # 读入第 2 个参数，服务器端口，转 int
Lmin = int(sys.argv[3])          # 从命令行读入第 3 个参数，块最小长度
Lmax = int(sys.argv[4])          # 从命令行读入第 4 个参数，块最大长度

# === 读取源文件 ===
with open('source.txt', 'rb') as fin:  # 以二进制方式打开 source.txt
    data = fin.read()                  # 读取整个文件内容到 data 变量

# === 按 Lmin~Lmax 随机拆块 ===
blocks = []  # 用列表保存所有拆出来的块
i = 0        # 块拆分的当前位置
while i < len(data):  # 循环直到拆完所有数据
    blk_size = random.randint(Lmin, Lmax)  # 生成 Lmin~Lmax 范围内的随机块大小
    blk = data[i:i+blk_size]               # 从当前位置切出该块
    blocks.append(blk)                     # 把块加入列表
    i += blk_size                          # 更新当前位置

N = len(blocks)  # 总块数
print(f"总共拆成 {N} 块")  # 打印拆块信息

# === 建立 TCP 连接 ===
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 TCP socket
s.connect((server_ip, server_port))  # 连接到服务器
print(f"已连接服务器 {server_ip}:{server_port}")  # 打印连接成功

# === 发送 Initialization 报文 ===
s.sendall(struct.pack('!HI', 1, N))  # 使用网络字节序打包 Type=1 和块数量 N，发送给服务器
agree_type = struct.unpack('!H', s.recv(2))[0]  # 接收服务器回复的 agree 报文（2 字节）
print(f"收到 agree 报文: Type={agree_type}")  # 打印服务器回复

# === 准备保存所有反转后块 ===
all_reversed_blocks = []  # 用列表保存服务器返回的每个反转块

# === 循环发送每块 + 接收返回块 ===
for idx, blk in enumerate(blocks):  # 遍历每个块，带序号
    # === 发送 reverseRequest 报文 ===
    s.sendall(struct.pack('!H', 3))           # 先发 2 字节 Type=3，表示请求反转
    s.sendall(struct.pack('!I', len(blk)))    # 再发 4 字节块长度
    s.sendall(blk)                             # 再发块的实际内容

    print(f"已发送 reverseRequest 块 {idx+1}: {blk.decode('utf-8', errors='ignore')}")  # 打印发送信息

    # === 接收 reverseAnswer 报文 ===
    recv_type = struct.unpack('!H', s.recv(2))[0]  # 收到服务器回复 Type=4
    recv_len = struct.unpack('!I', s.recv(4))[0]   # 收到反转后块的长度

    # === 收完整的反转块 ===
    reversed_data = b''  # 初始化空字节串
    while len(reversed_data) < recv_len:  # 循环直到收够指定长度
        reversed_data += s.recv(recv_len - len(reversed_data))  # 分批接收

    print(f"已收到 reverseAnswer 块 {idx+1}: {reversed_data.decode('utf-8', errors='ignore')}")  # 打印收到的反转块

    # === 保存到列表 ===
    all_reversed_blocks.append(reversed_data)  # 把收到的反转块加入列表

# === 所有块收完后，客户端做块顺序反转后写文件 ===
with open('result.txt', 'wb') as fout:  # 以二进制写模式打开 result.txt
    for blk in reversed(all_reversed_blocks):  # 对块列表整体做顺序反转
        fout.write(blk)                        # 按新顺序写入文件

print("已写入 result.txt (顺序反转完成)")  # 提示写文件完成

s.close()  # 关闭 TCP 连接
