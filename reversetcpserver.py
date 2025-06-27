import socket       # 网络通信相关
import struct       # 二进制数据打包/解包
import threading    # 多线程处理每个客户端
import sys          # 处理命令行参数

# 精确读取n字节数据，TCP 是流式协议，recv() 可能读不满要的字节，所以要循环读。
def recv_exact(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))# 每次尽可能多地读，直到够 n 字节
        if not packet:
            raise RuntimeError("Socket connection broken")
        data += packet
    return data

# 处理一个客户端连接
def handle_client(conn):
    try:
        # 接收初始化报文 (6字节: 2字节类型+4字节块数)
        init_header = recv_exact(conn, 6)
        # 前 2 字节 init_type：类型码（这里要是 1）
        # 后 4 字节 num_blocks：数据块数量（客户端要发送的块数）
        # >HI：表示用大端字节序(>) 解包，分别是：
        # H → unsigned short（2字节）
        # I → unsigned int（4字节）
        init_type, num_blocks = struct.unpack('>HI', init_header)
        # 校验类型（类型码必须是1，代表初始化报文）
        if init_type != 1:
            print(f"Invalid initialization type: {init_type}")
            return

        # 发送同意报文 (Type=2, 2字节)
        # 发送类型为 2 的回应报文，表示“收到初始化”。
        conn.sendall(struct.pack('>H', 2))
        # 循环处理每个请求块
        for _ in range(num_blocks):
            # 接收请求头 (6字节: 2字节类型+4字节长度)
            req_header = recv_exact(conn, 6)
            req_type, data_len = struct.unpack('>HI', req_header)
            # req_type 应该是 3：表示“请求数据反转”
            if req_type != 3:
                print(f"Invalid request type: {req_type}")
                break
            # 读取原始数据
            # data_len：后续数据的长度（单位字节）
            data = recv_exact(conn, data_len)
            # 进行反转
            reversed_data = data[::-1] # 字节反转

            # 发送反转结果 (Type=4)
            ans_header = struct.pack('>HI', 4, len(reversed_data)) # 响应头：4 + 数据长度
            conn.sendall(ans_header) # 首先发响应头
            conn.sendall(reversed_data) # 然后发反转后的内容

    # 出错和关闭
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        conn.close()

# 主程序入口
def main():
    #参数检查，从命令行获取端口号：例如：python server.py 8888
    if len(sys.argv) != 2:
        print("Usage: reversetcpserver.py <port>")
        sys.exit(1)

    port = int(sys.argv[1]) # 端口号设置
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # 创建 TCP 服务器 socket：ipv4,tcp协议
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 设置地址重用：，防止端口占用报错
    server_socket.bind(('0.0.0.0', port)) # 绑定端口,绑定到本地ip地址
    server_socket.listen(5) # 开始监听（此处设置为最多5个客户端线程）
    print(f"Server listening on port {port}")

    try:
        # 循环接受连接并创建线程：
        while True:
            conn, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")
            # 每个连接开一个线程，调用 handle_client(conn)
            client_thread = threading.Thread(
                target=handle_client,# 线程执行的函数
                args=(conn,),# 传递给 handle_client 函数的参数（必须是元组）
                daemon=True# 设置为守护线程（主线程结束时，这个子线程会自动退出）
            )
            client_thread.start()
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()