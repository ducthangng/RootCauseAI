"""
Watch a folder for new files and trigger a processing pipeline.

Two implementations:
1. watch_folder_events()  -> event-driven, uses `watchdog` (inotify on Linux). Preferred: low latency, low CPU.
2. watch_folder_polling() -> zero-dependency fallback, uses os.scandir() in a loop. Use only if you can't install packages.

Install for (1):  pip install watchdog --break-system-packages
"""

import os
import time
import shutil
import logging
from pathlib import Path
from typing import Callable

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("folder_watcher")


# ---------------------------------------------------------------------------
# Your pipeline goes here. Replace this with the real thing.
# ---------------------------------------------------------------------------
def process_pipeline(filepath: Path) -> None:
    log.info(f"Processing: {filepath}")
    # e.g. df = pd.read_csv(filepath); transform(df); load(df)
    # move/delete the file afterwards so it isn't reprocessed:
    processed_dir = filepath.parent / "processed"
    processed_dir.mkdir(exist_ok=True)
    shutil.move(str(filepath), str(processed_dir / filepath.name))


def _is_file_stable(filepath: Path, checks: int = 2, interval: float = 0.5) -> bool:
    """
    A file 'exists' the moment it's created, but may still be mid-write (large CSV,
    slow network copy). This polls its size N times and only returns True once
    the size stops changing — that's your signal the writer closed the handle.
    """
    last_size = -1
    for _ in range(checks):
        try:
            size = filepath.stat().st_size
        except FileNotFoundError:
            return False
        if size != last_size:
            last_size = size
            time.sleep(interval)
        else:
            return True
    return True


# ---------------------------------------------------------------------------
# Option 1: event-driven (watchdog / inotify)
# ---------------------------------------------------------------------------
def watch_folder_events(
    folder: str,
    on_new_file: Callable[[Path], None] = process_pipeline,
    pattern: str = "*",
) -> None:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            fp = Path(event.src_path)
            if not fp.match(pattern):
                return
            if not _is_file_stable(fp):
                log.warning(f"Skipped (disappeared before stabilizing): {fp}")
                return
            try:
                on_new_file(fp)
            except Exception:
                log.exception(f"Pipeline failed for {fp}")

    observer = Observer()
    observer.schedule(Handler(), str(folder_path), recursive=False)
    observer.start()
    log.info(f"Watching {folder_path} (event-driven, Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# Option 2: polling fallback, no external deps
# ---------------------------------------------------------------------------
def watch_folder_polling(
    folder: str,
    on_new_file: Callable[[Path], None] = process_pipeline,
    interval: float = 2.0,
    pattern: str = "*",
) -> None:
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    seen = set(p.name for p in folder_path.glob(pattern))

    log.info(f"Watching {folder_path} (polling every {interval}s, Ctrl+C to stop)")
    try:
        while True:
            current = set(p.name for p in folder_path.glob(pattern))
            for name in current - seen:
                fp = folder_path / name
                if fp.is_dir():
                    continue
                if not _is_file_stable(fp):
                    continue
                try:
                    on_new_file(fp)
                except Exception:
                    log.exception(f"Pipeline failed for {fp}")
            seen = current
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    WATCH_DIR = Path(__file__).resolve().parent.parent / "data"
    try:
        watch_folder_events(WATCH_DIR)
    except ImportError:
        log.warning("watchdog not installed, falling back to polling")
        watch_folder_polling(WATCH_DIR)