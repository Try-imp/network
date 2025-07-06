import socket           # 导入 socket 库，做 UDP 通信
import struct           # 用 struct 做数据包二进制封装和解析
import sys              # 用来接收命令行参数
import random           # 生成随机数（生成 payload）
import time             # 用来获取当前时间、计算 RTT
import threading        # 用多线程收 ACK
import pandas as pd     # 用 pandas 做 RTT 汇总分析

# ====== 协议头部（仿 TCP） ======
# 定义数据包头部：
# ‘！’：网络字节序，seq(4字节)，ack(4字节)，flags(2字节)，len(2字节)，timestamp(8字节)
HEADER_FORMAT = '!I I H H Q'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)#头部总共字节数

# ====== 标志位宏定义 ======（十六）
FLAG_SYN = 0x01         # SYN 标志
FLAG_ACK = 0x02         # ACK 标志
FLAG_FIN = 0x04         # FIN 标志

# ====== 从命令行读取参数 ======sys.argv 是Python 的系统参数列表
server_ip = sys.argv[1]             # 服务端 IP
server_port = int(sys.argv[2])      # 服务端端口
total_packets = int(sys.argv[3])    # 总共要发多少个数据块

# 创建 UDP socket
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#创建一个基于 IPv4 的 UDP 套接字，是程序和网络之间收发包的接口。

# === 1. 三次握手：发送 SYN ===
# 封装 SYN 包（seq=0, ack=0, flags=SYN, len=0, timestamp=当前时间）
handshake_pkt = struct.pack(HEADER_FORMAT, 0, 0, FLAG_SYN, 0, int(time.time() * 1000))#毫秒
client.sendto(handshake_pkt, (server_ip, server_port))
print("Sent: SYN")     # 输出提示

# === 接收 SYN-ACK ===
data, _ = client.recvfrom(1024)  # 接收服务端返回
seq, ack, flags, pkt_len, ts = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])#20
# 判断是否是 SYN+ACK
if not (flags & FLAG_SYN and flags & FLAG_ACK):
    print("Handshake failed")
    sys.exit(1)#非正常退出
print(f"Received: SYN-ACK (ack={ack})")

# === 2. 发送参数配置 ===
window_size = 5            # GBN 窗口大小
base = 1                   # 滑动窗口 base，起点 1#
next_seq_idx = 1           # 下一个要发的块序号

# 生成要发送的所有数据块
blocks = []                # 保存所有数据块：[(起始字节, 长度, payload)]
start_byte = 1             # 当前块起始字节偏移
for _ in range(total_packets):
    payload_len = random.randint(40, 80)                  # 块长度随机 40~80
    payload = bytes([random.randint(65, 90) for _ in range(payload_len)])  # 生成随机大写字母
    blocks.append((start_byte, payload_len, payload))     # 保存块信息
    start_byte += payload_len                             # 更新下一块的起始字节

send_times = {}            # 保存每个块的发送时间（用于算 RTT）
rtts = []                  # 保存所有 RTT
acked_seq = set()          # 已经确认的块序号#
total_sent = 0             # 统计实际总发送的块数

DEFAULT_TIMEOUT = 0.3      # 默认超时时间（秒）
lock = threading.Lock()    # 用锁保护 base、acked_seq
running = True             # 用来控制收 ACK 的线程

