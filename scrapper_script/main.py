#!/usr/bin/env python3
"""
Main entry point for the Optimized Google Maps Scraper
"""

import logging
import sys
from server import ProductionServer

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Set specific log levels for noisy modules
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.INFO)

if __name__ == '__main__':
    try:
        server = ProductionServer()
        server.run()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1) 