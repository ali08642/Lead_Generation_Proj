#!/usr/bin/env python3
"""
Simple Playwright browser installer for .exe distribution
Based on official Playwright documentation approaches
Now uses persistent storage to prevent reinstallation on every PC
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from persistent_browser_manager import get_app_data_dir, setup_persistent_browsers, check_browsers_available

logger = logging.getLogger(__name__)


def check_browsers_installed() -> bool:
    """Check if Playwright browsers are installed and working"""
    # First try to setup persistent browsers (which includes bundled browser handling)
    try:
        setup_persistent_browsers()
        return check_browsers_available()
    except Exception as e:
        logger.debug(f"Browser check failed: {e}")
        return False


def install_browsers(progress_callback=None) -> bool:
    """Install Playwright browsers using official command with progress tracking"""
    try:
        # Get persistent storage directory
        persistent_dir = get_app_data_dir()
        logger.info(f"Installing Playwright browsers to persistent location: {persistent_dir}")
        logger.info("This will download ~127MB for Chromium browser")
        
        # Set environment variable to install to persistent location
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(persistent_dir)
        
        if progress_callback:
            progress_callback("Starting browser installation...", 0)
        
        # Use the official Playwright install command with real-time output
        process = subprocess.Popen([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
           text=True, universal_newlines=True, bufsize=1)
        
        output_lines = []
        download_started = False
        current_progress = 0
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                output_lines.append(output.strip())
                line = output.strip()
                logger.info(f"Playwright: {line}")
                
                # Enhanced progress tracking based on output patterns
                if progress_callback:
                    # Initial setup phase
                    if "Downloading" in line and "chromium" in line.lower():
                        download_started = True
                        current_progress = 15
                        progress_callback("Starting Chromium download...", current_progress)
                    
                    # Download progress tracking
                    elif "downloading" in line.lower() or "downloaded" in line.lower():
                        if any(size in line for size in ["MB", "KB", "GB"]):
                            # Try to extract percentage or size information
                            if "%" in line:
                                try:
                                    percent = int(line.split("%")[0].split()[-1])
                                    current_progress = 15 + (percent * 0.5)  # 15-65% for download
                                    progress_callback(f"Downloading: {percent}%", int(current_progress))
                                except:
                                    current_progress = min(current_progress + 5, 60)
                                    progress_callback(f"Downloading: {line[:50]}...", current_progress)
                            else:
                                current_progress = min(current_progress + 3, 60)
                                progress_callback(f"Downloading: {line[:50]}...", current_progress)
                    
                    # Extraction/Installation phase
                    elif any(word in line.lower() for word in ["extracting", "installing", "setting up"]):
                        current_progress = 70
                        progress_callback("Extracting and installing browser...", current_progress)
                    
                    # Completion indicators
                    elif any(word in line.lower() for word in ["success", "installed", "complete"]) and "chromium" in line.lower():
                        current_progress = 95
                        progress_callback("Installation completed!", current_progress)
                    
                    # Progress during various phases
                    elif any(word in line.lower() for word in ["preparing", "checking", "verifying"]):
                        if current_progress < 10:
                            current_progress = 5
                            progress_callback("Preparing installation...", current_progress)
                    
                    # Generic progress increment for active lines
                    elif line and not any(skip in line.lower() for skip in ["warning", "error"]) and download_started:
                        if current_progress < 90:
                            current_progress = min(current_progress + 1, 90)
                            progress_callback(f"Installing: {line[:40]}...", current_progress)
        
        # Wait for process to complete
        return_code = process.poll()
        
        if return_code == 0:
            logger.info("✅ Browsers installed successfully!")
            if progress_callback:
                progress_callback("Browsers installed successfully!", 100)
            return True
        else:
            error_output = '\n'.join(output_lines[-10:])  # Last 10 lines
            logger.error(f"Browser installation failed: {error_output}")
            if progress_callback:
                progress_callback("Installation failed", -1)
            return False
            
    except Exception as e:
        logger.error(f"Browser installation error: {e}")
        if progress_callback:
            progress_callback(f"Installation error: {str(e)}", -1)
        return False


def get_browser_status() -> dict:
    """Get simple browser status"""
    # Import here to avoid circular imports
    from persistent_browser_manager import get_browser_status as get_persistent_status
    
    # Get detailed status from persistent manager
    detailed_status = get_persistent_status()
    
    # Return simplified status for backwards compatibility
    return {
        "installed": detailed_status["available"],
        "status": "Ready" if detailed_status["available"] else "Not installed",
        "size_info": "~127MB download required" if not detailed_status["available"] else "Installed",
        "location": detailed_status["location"]
    }
