import socket
import os

FORMAT = "utf-8"

def send_file_list(conn: socket.socket, filename: str):
    file_list = []
    with open(filename, "r") as file:
        for line in file:
            filename = line.strip()
            a = filename.split()
            b, d = map(str, a)
            file_list.append(b)
        filename_STR = "\n".join(file_list)
        conn.sendall(filename_STR.encode(FORMAT))

def send_file(filename, conn):
    try:
        filesize = os.path.getsize(filename)
        conn.sendall(str(filesize).encode(FORMAT))
        conn.recv(1024)  

        with open(filename, 'rb') as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                conn.sendall(data)
    except Exception as e:
        print(f"Error sending file {filename}: {e}")

def handle_client(conn , addr):
    try:
        print(f"Connected to {addr}")
        send_file_list(conn, "text.txt")
        s = None
        while (s != "x"):
            s = conn.recv(1024).decode(FORMAT)
            if s != "x":
                print(f"Received from {addr}: {s}")
            else:
                print("Ctrl-C pressed")
            if (s != "x" and s != ""):
                send_file(s, conn)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()
        print(f"Connection with {addr} closed.")

def main():
    HOST = socket.gethostbyname(socket.gethostname())
    PORT = 55555
    
    ADDR = (HOST, PORT)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen(5)
    print(f"Server listening on {HOST}:{PORT}")

    nClient = 0
    while nClient < 5:
        try:
            conn, addr = server.accept()
            handle_client(conn, addr)
            nClient += 1
        except Exception as e:
            print(f"Error accepting connection: {e}")

if __name__ == "__main__":
    main()
