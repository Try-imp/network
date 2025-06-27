import socket
import struct
import sys
import random

# === 读取命令行参数 ===
# 用法示例: python reverseTCPClient.py 127.0.0.1 12345 5 10
server_ip = sys.argv[1]
server_port = int(sys.argv[2])
Lmin = int(sys.argv[3])
Lmax = int(sys.argv[4])

# === 读取源文件 ===
with open('source.txt', 'rb') as fin:
    data = fin.read()

# === 按 Lmin~Lmax 随机拆块 ===
blocks = []
i = 0
while i < len(data):
    blk_size = random.randint(Lmin, Lmax)
    blk = data[i:i+blk_size]
    blocks.append(blk)
    i += blk_size

N = len(blocks)
print(f"总共拆成 {N} 块")

# === 建立 TCP 连接 ===
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server_ip, server_port))
print(f"已连接服务器 {server_ip}:{server_port}")

# === 发送 Initialization ===
s.sendall(struct.pack('!HI', 1, N))
agree_type = struct.unpack('!H', s.recv(2))[0]
print(f"收到 agree 报文: Type={agree_type}")

# === 存放所有块的列表 ===
all_reversed_blocks = []

# === 循环发块 + 收块 ===
for idx, blk in enumerate(blocks):
    # 发送请求 Type(2) + Length(4) + Data
    s.sendall(struct.pack('!H', 3))
    s.sendall(struct.pack('!I', len(blk)))
    s.sendall(blk)

    print(f"已发送 reverseRequest 块 {idx+1}: {blk.decode('utf-8', errors='ignore')}")

    # 收 Type + Length
    recv_type = struct.unpack('!H', s.recv(2))[0]
    recv_len = struct.unpack('!I', s.recv(4))[0]

    # 收反转后的数据
    reversed_data = b''
    while len(reversed_data) < recv_len:
        reversed_data += s.recv(recv_len - len(reversed_data))

    print(f"已收到 reverseAnswer 块 {idx+1}: {reversed_data.decode('utf-8', errors='ignore')}")

    # 保存到列表
    all_reversed_blocks.append(reversed_data)

# === 块顺序反转后写文件 ===
with open('result.txt', 'wb') as fout:
    for blk in reversed(all_reversed_blocks):
        fout.write(blk)

print("已写入 result.txt (顺序反转完成)")

s.close()
