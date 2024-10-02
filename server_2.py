import socket
import threading
import os
import signal
import sys
import time  # Import thư viện time

FORMAT = "utf-8"
clients = []  # List to store current client connections
shutdown_flag = False
CHUNK_SIZE = 1024

def send_file_list(conn): #gửi những file có thể tải về
    try: 
        file_list = os.listdir("server_files") #liệt kê các tên trong file rồi thêm vào file_list
        file_list_str = "\n".join(file_list)  #thêm các tên file của file_list thành 1 chuỗi duy nhất cách nhau bởi ký tự xuống dòng
        conn.sendall(file_list_str.encode(FORMAT)) #gửi hết file sang
    except Exception as e:
        print(f"Error sending file list: {e}")

def send_chunk(filename, offset, conn):
    try:
        with open(f"server_files/{filename}", 'rb') as file: # tên file cần gửi
            file.seek(offset) #vị trí hiện tại 
            data = file.read(CHUNK_SIZE) # đọc 1 chunk dữ liệu
            if data:
                conn.sendall(data)  #gửi dữ liệu vừa đọc
            else:
                conn.sendall(b'')  # Send an empty message to indicate EOF
    except Exception as e:
        print(f"Error sending chunk of file {filename}: {e}")

def handle_client(conn, addr): #quản lý phiên làm việc giữa client và server
    global clients, shutdown_flag
    try:
        print(f"Connected to {addr}") 
        send_file_list(conn) 
        while not shutdown_flag:
            try:
                data = conn.recv(1024).decode(FORMAT).strip() 
                if not data:
                    break
                #print(f"Received command: {data}")

                # chia lệnh
                commands = data.splitlines() 
                for command in commands:
                    if command == "x":
                        print("Ctrl-C pressed by client")
                        break
                    
                    
                    if command.startswith("SIZE"): 
                        parts = command.split()
                        if len(parts) == 2:
                            filename = parts[1]
                            #kiểm tra file có tồn tại không
                            if os.path.exists(f"server_files/{filename}"):
                                filesize = os.path.getsize(f"server_files/{filename}")
                                conn.sendall(str(filesize).encode(FORMAT))
                            else:
                                conn.sendall(b"File not found")
                        else:
                            conn.sendall(b"Invalid command")

                    elif command.startswith("GET"): 
                        parts = command.split()
                        if len(parts) == 3:
                            _, filename, offset = parts
                            try:
                                offset = int(offset)
                                #nếu tồn tại cái file cần tải trong server_files
                                if os.path.exists(f"server_files/{filename}"):
                                    filesize = os.path.getsize(f"server_files/{filename}")
                                    if offset < filesize: #nếu kích thước yêu cầu hợp lệ thì gửi chunk
                                        send_chunk(filename, offset, conn) 
                                else:
                                    conn.sendall(b"File not found")
                            except ValueError:
                                conn.sendall(b"Invalid request")
                        else:
                            conn.sendall(b"Invalid command")
                    else:
                        conn.sendall(b"Invalid command")
            except Exception as e:
                print(f"Error processing command: {e}")
                conn.sendall(b"Error processing command")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()
        if conn in clients:
            clients.remove(conn)
        print(f"Connection with {addr} closed.")

def main():
    global server

    HOST = socket.gethostbyname(socket.gethostname())
    PORT = 12345
    ADDR = (HOST, PORT)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(ADDR)
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while not shutdown_flag:
        try:
            conn, addr = server.accept()
            clients.append(conn)
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = False
            client_thread.start()
        except Exception as e:
            if not shutdown_flag:
                print(f"Error accepting connection: {e}")

if __name__ == "__main__":
    main()
