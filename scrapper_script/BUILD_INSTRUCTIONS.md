# Google Maps Scraper - Build Instructions

This guide will help you compile the Google Maps Scraper into a single executable file.

## Prerequisites

- Windows 10 or later (64-bit)
- Python 3.8 or higher
- Internet connection for downloading dependencies

## Quick Build (Recommended)

1. **Double-click `build_setup.bat`**
   - This will automatically install all dependencies and build the executable
   - The process takes 5-10 minutes depending on your system

2. **Find your executable**
   - Look in the `dist` folder for `GoogleMapsScraper.exe`
   - Also check for `run_scraper.bat` in the root directory

## Manual Build Process

If you prefer to build manually or the automatic process fails:

### Step 1: Install Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m pip install -r requirements_build.txt
```

### Step 2: Run Build Script
```bash
python build_exe.py
```

### Step 3: Test the Executable
```bash
# Option 1: Use the run script
run_scraper.bat

# Option 2: Run directly
dist/GoogleMapsScraper.exe
```

## What Gets Built

The build process creates:

- **`dist/GoogleMapsScraper.exe`** - Single executable file (~50-100MB)
- **`run_scraper.bat`** - Convenient launcher script
- **`build/`** - Temporary build files (can be deleted)
- **`GoogleMapsScraper.spec`** - PyInstaller specification file

## Executable Features

The compiled executable includes:

✅ **Complete Application** - All Python code and dependencies  
✅ **Web Server** - Flask-based API server  
✅ **Database Support** - SQLite and Supabase integration  
✅ **Browser Automation** - Playwright for web scraping  
✅ **Configuration Files** - All necessary config files bundled  
✅ **No Installation Required** - Runs on any Windows machine  

## Distribution

To distribute the application:

1. Copy `GoogleMapsScraper.exe` to any Windows machine
2. Copy `run_scraper.bat` (optional, for easier launching)
3. Create a `.env` file with your configuration (see Configuration section)

## Configuration

The executable will look for a `.env` file in the same directory:

```env
# Database Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
ADMIN_ID=your_admin_id

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# N8N Integration
N8N_WEBHOOK_URL=http://localhost:5678/webhook/job-completion

# Scraping Configuration
DEFAULT_MAX_RESULTS=50
CACHE_TTL_MINUTES=0
```

## Troubleshooting

### Build Fails
- Ensure Python 3.8+ is installed
- Check internet connection for dependency downloads
- Try running as administrator if permission issues occur

### Executable Won't Start
- Check Windows Defender/Antivirus isn't blocking it
- Ensure all required files are in the same directory
- Check the `.env` configuration file

### Missing Dependencies
- The executable includes all Python dependencies
- Playwright browsers are downloaded automatically on first run
- No additional installation required

### Large File Size
- The executable is ~50-100MB due to included dependencies
- This is normal for Python applications with web automation
- Much smaller than alternatives that bundle browsers

## Advanced Options

### Custom Icon
To add a custom icon:
1. Place your `.ico` file in the project directory
2. Update the spec file to include: `icon='your_icon.ico'`

### Smaller Build
To reduce file size:
1. Remove unused dependencies from `requirements_build.txt`
2. Add `--exclude-module` options to PyInstaller
3. Use `--strip` option (may affect debugging)

### Debug Build
For debugging:
1. Remove `--onefile` option for faster builds
2. Add `--debug` flag to PyInstaller
3. Check `build/` directory for intermediate files

## Support

If you encounter issues:

1. Check the build logs in the console output
2. Ensure all prerequisites are met
3. Try the manual build process
4. Check for Windows updates and Visual C++ redistributables

## Performance Notes

- First run may be slower as Playwright downloads browsers
- Subsequent runs will be faster
- The executable uses the same performance as the Python version
- Memory usage is similar to running the Python script directly
