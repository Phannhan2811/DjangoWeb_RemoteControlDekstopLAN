import socket
import cv2
import numpy as np
import struct
import lz4.frame
from pynput import keyboard
import time
import threading
import sys

client_socket = None
mouse_socket = None
keyboard_socket = None
window_name = "Remote Screen"

def get_server_ip():
    if len(sys.argv) > 1:
        return sys.argv[1]  # Lấy địa chỉ IP từ tham số dòng lệnh
    else:
        print("Usage: python client.py <server_ip>")
        sys.exit(1)


def on_press(key):
    try:
        # Ưu tiên phím thường
        if hasattr(key, 'char') and key.char:
            # Phím thường
            send_key_event(
                keyboard_socket, 
                event_type=1,  # 1 là press 
                key=key.char, 
                is_special=0
            )
        else:
            # Phím đặc biệt
            send_key_event(
                keyboard_socket, 
                event_type=1,  # 1 là press
                key=str(key), 
                is_special=1
            )
    except Exception as e:
        print(f"Lỗi xử lý phím: {e}")

def on_release(key):
    try:
        # Tương tự on_press nhưng thay đổi event_type
        if hasattr(key, 'char') and key.char:
            # Phím thường
            send_key_event(
                keyboard_socket, 
                event_type=2,  # 2 là release
                key=key.char, 
                is_special=0
            )
        else:
            # Phím đặc biệt
            send_key_event(
                keyboard_socket, 
                event_type=2,  # 2 là release
                key=str(key), 
                is_special=1
            )
    except Exception as e:
        print(f"Lỗi xử lý phím: {e}")

def send_key_event(socket, event_type, key, is_special):
    try:
        # Mã hóa key thành bytes
        key_bytes = key.encode('utf-8')
        
        # Định dạng gói tin:
        # 1 byte: Loại sự kiện (press/release)
        # 1 byte: Cờ phím đặc biệt
        # 1 byte: Độ dài key
        # Các byte còn lại: Nội dung key
        packet = struct.pack(
            '!BBB{}s'.format(len(key_bytes)),
            event_type,          # Loại sự kiện (1 byte)
            is_special,          # Cờ phím đặc biệt (1 byte) 
            len(key_bytes),      # Độ dài key (1 byte)
            key_bytes            # Nội dung key
        )
        
        # Gửi độ dài gói tin
        socket.send(struct.pack('!I', len(packet)))
        
        # Gửi gói tin
        socket.send(packet)
        
        print(f"Đã gửi: {key} (Loại: {event_type})")
    
    except Exception as e:
        print(f"Lỗi gửi sự kiện: {e}")
    
listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release
)

def run_client():
    global client_socket
    global mouse_socket
    global keyboard_socket
    host = get_server_ip()
    screen_port = 9999
    mouse_port = 5656
    keyboard_port = 6767
   

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, screen_port))

    # Kết nối đến server cho luồng sự kiện chuột
    mouse_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mouse_socket.connect((host, mouse_port))

    keyboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    keyboard_socket.connect((host, keyboard_port))

    try:
        # Đặt callback sự kiện chuột cho cửa sổ OpenCV
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, on_mouse_event)
        listener.start()

        receive_screen_stream(client_socket)
        listener.join()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        listener.stop()
        client_socket.close()
        mouse_socket.close()
        keyboard_socket.close()

# Gửi sự kiện chuột đến server
def send_mouse_event(mouse_socket, x, y, event_type):
    # event_type: 0 = click, 1 = move
    data = struct.pack("IIH", x, y, event_type)
    mouse_socket.sendall(data)

# Callback xử lý sự kiện chuột từ OpenCV
def on_mouse_event(event, x, y, flags, param):
    global last_x, last_y
    
    if event == cv2.EVENT_MOUSEMOVE:  # Di chuyển chuột
        send_mouse_event(mouse_socket, x, y, 1)
    elif event == cv2.EVENT_LBUTTONDOWN:  # Nhấn chuột trái
        send_mouse_event(mouse_socket, x, y, 0)
    elif event == cv2.EVENT_RBUTTONDOWN:  # Nhấn chuột phải
        send_mouse_event(mouse_socket, x, y, 2)  # 2 có thể là mã sự kiện cho chuột phải
    elif event == cv2.EVENT_MOUSEWHEEL:  # Sự kiện cuộn chuột
        if flags > 0:
            send_mouse_event(mouse_socket, x, y, 3)  # 3 có thể là mã sự kiện cho cuộn chuột lên
        else:
            send_mouse_event(mouse_socket, x, y, 4)

def receive_screen_stream(client_socket):
    global mouse_socket
    global keyboard
    data = b""
    payload_size = struct.calcsize("Q")  # Use 'Q' for unsigned long long (matching server)
    cv2.namedWindow(window_name, flags=cv2.WINDOW_KEEPRATIO)

    while True:
        # Receive the image size
        while len(data) < payload_size:
            data += client_socket.recv(4096)

        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("Q", packed_msg_size)[0]  # Unpack the message size

        # Receive the image data
        while len(data) < msg_size:
            data += client_socket.recv(65536)

        frame_data = data[:msg_size]
        data = data[msg_size:]

        # Decode the image and display
        frame_data = lz4.frame.decompress(frame_data)
        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR) 
        
        if frame is not None:
            cv2.imshow(window_name, frame)
        else:
            print("frame is None")

        

        # Exit on 'q' key press
        if cv2.waitKey(1) and cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            print("Exiting...")
            listener.stop()
            client_socket.close()
            mouse_socket.close()
            keyboard_socket.close()
            cv2.destroyAllWindows()
            break


if __name__ == "__main__":
    run_client()