import socket      # 用于 TCP 网络通信
import struct      # 用于打包/解包二进制数据（网络协议用）
import random      # 生成随机块长度
import sys         # 读取命令行参数
import os          # 处理文件路径

# 发送所有数据,TCP 并不保证一次 send() 就发送完全部数据，因此要用循环确保发完整。
def send_all(sock, data):
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise RuntimeError("Socket connection broken")
        total_sent += sent

# 接收固定字节数
def recv_exact(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            raise RuntimeError("Socket connection broken")
        data += packet
    return data


def main():
    #读取命令行参数,确保参数数量正确，否则打印用法提示并退出。
    if len(sys.argv) != 6:
        print("Usage: client.py <server_ip> <server_port> <filename> <min_len> <max_len>")
        sys.exit(1)

    server_ip = sys.argv[1] # 读取ip
    server_port = int(sys.argv[2]) # 读取端口
    filename = sys.argv[3] # 要读的文件
    min_len = int(sys.argv[4]) # 最小块长度
    max_len = int(sys.argv[5]) # 最大块长度

    # 打开文件读取文件内容
    # 用 with open() 读取整个文件内容（文本），出错就报错退出。
    try:
        with open(filename, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # 生成随机分块
    # 将整个文本内容切分成长度 在 min_len 和 max_len 之间的随机块。
    blocks = []
    index = 0
    total_len = len(content)
    while index < total_len:
        if total_len - index < min_len:
            block_len = total_len - index
        else:
            block_len = random.randint(min_len, min(max_len, total_len - index))
        blocks.append(content[index:index + block_len])
        index += block_len
    num_blocks = len(blocks)

    # 创建TCP socket，开始建立连接
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((server_ip, server_port))
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit(1)

        # 发送初始化报文 (Type=1)
        # 发送 6 字节：1 是初始化类型（2 字节）num_blocks 是块数量（4 字节）
        # 用 struct.pack('>HI', ...) 制作报文。
        init_packet = struct.pack('>HI', 1, num_blocks)  # H:2字节无符号整数, I:4字节无符号整数
        send_all(s, init_packet)

        # 接收同意报文，等待服务器同意(Type=2, 2字节)
        agree_packet = recv_exact(s, 2)
        agree_type = struct.unpack('>H', agree_packet)[0]
        if agree_type != 2:
            print(f"Server responded with error: expected type 2, got {agree_type}")
            sys.exit(1)

        # 反向发送每一块数据
        # 倒序处理块（从最后一块到第一块）：
        reversed_blocks = []
        for i in range(num_blocks - 1, -1, -1):
            block = blocks[i]
            # 发送反转请求报文 (Type=3)
            header = struct.pack('>HI', 3, len(block))  # 2字节类型 + 4字节长度
            send_all(s, header)
            # 发送块数据，将当前块以 ASCII 编码发送。
            send_all(s, block.encode('ascii'))

            # 接收反转结果报文 (Type=4)
            ans_header = recv_exact(s, 6)  # 2字节类型 + 4字节长度
            ans_type, ans_len = struct.unpack('>HI', ans_header)
            if ans_type != 4:
                print(f"Invalid answer type received: expected 4, got {ans_type}")
                sys.exit(1)
            # 接收反转数据并保存
            reversed_data = recv_exact(s, ans_len).decode('ascii')

            # 打印并保存结果
            block_idx = num_blocks - i
            print(f"{block_idx}:{reversed_data}")
            reversed_blocks.append(reversed_data) # 反转结果打印并存入列表中。

        # 生成写入最终反转文件
        # os.path.splitext(filename)[0] 是原文件去掉扩展名
        # 拼成 "原名_reversed.txt" 文件
        # 把所有反转块拼起来写进去
        output_filename = os.path.splitext(filename)[0] + '_reversed.txt'
        with open(output_filename, 'w') as f:
            f.write(''.join(reversed_blocks))
        print(f"Final reversed file saved as {output_filename}")


if __name__ == "__main__":
    main()