# === 3. 收 ACK 的线程 ===
def recv_ack():
    global base, running
    while running:
        try:
            data, _ = client.recvfrom(1024)   # 阻塞收 ACK 包
            recv_time = time.time()           # 记录当前接收时间（用于算 RTT）
            seq, ack_num, flags, pkt_len, ts = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])

            if flags & FLAG_ACK:  # 判断包里带 ACK 标志
                with lock:
                    acked_byte = ack_num - 1  # ack_num 表示累计确认到哪一个字节，减 1 得到最后确认字节
                    confirmed_idx = None  # 初始化blocks 列表中的索引
                    # 遍历所有块找出哪块被这个 ACK 覆盖
                    for i, (start_byte, length, _) in enumerate(blocks, start=1):
                        end_byte = start_byte + length - 1
                        if end_byte == acked_byte:
                            confirmed_idx = i
                            break
                    # 如果找到这块且没确认过，说明是首次确认
                    if confirmed_idx and confirmed_idx not in acked_seq:
                        RTT = recv_time - send_times[confirmed_idx]  # 算 RTT
                        rtts.append(RTT)  # 保存 RTT
                        acked_seq.add(confirmed_idx)  # 标记已确认
                        s, l, _ = blocks[confirmed_idx - 1]
                        print(f"Received: ACK {ack_num} (bytes up to {ack_num -1}) RTT = {RTT*1000:.2f} ms")

                    # 如果当前确认块的下一个比 base 大，就滑动 base
                    if confirmed_idx and confirmed_idx + 1 > base:
                        base = confirmed_idx + 1  # 更新 base

        except:
            continue  # 有异常就忽略继续收包

# 启动收 ACK 线程
ack_thread = threading.Thread(target=recv_ack)
ack_thread.start()

# === 4. 主循环：GBN 发送窗口 & 超时重传 ===
while base <= total_packets:  # 只要还有块没被累计确认，就持续循环

    # === 动态计算超时重传时间 ===
    if rtts:  # 如果已经有 RTT 样本
        avg_rtt = sum(rtts) / len(rtts)  # 计算平均 RTT
        timeout = avg_rtt * 5  # 动态超时时间 = 平均 RTT × 5（经验值）
        if timeout < 0.05:
            timeout = 0.05  # 设置一个最小超时阈值
    else:#未收到ACK
        timeout = DEFAULT_TIMEOUT  # 如果没有 RTT 样本，就用默认值

    with lock:  # base / next_seq_idx / acked_seq
        curr_window_bytes = 0  # 当前窗口累计占用的字节数（控制单轮最大发包量）

        # === 在窗口范围内尽可能发送新块 ===
        while next_seq_idx < base + window_size and next_seq_idx <= total_packets:
            start_byte, length, payload = blocks[next_seq_idx - 1]  # 当前块的首字节、长度、内容

            if curr_window_bytes + length > 400:
                break  # 如果本轮加上这块就超出 400 字节限制，就暂停发，等待下轮

            # === 封装数据包头：DATA 包没有 flags（flags = 0） ===
            header = struct.pack(
                HEADER_FORMAT,
                start_byte,  # seq: 当前块的起始字节偏移
                0,  # ack: DATA 包不带确认号
                0,  # flags: DATA
                length,  # len: 这块的 payload 长度
                int(time.time() * 1000)  # timestamp: 当前毫秒时间戳
            )

            # === 发送 DATA ===
            client.sendto(header + payload, (server_ip, server_port))
            send_times[next_seq_idx] = time.time()  # 记录发送时间，用于后续 RTT 计算
            total_sent += 1  # 总发送次数 +1 （包含重传）

            print(f"Sent: DATA {next_seq_idx} (byte {start_byte}~{start_byte + length - 1})")

            curr_window_bytes += length  # 已用窗口字节累加
            next_seq_idx += 1  # 块序号 +1，准备发下一块

    time.sleep(timeout)  # 等待一轮超时，准备检查是否需要重发

    # === 检查是否存在超时未确认的数据块 ===
    earliest_timeout_idx = None  # 用来记录最早发生超时的块
    curr_time = time.time()

    for idx in range(base, next_seq_idx):  # 在窗口范围内从 base 开始检查
        if idx in acked_seq:
            continue  # 已经确认的不检查

        send_time = send_times.get(idx)
        if not send_time:
            continue  # 前面的字节数超限break

        if curr_time - send_time > timeout:  # 如果超时
            earliest_timeout_idx = idx
            break  # 找到就退出，只找最早的一个

    # === 如果有超时：执行 GBN 回退重传 ===
    if earliest_timeout_idx:
        print(f"Detected timeout: earliest timeout idx = {earliest_timeout_idx}")
        next_seq_idx = earliest_timeout_idx  # 从最早超时块重新开始发

        with lock:  # 重新加锁保证一致性
            curr_window_bytes = 0  # 本轮重新计数
            while next_seq_idx < base + window_size and next_seq_idx <= total_packets:
                if next_seq_idx in acked_seq:
                    next_seq_idx += 1  # 如果这块已确认就跳过
                    continue

                start_byte, length, payload = blocks[next_seq_idx - 1]
                if curr_window_bytes + length > 400:
                    break  # 本轮累加超了，就等下一轮再发

                # === 重发该块 ===
                header = struct.pack(
                    HEADER_FORMAT,
                    start_byte,
                    0,
                    0,
                    length,
                    int(time.time() * 1000)
                )
                client.sendto(header + payload, (server_ip, server_port))
                send_times[next_seq_idx] = time.time()  # 更新该块的新发送时间
                total_sent += 1  # 总发送次数 +1

                print(f"Resent: DATA {next_seq_idx} (byte {start_byte}~{start_byte + length - 1})")

                curr_window_bytes += length  # 本轮已用窗口字节数累加
                next_seq_idx += 1  # 块序号递增

