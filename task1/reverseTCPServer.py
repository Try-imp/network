import socket
import struct
import threading

HOST = '0.0.0.0'
PORT = 12345

def handle_client(conn, addr):
    print(f"Connected by {addr}")

    try:
        # === 收 Initialization ===
        data = conn.recv(6)  # 2 bytes Type + 4 bytes Block num
        msg_type, block_num = struct.unpack('!HI', data)
        print(f"Received Initialization: Type={msg_type}, Block num={block_num}")

        # 回复 agree
        conn.sendall(struct.pack('!H', 2))
        print("Sent agree: Type=2")

        # === 循环收每块 ===
        for idx in range(block_num):
            # 收 Type
            recv_type = struct.unpack('!H', conn.recv(2))[0]

            # 收 Length
            recv_len = struct.unpack('!I', conn.recv(4))[0]

            # 收 Data
            chunk = b''
            while len(chunk) < recv_len:
                chunk += conn.recv(recv_len - len(chunk))

            print(f"Received reverseRequest: Type={recv_type}, Length={recv_len}")
            print(f"Original chunk: {chunk.decode('utf-8', errors='ignore')}")

            # Reverse
            reversed_chunk = chunk[::-1]
            print(f"Reversed chunk: {reversed_chunk.decode('utf-8', errors='ignore')}")

            # 发送 reverseAnswer
            conn.sendall(struct.pack('!H', 4))
            conn.sendall(struct.pack('!I', len(reversed_chunk)))
            conn.sendall(reversed_chunk)

            print(f"Sent reverseAnswer {idx+1}")

    except Exception as e:
        print(f"Error handling client {addr}: {e}")

    finally:
        conn.close()
        print(f"Connection with {addr} closed.")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            # === 新起线程处理 ===
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.start()

if __name__ == '__main__':
    main()
