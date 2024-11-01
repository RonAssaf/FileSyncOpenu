import os
import time
from watchdog.events import FileSystemEventHandler
from network import sync_file, sync_delete, sync_directory
from utils import md5
from config.settings import SYNC_MARKER_DIR, DEBOUNCE_DELAY


class DirectoryEventHandler(FileSystemEventHandler):
    def __init__(self, sync_dir, target_host, target_port):
        self.sync_dir = sync_dir
        self.target_host = target_host
        self.target_port = target_port
        self.marker_path = os.path.join(sync_dir, SYNC_MARKER_DIR)
        os.makedirs(self.marker_path, exist_ok=True)
        self.last_sync_time = {}
        self.syncing = False
        self.file_hashes = {}

    def on_created(self, event):
        if not self.is_sync_marker(event.src_path):
            print(f"Created: {event.src_path}")
            self.sync(event.src_path, "CREATE")

    def on_modified(self, event):
        if not self.is_sync_marker(event.src_path) and not self.syncing:
            current_time = time.time()
            if (
                event.src_path not in self.last_sync_time
                or current_time - self.last_sync_time[event.src_path] > DEBOUNCE_DELAY
            ):
                if self.has_file_changed(event.src_path):
                    print(f"Modified: {event.src_path}")
                    self.sync(event.src_path, "MODIFY")
                self.last_sync_time[event.src_path] = current_time

    def on_deleted(self, event):
        if not self.is_sync_marker(event.src_path):
            print(f"Deleted: {event.src_path}")
            self.sync(event.src_path, "DELETE")

    def on_moved(self, event):
        if not self.is_sync_marker(event.src_path) and not self.syncing:
            self.sync(event.src_path, "DELETE")
            self.sync(event.dest_path, "CREATE")
            self.last_sync_time[event.src_path] = time.time()

    def is_sync_marker(self, path):
        return ".sync" in path

    def get_sync_marker_path(self, path):
        relative_path = os.path.relpath(path, self.sync_dir)
        return os.path.join(self.marker_path, f"{relative_path}.sync")

    def sync(self, path, event_type):
        marker_path = self.get_sync_marker_path(path)
        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        open(marker_path, "a").close()

        self.syncing = True
        try:
            if event_type == "DELETE":
                sync_delete(path, self.sync_dir, self.target_host, self.target_port)
            else:
                self.sync_file_or_directory(path, event_type)
        finally:
            self.syncing = False

        time.sleep(1)
        if os.path.exists(marker_path):
            os.remove(marker_path)

    def sync_file_or_directory(self, path, event_type):
        if os.path.isdir(path):
            print(f"Syncing directory: {path}")
            sync_directory(
                path, self.sync_dir, self.target_host, self.target_port, event_type
            )
        else:
            print(f"Syncing file: {path}")
            sync_file(
                path, self.sync_dir, self.target_host, self.target_port, event_type
            )

    def has_file_changed(self, file_path):
        if not os.path.isfile(file_path):
            return False

        new_hash = md5(file_path)
        if file_path in self.file_hashes:
            if self.file_hashes[file_path] == new_hash:
                return False
        self.file_hashes[file_path] = new_hash
        return True
