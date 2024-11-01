import sys
import threading
import time
from watchdog.observers import Observer
from openuwork.file_handler import DirectoryEventHandler
from openuwork.network import start_server

# TODO: remove it before submit
from config.settings import (
    SERVER_HOST,
    SERVER_PORT_1,
    SERVER_PORT_2,
    TARGET_PORT_1,
    TARGET_PORT_2,
    SYNC_DIR_1,
    SYNC_DIR_2,
)


def watch_directory(sync_dir, target_host, target_port):
    event_handler = DirectoryEventHandler(sync_dir, target_host, target_port)
    observer = Observer()
    observer.schedule(event_handler, sync_dir, recursive=True)
    observer.start()
    print(f"Watching directory: {sync_dir}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    # TODO: remove it before submit

    # client = sys.argv[1]
    # print(client)
    # if client == "1":
    #     server_port = SERVER_PORT_1
    #     target_port = TARGET_PORT_1
    #     sync_dir = SYNC_DIR_1
    # elif client == "2":
    #     server_port = SERVER_PORT_2
    #     target_port = TARGET_PORT_2
    #     sync_dir = SYNC_DIR_2

    sync_dir = input("Enter the path to the directory to sync: ")
    server_host = "0.0.0.0"
    server_port = int(input("Enter the port for your server: "))
    target_host = "127.0.0.1"
    target_port = int(input("Enter the port of the other machine's server: "))

    threading.Thread(
        target=start_server, args=(sync_dir, server_host, server_port), daemon=True
    ).start()

    watch_directory(sync_dir, target_host, target_port)


if __name__ == "__main__":
    main()
