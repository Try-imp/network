import socket
import struct
import random
import time
import threading             # 用线程让 server 可停止

# ====== 协议头格式 ======
# 格式：seq(4字节) ack(4字节) flags(2字节) len(2字节) timestamp(8字节)
HEADER_FORMAT = '!I I H H Q'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# ====== 标志位 ======
FLAG_SYN = 0x01    # SYN 标志位
FLAG_ACK = 0x02    # ACK 标志位
FLAG_FIN = 0x04    # FIN 标志位

class UDPServer:
    def __init__(self, host, port, drop_rate=0.2):
        self.host = host
        self.port = port
        self.drop_rate = drop_rate             # 模拟丢包率
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建 UDP socket
        self.sock.bind((self.host, self.port)) # 绑定地址和端口
        self.expected_seq = 1                  # 期望的下一个字节序号（累计确认）
        self.running = True                    # 控制服务是否继续运行

    def pack_header(self, seq, ack, flags, data_len=0, timestamp=0):
        #封装协议头
        return struct.pack(HEADER_FORMAT, seq, ack, flags, data_len, timestamp)

    def unpack_header(self, data):
        #解析协议头
        return struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])

    def handle_connection(self):
        #主循环：处理握手、数据传输、四次挥手
        print(f"[Server] UDP Server started on {self.host}:{self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)  # 收数据
                if len(data) < HEADER_SIZE:#20，不合法
                    continue

                seq, ack_num, flags, data_len, ts = self.unpack_header(data)
                now_ts = int(time.time() * 1000)  # 当前时间戳（毫秒）

                # === 处理 SYN（握手第一步）===
                if flags & FLAG_SYN:
                    syn_ack = self.pack_header(
                        seq=0,
                        ack=self.expected_seq,
                        flags=FLAG_SYN | FLAG_ACK,
                        timestamp=now_ts
                    )
                    self.sock.sendto(syn_ack, addr)  # 回 SYN-ACK
                    print(f"[Server] Handshake OK. Sent SYN-ACK, ack={self.expected_seq}")

                # === 处理 FIN（挥手）===
                elif flags & FLAG_FIN:
                    # 回 FIN-ACK
                    fin_ack = self.pack_header(
                        seq=0,
                        ack=self.expected_seq,
                        flags=FLAG_ACK | FLAG_FIN,
                        timestamp=now_ts
                    )
                    self.sock.sendto(fin_ack, addr)
                    print(f"[Server] Sent FIN-ACK, ack={self.expected_seq}")

                    time.sleep(0.5)  # 等一下再发 FIN
                    fin_pkt = self.pack_header(
                        seq=0,
                        ack=self.expected_seq,
                        flags=FLAG_FIN,
                        timestamp=now_ts
                    )
                    self.sock.sendto(fin_pkt, addr)
                    print(f"[Server] Sent FIN, ack={self.expected_seq}")

                # === 处理数据包 ===
                else:
                    print(f"[Server] Received DATA seq={seq}, expected={self.expected_seq}, len={data_len}")

                    # === 丢包模拟 ===
                    if random.random() < self.drop_rate:
                        print(f"[Server] Simulated packet drop (seq={seq})")
                        continue  # 丢掉这个包，不回复 ACK

                    # === 正确顺序 ===
                    if seq == self.expected_seq:
                        self.expected_seq += data_len
                        print(f"[Server] In-order packet. Updated expected_seq={self.expected_seq}")
                    else:
                        print(f"[Server] Out-of-order! Expected {self.expected_seq} but got {seq}")

                    # 回复 ACK（累计确认或重复 ACK）
                    ack_pkt = self.pack_header(
                        seq=0,
                        ack=self.expected_seq,
                        flags=FLAG_ACK,
                        timestamp=now_ts
                    )
                    self.sock.sendto(ack_pkt, addr)
                    print(f"[Server] Sent ACK, ack={self.expected_seq}")

            except Exception as e:
                print(f"[Server] Error: {e}")  # 有异常直接输出

    def start(self):
        #启动服务端线程"""
        self.thread = threading.Thread(target=self.handle_connection)
        self.thread.start()

    def stop(self):
        #停止服务端"""
        self.running = False
        self.sock.close()
        self.thread.join()
        print("[Server] Stopped.")

# === 命令行执行入口 ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python udp_server.py <port> [drop_rate]")
        sys.exit(1)

    port = int(sys.argv[1])  # 端口
    drop_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2  # 丢包率（可选参数）

    server = UDPServer("0.0.0.0", port, drop_rate)
    server.start()

    try:
        while True:
            time.sleep(1)  # 主线程阻塞，保持服务端活着（挂起）
    except KeyboardInterrupt:
        server.stop()  # Ctrl+C 时关闭
