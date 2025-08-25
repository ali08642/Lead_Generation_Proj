#!/usr/bin/env python3
"""
Persistent browser manager that prevents reinstallation on every new PC
Uses a consistent storage location and properly detects bundled browsers
"""

import os
import sys
import logging
import platform
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

def get_app_data_dir() -> Path:
    """Get a persistent app data directory for browsers across runs"""
    try:
        if platform.system() == "Windows":
            # Use %APPDATA% on Windows
            app_data = Path(os.environ.get("APPDATA", "")) / "GoogleMapsScraper"
        elif platform.system() == "Darwin":
            # Use ~/Library/Application Support on macOS
            app_data = Path.home() / "Library" / "Application Support" / "GoogleMapsScraper"
        else:
            # Use ~/.config on Linux
            app_data = Path.home() / ".config" / "GoogleMapsScraper"
        
        # Create directory if it doesn't exist
        app_data.mkdir(parents=True, exist_ok=True)
        browsers_dir = app_data / "playwright_browsers"
        browsers_dir.mkdir(exist_ok=True)
        
        return browsers_dir
    except Exception as e:
        logger.error(f"Failed to create app data directory: {e}")
        # Fallback to a temp directory in the working directory
        fallback_dir = Path(os.getcwd()) / ".browsers"
        fallback_dir.mkdir(exist_ok=True)
        return fallback_dir

def get_bundle_browser_path() -> Path:
    """Get path to bundled browsers in the executable"""
    if hasattr(sys, '_MEIPASS'):
        # Check different possible paths in the bundle
        bundle_dir = Path(sys._MEIPASS)
        candidates = [
            bundle_dir / "ms-playwright",
            bundle_dir / "playwright_browsers",
            bundle_dir / "playwright_browsers" / "ms-playwright",
            bundle_dir / ".local-browsers"
        ]
        
        for path in candidates:
            if path.exists() and any(path.glob("*")):  # Check if not empty
                logger.info(f"Found bundled browsers at: {path}")
                return path
                
        logger.warning("No browsers found in executable bundle")
    
    return Path()  # Return empty path if not found

def setup_persistent_browsers() -> bool:
    """
    Setup browsers using this priority:
    1. Use bundled browsers if available
    2. Use browsers in persistent storage if available
    3. Otherwise, flag for installation
    
    Returns True if browsers are available and ready to use
    """
    # Get persistent storage location
    persistent_dir = get_app_data_dir()
    logger.info(f"Persistent browser directory: {persistent_dir}")
    
    # Priority 1: Check for bundled browsers in executable
    bundled_path = get_bundle_browser_path()
    if bundled_path.exists() and any(bundled_path.glob("*")):
        # We have bundled browsers! Copy them to persistent storage if needed
        if not any(persistent_dir.glob("*")) or not os.listdir(str(persistent_dir)):
            logger.info(f"Copying bundled browsers to persistent storage: {persistent_dir}")
            try:
                # Copy bundled browsers to persistent location
                for item in bundled_path.glob("*"):
                    if item.is_dir():
                        shutil.copytree(item, persistent_dir / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, persistent_dir / item.name)
                logger.info("Bundled browsers copied successfully")
            except Exception as e:
                logger.error(f"Failed to copy bundled browsers: {e}")
        
        # Set environment variable to use persistent location
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(persistent_dir)
        logger.info(f"Using persistent browsers at: {persistent_dir}")
        return True
    
    # Priority 2: Check for browsers in persistent storage
    if persistent_dir.exists() and any(persistent_dir.glob("*")) and os.listdir(str(persistent_dir)):
        # We have browsers in persistent storage
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(persistent_dir)
        logger.info(f"Using existing persistent browsers at: {persistent_dir}")
        return True
    
    # Priority 3: No browsers available, need installation
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(persistent_dir)
    logger.info(f"No browsers available, will need installation to: {persistent_dir}")
    return False

def check_browsers_available() -> bool:
    """Check if browsers are properly setup and working"""
    try:
        # Try importing and testing Playwright
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
            logger.info("Browsers are working correctly")
            return True
            
    except Exception as e:
        logger.warning(f"Browsers not available or not working: {e}")
        return False

def get_browser_status() -> dict:
    """Get status of persistent browsers"""
    persistent_dir = get_app_data_dir()
    bundled_path = get_bundle_browser_path()
    has_bundled = bundled_path.exists() and any(bundled_path.glob("*"))
    has_persistent = persistent_dir.exists() and any(persistent_dir.glob("*"))
    browsers_working = check_browsers_available()
    
    if browsers_working:
        return {
            "available": True,
            "bundled_found": has_bundled,
            "persistent_found": has_persistent,
            "status": "Browsers ready to use",
            "location": str(persistent_dir)
        }
    elif has_persistent:
        return {
            "available": False,
            "bundled_found": has_bundled,
            "persistent_found": True,
            "status": "Browsers found but not working - may need reinstallation",
            "location": str(persistent_dir)
        }
    elif has_bundled:
        return {
            "available": False,
            "bundled_found": True,
            "persistent_found": False,
            "status": "Bundled browsers found but not copied - may need installation",
            "location": str(bundled_path)
        }
    else:
        return {
            "available": False,
            "bundled_found": False,
            "persistent_found": False,
            "status": "No browsers available - installation required",
            "location": str(persistent_dir)
        }

# Initialize on module import
setup_persistent_browsers()
