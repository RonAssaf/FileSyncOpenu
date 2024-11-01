import os
import socket
import threading
import time
from config.settings import BUFFER_SIZE, SYNC_MARKER_DIR


def start_server(sync_dir, server_host, server_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((server_host, server_port))
        server_sock.listen()
        print(f"Server listening on {server_host}:{server_port}")
        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(conn, sync_dir)).start()


def handle_client(conn, sync_dir):
    with conn:
        metadata = conn.recv(BUFFER_SIZE).decode()
        event_type, name, file_size_str, file_type = metadata.split("|")

        path = os.path.join(sync_dir, name)
        marker_path = os.path.join(sync_dir, SYNC_MARKER_DIR, f"{name}.sync")

        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        open(marker_path, "a").close()

        conn.sendall("OK".encode())

        if event_type == "DELETE":
            if os.path.exists(path):
                if os.path.isdir(path):
                    os.rmdir(path)
                    print(f"Deleted directory: {name}")
                else:
                    os.remove(path)
                    print(f"Deleted file: {name}")
        else:
            if event_type == "CREATE" and file_type == "directory":
                os.makedirs(path, exist_ok=True)
                print(f"Created directory: {name}")

            if file_type == "file":
                os.makedirs(os.path.dirname(path), exist_ok=True)

                with open(path, "wb") as f:
                    remaining = int(file_size_str)
                    while remaining > 0:
                        data = conn.recv(min(BUFFER_SIZE, remaining))
                        if not data:
                            break
                        f.write(data)
                        remaining -= len(data)
                print(f"Saved file: {name}")

        time.sleep(1)
        if os.path.exists(marker_path):
            os.remove(marker_path)


def sync_file(file_path, sync_dir, target_host, target_port, event_type):
    relative_path = os.path.relpath(file_path, sync_dir)
    file_size = os.path.getsize(file_path) if event_type != "DELETE" else 0

    message = f"{event_type}|{relative_path}|{file_size}|file"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((target_host, target_port))
        s.sendall(message.encode())

        response = s.recv(BUFFER_SIZE).decode()
        if response == "OK" and event_type != "DELETE":
            with open(file_path, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    s.sendall(chunk)

    print(f"Synced file: {relative_path}")


def sync_delete(path, sync_dir, target_host, target_port):
    relative_path = os.path.relpath(path, sync_dir)
    message = f"DELETE|{relative_path}|0|file"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((target_host, target_port))
        s.sendall(message.encode())
        response = s.recv(BUFFER_SIZE).decode()
        if response == "OK":
            print(f"Sent delete command for: {relative_path}")


def sync_directory(dir_path, sync_dir, target_host, target_port, event_type):
    for root, dirs, files in os.walk(dir_path):
        relative_root = os.path.relpath(root, sync_dir)

        message = f"{event_type}|{relative_root}|0|directory"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((target_host, target_port))
            s.sendall(message.encode())
            response = s.recv(BUFFER_SIZE).decode()
            if response != "OK":
                print(f"Failed to sync directory: {relative_root}")
                continue

        for file in files:
            file_path = os.path.join(root, file)
            sync_file(file_path, sync_dir, target_host, target_port, event_type)

    print(f"Synced directory: {os.path.relpath(dir_path, sync_dir)}")
