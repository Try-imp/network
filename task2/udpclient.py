import socket
import struct
import sys
import random
import time

# === 参数解析 ===
server_ip = sys.argv[1]
server_port = int(sys.argv[2])
total_packets = int(sys.argv[3])

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# === 握手 ===
# 新首部：Seq(4B) | Type(1B) | Flags(1B) | Len(2B)
handshake_pkt = struct.pack('!I B B H', 0, 1, 0, 0)
client.sendto(handshake_pkt, (server_ip, server_port))
print("Sent: Handshake packet")

data, _ = client.recvfrom(1024)
seq, pkt_type, flags, pkt_len = struct.unpack('!I B B H', data[:8])
if pkt_type != 2:
    print("Handshake failed")
    sys.exit(1)
print("Received: Handshake ACK")

# === 发送窗口参数 ===
window_size = 5
base = 1
next_seq = 1

blocks = []
blocks_bytes = []
start = 1
for _ in range(total_packets):
    payload_len = random.randint(40, 80)
    payload = bytes([random.randint(65, 90) for _ in range(payload_len)])
    blocks.append(payload)
    end = start + payload_len - 1
    blocks_bytes.append((start, end))
    start = end + 1

send_times = {}
rtts = []
acked_seq = set()   # ✅ 新增：记录收到 ACK 的唯一序号

DEFAULT_TIMEOUT = 0.3

# === GBN 主循环 ===
while base <= total_packets:
    # 动态超时计算
    if rtts:
        avg_rtt = sum(rtts) / len(rtts)
        timeout = avg_rtt * 5
        if timeout < 0.05:
            timeout = 0.05
    else:
        timeout = DEFAULT_TIMEOUT
    client.settimeout(timeout)

    # 发送窗口内数据块
    while next_seq < base + window_size and next_seq <= total_packets:
        payload = blocks[next_seq - 1]
        header = struct.pack('!I B B H', next_seq, 3, 0, len(payload))
        client.sendto(header + payload, (server_ip, server_port))
        send_times[next_seq] = time.time()

        start_byte, end_byte = blocks_bytes[next_seq - 1]
        print(f"Sent: DATA {next_seq} （第 {start_byte}~{end_byte} 字节）")

        next_seq += 1

    try:
        data, _ = client.recvfrom(1024)
        recv_time = time.time()
        seq, pkt_type, flags, _, hh, mm, ss = struct.unpack('!I B B H H H H', data)

        if pkt_type == 4:
            RTT = recv_time - send_times[seq]
            rtts.append(RTT)

            acked_seq.add(seq)  # ✅ 新增：去重记录

            start_byte, end_byte = blocks_bytes[seq - 1]
            print(f"Received: ACK {seq} （第 {start_byte}~{end_byte} 字节）RTT = {RTT*1000:.2f} ms, ServerTime: {hh:02}:{mm:02}:{ss:02}")

            base = seq + 1

    except socket.timeout:
        print(f"Timeout, retransmitting window [{base} ~ {next_seq - 1}]")
        for seq in range(base, next_seq):
            payload = blocks[seq - 1]
            header = struct.pack('!I B B H', seq, 3, 0, len(payload))
            client.sendto(header + payload, (server_ip, server_port))
            send_times[seq] = time.time()

            start_byte, end_byte = blocks_bytes[seq - 1]
            print(f"重传第 {seq} 个 （第 {start_byte}~{end_byte} 字节）")

# === 统计汇总 ===
loss_rate = (total_packets - len(acked_seq)) / total_packets
print("\n=== 传输完成 ===")
print(f"丢包率: {loss_rate*100:.2f}%")
print(f"RTT max: {max(rtts)*1000:.2f} ms")
print(f"RTT min: {min(rtts)*1000:.2f} ms")
print(f"RTT avg: {sum(rtts)/len(rtts)*1000:.2f} ms")
print(f"RTT std: {((sum([(r - sum(rtts)/len(rtts))**2 for r in rtts])/len(rtts))**0.5)*1000:.2f} ms")

client.close()
