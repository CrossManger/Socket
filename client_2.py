import socket  # Thư viện để làm việc với các kết nối mạng
import signal  # Thư viện để xử lý tín hiệu từ hệ điều hành
import sys     # Thư viện hệ thống để thoát khỏi chương trình và xử lý đầu vào/đầu ra
import os      # Thư viện để làm việc với hệ thống tập tin
import time    # Thư viện để quản lý thời gian và độ trễ
from threading import Thread, Lock  # Thư viện để quản lý đa luồng và khóa đồng bộ
from queue import PriorityQueue     # Thư viện để quản lý hàng đợi ưu tiên

# Các hằng số thiết lập chung
FORMAT = "utf-8"  # Định dạng mã hóa dữ liệu
CHUNK_SIZE = 1024  # Kích thước của mỗi phần dữ liệu nhận/gửi
PRIORITY = {"CRITICAL": 10, "HIGH": 4, "NORMAL": 1}  # Định nghĩa mức độ ưu tiên của các file

# Các biến toàn cục
client = None  # Biến toàn cục để lưu kết nối client
processed_files = set()  # Tập hợp các tệp đã được xử lý
queue = PriorityQueue()  # Hàng đợi ưu tiên để quản lý các nhiệm vụ tải xuống
lock = Lock()  # Khóa đồng bộ để tránh xung đột trong đa luồng
progress_lines = {}  # Lưu trữ vị trí dòng để cập nhật tiến trình tải xuống
shutdown_flag = False  # Cờ để theo dõi trạng thái tắt máy

# Hàm xử lý tín hiệu ngắt từ bàn phím (Ctrl+C)
def signal_handler(sig, frame):
    global shutdown_flag
    shutdown_flag = True  # Đặt cờ tắt máy
    if client:
        client.sendall("x".encode(FORMAT))  # Gửi tín hiệu tắt tới server
        client.close()  # Đóng kết nối client
    sys.exit(0)  # Thoát chương trình

# Hàm nhận từng phần của tệp từ server
def receive_chunk(client, output_file, offset, filesize):
    try: 
        data_Receive = filesize - offset  # Tính toán kích thước dữ liệu cần nhận
        if data_Receive > CHUNK_SIZE:
            data = client.recv(CHUNK_SIZE)  # Nhận một phần dữ liệu với kích thước cố định
        else: 
            data = client.recv(data_Receive)  # Nhận phần còn lại của tệp
        if not data:
            return False  # Trả về False nếu không nhận được dữ liệu
        with open(output_file, "ab") as file:
            file.write(data)  # Ghi dữ liệu nhận được vào tệp
        return len(data)  # Trả về kích thước dữ liệu đã nhận
    except Exception as e:
        print(f"Error receiving chunk of file {output_file}: {e}")
        return False  # Trả về False nếu có lỗi xảy ra

# Lớp đại diện cho một nhiệm vụ tải xuống tệp
class DownloadTask:
    def __init__(self, priority, filename, filesize):
        self.priority = priority  # Độ ưu tiên của nhiệm vụ
        self.filename = filename  # Tên tệp cần tải xuống
        self.filesize = filesize  # Kích thước của tệp
        self.offset = 0  # Vị trí bắt đầu tải xuống
        self.lock = Lock()  # Khóa đồng bộ cho nhiệm vụ này

    # Hàm tải xuống một phần của tệp
    def download_chunk(self, client):
        output_file = f"Client_path/{self.filename}"  # Đường dẫn đến tệp cần lưu

        try:
            with self.lock:
                client.sendall(f"GET {self.filename} {self.offset}".encode(FORMAT))  # Gửi yêu cầu lấy phần dữ liệu từ server
                if self.offset < self.filesize:
                    received_size = receive_chunk(client, output_file, self.offset, self.filesize)  # Nhận và lưu phần dữ liệu
                    self.offset += received_size  # Cập nhật vị trí tải xuống tiếp theo
                    return received_size  # Trả về kích thước phần dữ liệu nhận được
        except Exception as e:
            print(f"Error receiving chunk of file {self.filename}: {e}")
        return 0  # Trả về 0 nếu có lỗi xảy ra

    def __lt__(self, other):
        return self.priority > other.priority  # So sánh độ ưu tiên, để sử dụng với PriorityQueue

# Hàm lấy kích thước tệp từ tệp văn bản lưu trữ
def get_file_size_from_text(filename):
    try:
        with open("text.txt", "r") as file:
            lines = file.readlines()  # Đọc toàn bộ các dòng từ tệp văn bản
            for line in lines:
                parts = line.strip().split()  # Tách dòng thành các phần
                if len(parts) == 2 and parts[0] == filename:
                    return int(parts[1])  # Trả về kích thước tệp nếu tìm thấy
    except FileNotFoundError:
        print("text.txt not found")
    except ValueError:
        print(f"Invalid file size in text.txt for {filename}")
    return None  # Trả về None nếu không tìm thấy hoặc có lỗi

