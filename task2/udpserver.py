import socket
import struct
import random
import time

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("", 9999))

print("UDP Server listening on port 9999...")

expected_seq = 1

while True:
    data, addr = server.recvfrom(4096)
    seq, pkt_type, flags, pkt_len = struct.unpack('!I B B H', data[:8])

    if pkt_type == 1:
        ack_pkt = struct.pack('!I B B H', 0, 2, 0, 0)
        server.sendto(ack_pkt, addr)
        print("Handshake OK.")
        continue

    if pkt_type == 3:
        print(f"Received: DATA {seq}, Len={pkt_len}")

        if random.random() < 0.2:
            print(f"Simulated packet loss for DATA {seq}")
            continue

        if seq == expected_seq:
            expected_seq += 1

        now = time.localtime()
        ack_pkt = struct.pack('!I B B H H H H', expected_seq - 1, 4, 0, 0, now.tm_hour, now.tm_min, now.tm_sec)
        server.sendto(ack_pkt, addr)
        print(f"Sent: ACK {expected_seq - 1}")
