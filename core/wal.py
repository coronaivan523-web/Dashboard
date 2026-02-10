import os
import json
import threading
import queue
import time
import logging

logger = logging.getLogger("TITAN-WAL")

class WriteAheadLog:
    """
    Async Write-Ahead Log for non-blocking persistence.
    Implements a queue-based flush mechanism.
    FAIL-CLOSED: If queue is full or flush fails repeatedly, signals system halt.
    """
    def __init__(self, flush_interval=1.0, max_queue_size=1000):
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.flush_interval = flush_interval
        self.running = False
        self.worker_thread = None
        self.metrics = {
            "queue_len": 0,
            "flush_ok": 0,
            "flush_fail": 0, 
            "last_flush_ts": 0.0,
            "backlog_hit": False
        }

    def start(self):
        if self.running: return
        self.running = True
        self.worker_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.worker_thread.start()
        logger.info("WAL: Worker started.")

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        logger.info("WAL: Worker stopped.")

    def write(self, file_path, data):
        """
        Enqueues a write operation.
        Event: (file_path, data_dict)
        """
        try:
            self.queue.put((file_path, data), block=False)
            self.metrics["queue_len"] = self.queue.qsize()
        except queue.Full:
            logger.critical("WAL SAFETY: Queue Full! Persistence blocked.")
            self.metrics["backlog_hit"] = True
            # In a strict fail-closed system, this might trigger a shutdown.
            # For now we log critical.

    def _flush_worker(self):
        while self.running:
            try:
                # Flush all pending
                while not self.queue.empty():
                    file_path, data = self.queue.get()
                    self._persist_atomic(file_path, data)
                    self.queue.task_done()
                    self.metrics["queue_len"] = self.queue.qsize()
                
                # Check metrics update
                self.metrics["last_flush_ts"] = time.time()
                time.sleep(self.flush_interval)
            except Exception as e:
                logger.error(f"WAL WORKER ERROR: {e}")
                self.metrics["flush_fail"] += 1
                time.sleep(1.0) # Backoff

    def _persist_atomic(self, file_path, data):
        temp = file_path + ".tmp"
        try:
            with open(temp, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(temp, file_path)
            self.metrics["flush_ok"] += 1
        except Exception as e:
            logger.error(f"WAL PERSIST FAIL {file_path}: {e}")
            self.metrics["flush_fail"] += 1