# Hàm xử lý các file client cần tải xuống
def client_processing():
    global processed_files, queue
    while not shutdown_flag:
        try:
            with open("input.txt", "r") as file:
                lines = file.readlines()  # Đọc toàn bộ các dòng từ tệp input.txt
                new_files = set()  # Tập hợp các tệp mới cần xử lý
                for line in lines:
                    parts = line.strip().split()  # Tách dòng thành các phần
                    if len(parts) != 2:
                        continue  # Bỏ qua nếu dòng không hợp lệ
                    filename, priority = parts
                    if filename not in processed_files:
                        processed_files.add(filename)  # Thêm tệp vào danh sách đã xử lý
                        filesize = get_file_size_from_text(filename)  # Lấy kích thước tệp
                        if filesize is None:
                            client.sendall(f"SIZE {filename}".encode(FORMAT))  # Gửi yêu cầu lấy kích thước tệp tới server
                            try:
                                response = client.recv(CHUNK_SIZE).decode(FORMAT).strip()  # Nhận phản hồi từ server
                                filesize = int(response)  # Chuyển đổi kích thước tệp nhận được thành số nguyên
                                with open("text.txt", "a") as text_file:
                                    text_file.write(f"{filename} {filesize}\n")  # Lưu kích thước tệp vào text.txt
                            except ValueError:
                                print(f"Error: Invalid file size for {filename} - Received: {response}")
                                continue
                        task = DownloadTask(PRIORITY[priority], filename, filesize)  # Tạo nhiệm vụ tải xuống mới
                        queue.put(task)  # Đưa nhiệm vụ vào hàng đợi ưu tiên
                        new_files.add(filename)
                        # CRITICAL - HIGH - NORMAL
        except FileNotFoundError:
            print("input.txt not found")  # Báo lỗi nếu không tìm thấy tệp input.txt
        
        time.sleep(2)  # Đợi một khoảng thời gian trước khi tiếp tục xử lý

# Hàm tải xuống các tệp từ server
def download_files(client):
    tasks = []
    while not shutdown_flag:
        try:
            while not queue.empty():
                task = queue.get()  # Lấy nhiệm vụ từ hàng đợi ưu tiên
                tasks.append(task)  # Thêm nhiệm vụ vào danh sách nhiệm vụ
                queue.task_done()  # Đánh dấu nhiệm vụ đã được xử lý

            threads = []
            for task in tasks:
                if shutdown_flag:
                    break
                thread = Thread(target=task.download_chunk, args=(client,))  # Tạo luồng tải xuống cho mỗi nhiệm vụ
                thread.start()  # Bắt đầu luồng tải xuống
                threads.append(thread)  # Thêm luồng vào danh sách các luồng
                thread.join()  # Đợi luồng kết thúc
            # for thread in threads:
            #     thread.join()  # Đợi tất cả các luồng kết thúc (không cần thiết nếu đã dùng `join` ngay sau khi start)

            for task in tasks:
                progress = (task.offset / task.filesize) * 100  # Tính toán tiến trình tải xuống
                with lock:
                    line_index = progress_lines.get(task.filename, len(progress_lines) + 10)  # Lấy vị trí dòng cho tiến trình
                    progress_lines[task.filename] = line_index
                    sys.stdout.write(f"\033[{line_index}HDownloading {task.filename} progress: {progress:.3f}%")  # Cập nhật tiến trình tải xuống trên màn hình
                    sys.stdout.flush()  # Làm mới dòng lệnh để hiển thị ngay lập tức
                if task.offset == task.filesize:
                    sys.stdout.write(f"\033[{line_index}HDownload of {task.filename} complete\n\n\n\n\n\n\n\n\n")  # Thông báo tải xong tệp
                    sys.stdout.flush()  # Làm mới dòng lệnh
                    tasks.remove(task)  # Xóa nhiệm vụ đã hoàn thành

        except Exception as e:
            print(f"Error during download: {e}")  # Báo lỗi nếu xảy ra lỗi trong quá trình tải xuống

# Hàm chính khởi động chương trình
def main():
    os.system('cls')  # Xóa màn hình console
    global client
    signal.signal(signal.SIGINT, signal_handler)  # Đăng ký xử lý tín hiệu ngắt

    HOST = input("Server IP: ")  # Nhập địa chỉ IP của server
    PORT = 12345  # Đặt cổng kết nối
    ADDR = (HOST, PORT)

    if not os.path.exists("Client_path"):
        os.makedirs("Client_path")  # Tạo thư mục lưu trữ tệp nếu chưa tồn tại

    print("CLIENT SIDE")

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Tạo socket kết nối TCP

    try:
        client.connect(ADDR)  # Kết nối tới server
        print(f"Connected to server at: {ADDR}")
        print("Client address:", client.getsockname())  # In địa chỉ của client
        filename_str = client.recv(CHUNK_SIZE).decode(FORMAT)  # Nhận danh sách tệp có sẵn từ server
        filenames = filename_str.split("\n")  # Tách danh sách tệp thành các tên riêng biệt
        print("Files available for download:", filenames)
        
        thread = Thread(target=client_processing)  # Tạo luồng xử lý các tệp cần tải xuống
        thread.start()  # Bắt đầu luồng xử lý

        download_files(client)  # Bắt đầu tải xuống các tệp
    except Exception as e:
        print("Error:", str(e))  # Báo lỗi nếu xảy ra lỗi khi kết nối hoặc xử lý
    finally:
        client.close()  # Đóng kết nối client
        print("Client connection closed")  # Thông báo đóng kết nối

# Khởi động chương trình
if __name__ == "__main__":
    main()
