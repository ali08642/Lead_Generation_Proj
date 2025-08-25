#!/usr/bin/env python3
"""
Async event loop management for Flask
"""

import asyncio
import threading
import time
import logging

logger = logging.getLogger(__name__)

class AsyncEventLoopManager:
    """Proper async event loop management for Flask"""
    
    def __init__(self):
        self.loop = None
        self.thread = None
        self._lock = threading.Lock()
    
    def get_loop(self):
        """Get or create event loop"""
        with self._lock:
            if self.loop is None or self.loop.is_closed():
                self._start_loop()
            return self.loop
    
    def _start_loop(self):
        """Start event loop in dedicated thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        if self.thread and self.thread.is_alive():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.thread.join(timeout=5.0)
            except:
                pass
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
        # Wait for loop to be ready
        timeout = 10.0
        start_time = time.time()
        while (self.loop is None or not self.loop.is_running()) and (time.time() - start_time) < timeout:
            time.sleep(0.1)
    
    def run_async(self, coro, timeout=300.0):
        """Run async function safely"""
        loop = self.get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout) 