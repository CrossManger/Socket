import socket
import signal
import sys
import os

FORMAT = "utf-8"
processed_files = set()

client = None 

def signal_handler(sig, frame):
    print("")
    print("Ctrl+C pressed")
    if client:
        client.sendall("x".encode(FORMAT))
        client.close()
    sys.exit(0)

def receive_file(client, output_file, filename):
    try:
        filesize = int(client.recv(1024).decode(FORMAT))
        client.sendall(b'READY')  
        
        with open(output_file, "wb") as file:
            received_data = 0
            print(f"Downloading {filename} progress: 0.000 %", end='\r')
            while received_data < filesize:
                data = client.recv(1024)
                if not data:
                    break
                file.write(data)
                received_data += len(data)
                progress = (received_data / filesize) * 100
                print(f"Downloading {filename} progress:", "%.3f"%progress, "%", end='\r')
            print(f"Downloading {filename} progress:", "%.3f"%progress, "%")
                
    except Exception as e:
        print(f"Error receiving file {output_file}: {e}")

def client_processing(client: socket.socket):

    while True:
        with open("input.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                filename = line.strip()
                if filename not in processed_files:
                    processed_files.add(filename)
                    client.sendall(filename.encode(FORMAT))
                    receive_file(client,"Client_path/" + filename, filename)

def main():
    global client
    HOST = input("E: ")
    if HOST == "" or not HOST:
        HOST = socket.gethostbyname(socket.gethostname())
    PORT = 55555
    ADDR = (HOST, PORT)

    print("CLIENT SIDE")

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    signal.signal(signal.SIGINT, signal_handler)
    client.connect(ADDR)
    
    try:
        print("Client address:", client.getsockname())
        filename_str = client.recv(1024).decode(FORMAT)
        filenames = filename_str.split("\n")
        print(filenames)
        client_processing(client)
    except Exception as e:
        print("Error:", str(e))
    finally:
        client.close()
        print("Client connection closed")

if __name__ == "__main__":
    folder_path = "Client_path"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    main()
    input()
