import socket
import mss
import cv2
import numpy as np
import enum
from pynput import keyboard
import struct
import lz4.frame
import threading
import pyautogui
import math

screen_width, screen_height = pyautogui.size()
pyautogui.PAUSE = 0
keyboard_controller = keyboard.Controller()
stop_event = threading.Event()

def get_scaled_screen_size():
    base_width = 1280
    scaled_height = int(screen_height / screen_width * base_width)
    return (base_width, scaled_height)

def run_server():
    host = "0.0.0.0"
    screen_port = 9999
    mouse_port = 5656
    keyboard_port = 6767

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, screen_port))
    server_socket.listen(1)

    # Tạo socket cho luồng sự kiện chuột
    mouse_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mouse_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    mouse_socket.bind((host, mouse_port))
    mouse_socket.listen(1)

    # Tạo socket cho luồng sự kiện bàn phím
    keyboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    keyboard_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    keyboard_socket.bind((host, keyboard_port))
    keyboard_socket.listen(1)

    print(f"Server is listening on {host}:{screen_port}...")

    # Accept client connection
    client_socket, client_address = server_socket.accept()
    print(f"Screen connection from {client_address} established.")
    mouse_socket, mouse_address = mouse_socket.accept()
    print(f"Mouse connection from {mouse_address} established.")
    keyboard_socket, keyboard_address = keyboard_socket.accept()
    print(f"Keyboard connection from {keyboard_address} established.")

    try:
        mouse_thread = threading.Thread(target=handle_mouse_event, args=(mouse_socket,))
        mouse_thread.daemon = True  # Đảm bảo thread kết thúc khi chương trình dừng
        mouse_thread.start()

        keyboard_thread = threading.Thread(target=handle_keyboard_event, args=(keyboard_socket,))
        keyboard_thread.daemon = True
        keyboard_thread.start()

        screen_stream(client_socket)

        mouse_thread.join()
        keyboard_thread.join()

    except Exception as e:
        print(f"Error: {e}")

    finally:
        stop_event.set()
        client_socket.close()
        server_socket.close()
        mouse_socket.close()
        keyboard_socket.close()
        print("Server stopped.")

def screen_stream(client_socket):
    scaled_width, scaled_height = get_scaled_screen_size()
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Choose the full screen
        while True:
            try:
                # Capture the screen
                img = np.array(sct.grab(monitor))[:, :, :3]
                img = cv2.resize(img, (scaled_width, scaled_height))
                _, buffer = cv2.imencode('.jpeg', img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                data = lz4.frame.compress(buffer.tobytes())
                client_socket.sendall(struct.pack("Q", len(data)) + data)

            except Exception as e:
                print(f"Error during image transmission: {e}")
                stop_event.set()
                break


def handle_mouse_event(mouse_socket):
    scaled_width, scaled_height = get_scaled_screen_size()
    print((scaled_width, scaled_height))
    while not stop_event.isSet():
        try:
            # Nhận dữ liệu sự kiện chuột
            data = mouse_socket.recv(10)  # 10 bytes: 4 (x) + 4 (y) + 2 (event_type)
            if len(data) < 10:
                print("Incomplete mouse event data received.")
                break

            # Giải mã dữ liệu
            x, y, event_type = struct.unpack("IIH", data)

            # Xử lý sự kiện chuột
            if event_type == 1:  # Di chuyển chuột
                pyautogui.moveTo(x / scaled_width * screen_width, y / scaled_height * screen_height, duration=0)
            elif event_type == 0:  # Nhấn chuột trái
                pyautogui.click(x / scaled_width * screen_width, y / scaled_height * screen_height, duration=0)
            elif event_type == 2:  # Nhấn chuột phải
                pyautogui.click(x / scaled_width * screen_width, y / scaled_height * screen_height, button='right', duration=0)
            elif event_type == 3:  # Cuộn chuột lên
                pyautogui.scroll(60)  # Cuộn lên
            elif event_type == 4:  # Cuộn chuột xuống
                pyautogui.scroll(-60)  # Cuộn xuống

        except Exception as e:
            print(f"Error handling mouse event: {e}")
            break

class KeyEventType(enum.Enum):
    PRESS = 1
    RELEASE = 2

# Hàm xử lý sự kiện bàn phím
def handle_keyboard_event(client_socket):
    while not stop_event.is_set():
        try:
            # Nhận độ dài gói tin
            length_bytes = client_socket.recv(4)
            if not length_bytes:
                break

            packet_length = struct.unpack('!I', length_bytes)[0]
                
            # Nhận toàn bộ gói tin
            packet = client_socket.recv(packet_length)
                
            # Giải mã gói tin
            event_type, is_special, key_length, key_bytes = struct.unpack(
                f'!BBB{len(packet) - 3}s', packet
            )
 
            # Chuyển đổi dữ liệu
            key = key_bytes.decode('utf-8')
            event_type = KeyEventType(event_type)

            # Thực thi sự kiện
            execute_key_event(event_type, key, is_special)

        except Exception as e:
            print(f"Lỗi nhận sự kiện: {e}")
            break

def execute_key_event(event_type, key, is_special):
    try:
        # Ánh xạ phím đặc biệt
        special_key_map = {
            'Key.space': keyboard.Key.space,
            'Key.enter': keyboard.Key.enter,
            'Key.shift': keyboard.Key.shift,
            'Key.ctrl': keyboard.Key.ctrl,
            'Key.alt': keyboard.Key.alt,
            'Key.tab': keyboard.Key.tab,
            'Key.backspace': keyboard.Key.backspace,
            'Key.caps_lock': keyboard.Key.caps_lock,
            'Key.up': keyboard.Key.up,
            'Key.down': keyboard.Key.down,
            'Key.left': keyboard.Key.left,
            'Key.right': keyboard.Key.right,
            'Key.esc': keyboard.Key.esc
        }

        if is_special:
            mapped_key = special_key_map.get(key)
            if mapped_key:
                key = mapped_key

            # Thực thi sự kiện
        if event_type == KeyEventType.PRESS:
            keyboard_controller.press(key)
        else:
            keyboard_controller.release(key)

    except Exception as e:
        print(f"Lỗi thực thi sự kiện: {e}")

if __name__ == "__main__":
    run_server()
