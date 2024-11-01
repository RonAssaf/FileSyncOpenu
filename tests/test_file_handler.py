import os
import unittest
import tempfile
import threading
import time
import socket
from watchdog.events import FileSystemEvent
from openuwork.file_handler import DirectoryEventHandler
import shutil


def start_test_server(host="localhost", port=8080):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Test server started on {host}:{port}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        data = client_socket.recv(1024).decode()
        if data:
            print(f"Received: {data}")
            client_socket.sendall(b"OK")
        client_socket.close()


class TestDirectoryEventHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the test server in a separate thread
        cls.server_thread = threading.Thread(target=start_test_server, daemon=True)
        cls.server_thread.start()
        time.sleep(1)

    def setUp(self):
        # Create a temporary directory for testing
        self.sync_dir = tempfile.mkdtemp()
        self.target_host = "localhost"
        self.target_port = 8080
        self.handler = DirectoryEventHandler(
            self.sync_dir, self.target_host, self.target_port
        )

    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists(self.sync_dir):
            shutil.rmtree(self.sync_dir)

    def test_sync_file_or_directory_file(self):
        test_file_path = os.path.join(self.sync_dir, "test_file.txt")

        with open(test_file_path, "w") as f:
            f.write("YAIR AND RON")

        self.handler.sync_file_or_directory(test_file_path, "CREATE")

        self.assertTrue(os.path.exists(test_file_path))

    def test_sync_file_or_directory_directory(self):
        test_dir_path = os.path.join(self.sync_dir, "test_directory")
        os.makedirs(test_dir_path)

        self.handler.sync_file_or_directory(test_dir_path, "CREATE")

        self.assertTrue(os.path.exists(test_dir_path))

    def test_on_created_event(self):
        event = FileSystemEvent(src_path=os.path.join(self.sync_dir, "new_file.txt"))

        with open(event.src_path, "w") as f:
            f.write("New file content")

        self.handler.on_created(event)

        self.assertTrue(os.path.exists(event.src_path))

    def test_on_deleted_event(self):
        test_file_path = os.path.join(self.sync_dir, "delete_me.txt")

        with open(test_file_path, "w") as f:
            f.write("Delete - YAIR AND RON")

        event = FileSystemEvent(src_path=test_file_path)
        os.remove(test_file_path)

        self.handler.on_deleted(event)

        self.assertFalse(os.path.exists(event.src_path))

    def test_on_modified_event_with_debounce(self):
        test_file_path = os.path.join(self.sync_dir, "modify_me.txt")

        with open(test_file_path, "w") as f:
            f.write("YAIR AND RON")

        event = FileSystemEvent(src_path=test_file_path)
        self.handler.on_modified(event)

        self.assertTrue(os.path.exists(test_file_path))

    def test_on_moved_event(self):
        test_file_path = os.path.join(self.sync_dir, "move_me.txt")

        with open(test_file_path, "w") as f:
            f.write("Move me!")

        new_path = os.path.join(self.sync_dir, "moved_file.txt")
        os.rename(test_file_path, new_path)

        event = FileSystemEvent(src_path=test_file_path, dest_path=new_path)

        self.handler.on_moved(event)

        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(test_file_path))


if __name__ == "__main__":
    unittest.main()