# === 5. 四次挥手 ===
# 主动发起 FIN，告诉服务端我要关闭连接
fin_pkt = struct.pack(
    HEADER_FORMAT,
    0,                        # seq，此处用不到
    0,                        # ack，此处用不到
    FLAG_FIN,                 # 设置 FIN 标志位
    0,                        # 数据长度 0
    int(time.time() * 1000)   # 当前时间戳（毫秒）
)
client.sendto(fin_pkt, (server_ip, server_port))
print("Sent: FIN")  # 输出提示：FIN 已发出

# === 等服务端回 FIN-ACK ===
while True:
    data, _ = client.recvfrom(1024)  # 阻塞收包
    seq, ack_num, flags, pkt_len, ts = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    # 如果收到的包同时带 ACK 和 FIN 标志，说明服务端确认关闭
    if flags & FLAG_ACK and flags & FLAG_FIN:
        print("Received: FIN-ACK")
        break

# === 等服务端最后发 FIN ===
# 模拟 TCP 中最后一次 FIN 的对等交换
while True:
    data, _ = client.recvfrom(1024)  # 继续收包
    seq, ack_num, flags, pkt_len, ts = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    # 如果收到服务端再次发的 FIN，表示服务端也要完全关闭
    if flags & FLAG_FIN:
        print("Received: FIN")
        # 发最后一个 ACK，表示自己确认服务端的 FIN
        ack_pkt = struct.pack(
            HEADER_FORMAT,
            0, 0,              # seq, ack 不用带实际值
            FLAG_ACK,          # ACK 标志位
            0,                 # 数据长度 0
            int(time.time() * 1000)
        )
        client.sendto(ack_pkt, (server_ip, server_port))
        print("Sent: Last ACK")
        break

# === 停止收 ACK 线程 ===
running = False         # 设置控制变量为 False，结束 while True
ack_thread.join()       # 等收 ACK 线程退出

# === 6. 汇总统计 ===
# 计算丢包率：预期块数 / 实际总发块数
loss_rate = (1 - (total_packets / total_sent)) * 100

# 把所有 RTT 换成毫秒，用 pandas 做描述性统计
rtt_series = pd.Series([r * 1000 for r in rtts])

print("\n=== 汇总 ===")
print(f"丢包率: {loss_rate:.2f}%")             # 输出丢包率
print(f"RTT Max: {rtt_series.max():.2f} ms")   # 最大 RTT
print(f"RTT Min: {rtt_series.min():.2f} ms")   # 最小 RTT
print(f"RTT Avg: {rtt_series.mean():.2f} ms")  # 平均 RTT
print(f"RTT Std: {rtt_series.std():.2f} ms")   # RTT 标准差

# === 关闭 socket ===
client.close()
