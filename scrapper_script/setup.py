#!/usr/bin/env python3
"""
Setup script for Google Maps Scraper
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Google Maps Scraper...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Install Playwright browsers
    if not run_command("playwright install chromium", "Installing Playwright browsers"):
        print("❌ Failed to install Playwright browsers")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run the server: python main.py")
    print("2. Test the health endpoint: curl http://localhost:5000/health")
    print("3. Make a scraping request:")
    print("   curl -X POST http://localhost:5000/scrape-single \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"search_term\": \"restaurants\", \"area_name\": \"Lahore\"}'")
    
    print("\n📚 Documentation:")
    print("- README.md: Quick start guide")
    print("- DOCUMENTATION.md: Comprehensive documentation")
    print("- LIBRARIES_REFERENCE.md: Library usage guide")

if __name__ == "__main__":
    main() 