#!/usr/bin/env python3
"""
GUI Application for Google Maps Scraper Server
Provides easy configuration and server management for end users
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import logging
import os
import sys
import json
import webbrowser
from datetime import datetime
from typing import Dict, Any
import configparser
from pathlib import Path
import shutil

# Use the new persistent browser manager to handle bundled browsers properly
# This prevents re-downloading on each machine
try:
	from persistent_browser_manager import setup_persistent_browsers
	setup_persistent_browsers()
except Exception as e:
	# Log the error but don't fail
	logging.warning(f"Failed to setup persistent browsers: {e}")

# Import the server components
from server import ProductionServer
from database_manager import DatabaseManager
from webhook_handler import WebhookHandler
from browser_installer import check_browsers_installed, install_browsers as install_playwright_browsers, get_browser_status
from persistent_browser_manager import get_browser_status as get_persistent_browser_status, check_browsers_available


class ScraperGUI:
	"""GUI Application for Google Maps Scraper Server"""
	
	def __init__(self):
		self.root = tk.Tk()
		self.root.title("Google Maps Scraper Server - Admin Panel")
		self.root.geometry("900x700")
		self.root.resizable(True, True)
		
		# Server and logging
		self.server = None
		self.server_thread = None
		self.log_queue = queue.Queue()
		self.is_server_running = False
		
		# Configuration
		self.config_file = "scraper_config.json"
		self.config = self.load_config()
		
		# Setup GUI
		self.setup_gui()
		self.setup_logging()
		
		# Start log processing
		self.process_log_queue()
		
		# Load saved configuration
		self.load_saved_config()
		
		# Protocol for window closing
		self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

	def setup_gui(self):
		"""Setup the main GUI components"""
		
		# Create notebook for tabs
		self.notebook = ttk.Notebook(self.root)
		self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
		
		# Configuration Tab
		self.config_frame = ttk.Frame(self.notebook)
		self.notebook.add(self.config_frame, text="Configuration")
		self.setup_config_tab()
		
		# Server Control Tab
		self.control_frame = ttk.Frame(self.notebook)
		self.notebook.add(self.control_frame, text="Server Control")
		self.setup_control_tab()
		
		# Logs Tab
		self.logs_frame = ttk.Frame(self.notebook)
		self.notebook.add(self.logs_frame, text="Server Logs")
		self.setup_logs_tab()
		
		# Status bar
		self.status_bar = ttk.Label(self.root, text="Server Status: Stopped", relief=tk.SUNKEN)
		self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

	def setup_config_tab(self):
		"""Setup configuration tab"""
		
		# Main configuration frame
		main_frame = ttk.LabelFrame(self.config_frame, text="Server Configuration", padding=10)
		main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
		
		# Database Configuration
		db_frame = ttk.LabelFrame(main_frame, text="Database Settings", padding=10)
		db_frame.pack(fill=tk.X, pady=(0, 10))
		
		ttk.Label(db_frame, text="Supabase URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
		self.supabase_url = ttk.Entry(db_frame, width=60)
		self.supabase_url.grid(row=0, column=1, padx=(10, 0), pady=2)
		
		ttk.Label(db_frame, text="Supabase API Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
		self.supabase_key = ttk.Entry(db_frame, width=60, show="*")
		self.supabase_key.grid(row=1, column=1, padx=(10, 0), pady=2)
		
		ttk.Label(db_frame, text="Admin ID:").grid(row=2, column=0, sticky=tk.W, pady=2)
		self.admin_id = ttk.Entry(db_frame, width=20)
		self.admin_id.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
		
		# Server Configuration
		server_frame = ttk.LabelFrame(main_frame, text="Server Settings", padding=10)
		server_frame.pack(fill=tk.X, pady=(0, 10))
		
		ttk.Label(server_frame, text="Server Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
		self.server_host = ttk.Entry(server_frame, width=30)
		self.server_host.grid(row=0, column=1, padx=(10, 0), pady=2)
		
		ttk.Label(server_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
		self.server_port = ttk.Entry(server_frame, width=30)
		self.server_port.grid(row=1, column=1, padx=(10, 0), pady=2)
		
		# N8N Configuration
		n8n_frame = ttk.LabelFrame(main_frame, text="N8N Integration", padding=10)
		n8n_frame.pack(fill=tk.X, pady=(0, 10))
		
		ttk.Label(n8n_frame, text="Job Completion Webhook:").grid(row=0, column=0, sticky=tk.W, pady=2)
		self.n8n_webhookC = ttk.Entry(n8n_frame, width=60)
		self.n8n_webhookC.grid(row=0, column=1, padx=(10, 0), pady=2)
		
		ttk.Label(n8n_frame, text="Test Connection Webhook:").grid(row=1, column=0, sticky=tk.W, pady=2)
		self.n8n_webhookT = ttk.Entry(n8n_frame, width=60)
		self.n8n_webhookT.grid(row=1, column=1, padx=(10, 0), pady=2)
		
		# Scraping Configuration
		scraping_frame = ttk.LabelFrame(main_frame, text="Scraping Settings", padding=10)
		scraping_frame.pack(fill=tk.X, pady=(0, 10))
		
		ttk.Label(scraping_frame, text="Default Max Results:").grid(row=0, column=0, sticky=tk.W, pady=2)
		self.max_results = ttk.Entry(scraping_frame, width=30)
		self.max_results.grid(row=0, column=1, padx=(10, 0), pady=2)
		
		# Buttons
		button_frame = ttk.Frame(main_frame)
		button_frame.pack(fill=tk.X, pady=(10, 0))
		
		ttk.Button(button_frame, text="Save Configuration", command=self.save_config).pack(side=tk.LEFT, padx=(0, 10))
		ttk.Button(button_frame, text="Test Database Connection", command=self.test_database).pack(side=tk.LEFT, padx=(0, 10))
		ttk.Button(button_frame, text="Test Webhook", command=self.test_webhook).pack(side=tk.LEFT, padx=(0, 10))
		ttk.Button(button_frame, text="Install Browsers", command=self.install_browsers).pack(side=tk.LEFT)
	
	def setup_control_tab(self):
		"""Setup server control tab"""
		
		# Server status frame
		status_frame = ttk.LabelFrame(self.control_frame, text="Server Status", padding=10)
		status_frame.pack(fill=tk.X, padx=10, pady=10)
		
		self.status_label = ttk.Label(status_frame, text="Server is currently stopped", foreground="red")
		self.status_label.pack(pady=5)
		
		self.server_url_label = ttk.Label(status_frame, text="Server URL: Not running")
		self.server_url_label.pack(pady=2)
		
		# Control buttons frame
		control_frame = ttk.LabelFrame(self.control_frame, text="Server Controls", padding=10)
		control_frame.pack(fill=tk.X, padx=10, pady=10)
		
		button_frame = ttk.Frame(control_frame)
		button_frame.pack()
		
		self.start_button = ttk.Button(button_frame, text="Start Server", command=self.start_server, state=tk.NORMAL)
		self.start_button.pack(side=tk.LEFT, padx=(0, 10))
		
		self.stop_button = ttk.Button(button_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
		self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
		
		self.restart_button = ttk.Button(button_frame, text="Restart Server", command=self.restart_server, state=tk.DISABLED)
		self.restart_button.pack(side=tk.LEFT)
		
		# Quick actions frame
		actions_frame = ttk.LabelFrame(self.control_frame, text="Quick Actions", padding=10)
		actions_frame.pack(fill=tk.X, padx=10, pady=10)
		
		ttk.Button(actions_frame, text="Open Server in Browser", command=self.open_server_browser).pack(side=tk.LEFT, padx=(0, 10))
		ttk.Button(actions_frame, text="Copy Server URL", command=self.copy_server_url).pack(side=tk.LEFT, padx=(0, 10))
		ttk.Button(actions_frame, text="View Health Check", command=self.view_health_check).pack(side=tk.LEFT)
		
		# Server info frame
		info_frame = ttk.LabelFrame(self.control_frame, text="Server Information", padding=10)
		info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
		
		self.info_text = scrolledtext.ScrolledText(info_frame, height=8, wrap=tk.WORD)
		self.info_text.pack(fill=tk.BOTH, expand=True)
		
		# Add server info
		self.update_server_info()
	
	def setup_logs_tab(self):
		"""Setup logs tab"""
		
		# Log controls frame
		controls_frame = ttk.Frame(self.logs_frame)
		controls_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
		
		ttk.Button(controls_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 10))
		ttk.Button(controls_frame, text="Export Logs", command=self.export_logs).pack(side=tk.LEFT, padx=(0, 10))
		
		# Auto-scroll checkbox
		self.auto_scroll = tk.BooleanVar(value=True)
		ttk.Checkbutton(controls_frame, text="Auto-scroll", variable=self.auto_scroll).pack(side=tk.LEFT, padx=(20, 0))
		
		# Log display
		log_frame = ttk.LabelFrame(self.logs_frame, text="Server Logs", padding=5)
		log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
		
		self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
		self.log_text.pack(fill=tk.BOTH, expand=True)
		
		# Add initial message
		self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Google Maps Scraper GUI started\n")
		self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Configure settings and start the server\n\n")
	
	def setup_logging(self):
		"""Setup logging to capture server logs"""
		
		# Create custom handler that puts logs in queue
		class QueueHandler(logging.Handler):
			def __init__(self, log_queue):
				super().__init__()
				self.log_queue = log_queue
			
			def emit(self, record):
				self.log_queue.put(record)
		
		# Setup logging
		logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		
		# Add our queue handler to root logger
		queue_handler = QueueHandler(self.log_queue)
		logging.getLogger().addHandler(queue_handler)
	
	def process_log_queue(self):
		"""Process log messages from queue and display in GUI"""
		
		try:
			while True:
				record = self.log_queue.get_nowait()
				message = f"[{record.levelname}] {record.getMessage()}\n"
				
				self.log_text.insert(tk.END, message)
				
				# Auto-scroll to bottom if enabled
				if self.auto_scroll.get():
					self.log_text.see(tk.END)
				
				# Limit log size (keep last 1000 lines)
				lines = int(self.log_text.index('end-1c').split('.')[0])
				if lines > 1000:
					self.log_text.delete('1.0', '100.0')
				
		except queue.Empty:
			pass
		
		# Schedule next check
		self.root.after(100, self.process_log_queue)
	
	def load_config(self) -> Dict[str, Any]:
		"""Load configuration from file"""
		
		default_config = {
			"supabase_url": "",
			"supabase_key": "",
			"admin_id": "",
			"server_host": "0.0.0.0",
			"server_port": "5000",
			"n8n_webhookC": "http://localhost:5678/webhook/job-completion",
			"n8n_webhookT": "http://localhost:5678/webhook/webhook-test-connection",
			"max_results": "5"
		}
		
		if os.path.exists(self.config_file):
			try:
				with open(self.config_file, 'r') as f:
					saved_config = json.load(f)
					default_config.update(saved_config)
			except Exception as e:
				logging.error(f"Failed to load config: {e}")
		
		return default_config
	
	def load_saved_config(self):
		"""Load saved configuration into GUI fields"""
		
		self.supabase_url.insert(0, self.config.get("supabase_url", ""))
		self.supabase_key.insert(0, self.config.get("supabase_key", ""))
		self.admin_id.insert(0, self.config.get("admin_id", ""))
		self.server_host.insert(0, self.config.get("server_host", "0.0.0.0"))
		self.server_port.insert(0, self.config.get("server_port", "5000"))
		self.n8n_webhookC.insert(0, self.config.get("n8n_webhookC", "http://localhost:5678/webhook/job-completion"))
		self.n8n_webhookT.insert(0, self.config.get("n8n_webhookT", "http://localhost:5678/webhook/webhook-test-connection"))
		self.max_results.insert(0, self.config.get("max_results", "5"))
	
	def save_config(self):
		"""Save configuration"""
		
		self.config = {
			"supabase_url": self.supabase_url.get().strip(),
			"supabase_key": self.supabase_key.get().strip(),
			"admin_id": self.admin_id.get().strip(),
			"server_host": self.server_host.get().strip(),
			"server_port": self.server_port.get().strip(),
			"n8n_webhookC": self.n8n_webhookC.get().strip(),
			"n8n_webhookT": self.n8n_webhookT.get().strip(),
			"max_results": self.max_results.get().strip()
		}
		
		# Validate configuration
		if not self.validate_config():
			return
		
		# Save to file
		try:
			with open(self.config_file, 'w') as f:
				json.dump(self.config, f, indent=2)
			
			# Update environment variables
			self.update_environment()
			
			messagebox.showinfo("Success", "Configuration saved successfully!")
			logging.info("Configuration saved successfully")
			
		except Exception as e:
			messagebox.showerror("Error", f"Failed to save configuration: {e}")
			logging.error(f"Failed to save configuration: {e}")
	
	def validate_config(self) -> bool:
		"""Validate configuration"""
		
		if not self.config["supabase_url"]:
			messagebox.showerror("Validation Error", "Supabase URL is required")
			return False
		
		if not self.config["supabase_key"]:
			messagebox.showerror("Validation Error", "Supabase API Key is required")
			return False
		
		if not self.config["admin_id"]:
			messagebox.showerror("Validation Error", "Admin ID is required")
			return False
		
		try:
			int(self.config["server_port"])
		except ValueError:
			messagebox.showerror("Validation Error", "Server port must be a number")
			return False
		
		try:
			int(self.config["max_results"])
		except ValueError:
			messagebox.showerror("Validation Error", "Max results must be a number")
			return False
		
		return True
	
	def update_environment(self):
		"""Update environment variables from config"""
		
		os.environ["SUPABASE_URL"] = self.config["supabase_url"]
		os.environ["SUPABASE_ANON_KEY"] = self.config["supabase_key"]
		os.environ["ADMIN_ID"] = self.config["admin_id"]
		os.environ["SERVER_HOST"] = self.config["server_host"]
		os.environ["SERVER_PORT"] = self.config["server_port"]
		os.environ["N8N_WEBHOOK_C"] = self.config["n8n_webhookC"]
		os.environ["N8N_WEBHOOK_T"] = self.config["n8n_webhookT"]
		os.environ["DEFAULT_MAX_RESULTS"] = self.config["max_results"]
		os.environ["CACHE_TTL_MINUTES"] = "0"  # Always disable caching for job processing
	
	def test_database(self):
		"""Test database connection"""
		
		if not self.validate_config():
			return
		
		self.update_environment()
		
		try:
			db_manager = DatabaseManager()
			db_manager.mark_admin_active()
			messagebox.showinfo("Success", "Database connection successful!")
			logging.info("Database connection test successful")
		except Exception as e:
			messagebox.showerror("Database Error", f"Database connection failed: {e}")
			logging.error(f"Database connection test failed: {e}")
	
	def test_webhook(self):
		"""Test webhook connection"""
		
		if not self.validate_config():
			return
		
		self.update_environment()
		
		try:
			webhook_handler = WebhookHandler()
			success = webhook_handler.test_webhook_connection()
			if success:
				messagebox.showinfo("Success", "Webhook connection successful!")
				logging.info("Webhook connection test successful")
			else:
				messagebox.showerror("Webhook Error", "Webhook connection failed - check N8N server")
				logging.error("Webhook connection test failed")
		except Exception as e:
			messagebox.showerror("Webhook Error", f"Webhook test failed: {e}")
			logging.error(f"Webhook test failed: {e}")
	
	def install_browsers(self):
		"""Install Playwright browsers using official method with real-time progress"""
		
		# Check if browsers are already available (bundled or persistent)
		status = get_persistent_browser_status()
		if status["available"]:
			messagebox.showinfo("Browsers", f"Browsers are already available and working!\n\nLocation: {status['location']}")
			return
		
		# Show installation dialog
		result = messagebox.askquestion(
			"Browser Installation",
			"This will download Chromium browser (~127MB) using the official Playwright installer.\n\nThis may take 5-10 minutes depending on your internet connection. Continue?",
			icon='question'
		)
		
		if result != 'yes':
			return
		
		# Show progress dialog with real-time updates
		progress_window = tk.Toplevel(self.root)
		progress_window.title("Installing Browsers")
		progress_window.geometry("500x220")
		progress_window.transient(self.root)
		progress_window.grab_set()
		progress_window.resizable(False, False)
		
		# Center the window
		progress_window.geometry("+%d+%d" % (
			self.root.winfo_rootx() + 50,
			self.root.winfo_rooty() + 50
		))
		
		# Main label
		main_label = ttk.Label(progress_window, text="Installing Playwright Chromium browser...", 
							  font=('TkDefaultFont', 10, 'bold'))
		main_label.pack(pady=20)
		
		# Progress bar (determinate mode for real progress)
		progress_var = tk.DoubleVar()
		progress_bar = ttk.Progressbar(progress_window, variable=progress_var, 
									 maximum=100, mode='determinate')
		progress_bar.pack(pady=10, padx=20, fill=tk.X)
		
		# Status label for detailed updates
		status_label = ttk.Label(progress_window, text="Preparing installation...", 
							   wraplength=450, justify='center')
		status_label.pack(pady=10, padx=20)
		
		# Progress percentage label
		percent_label = ttk.Label(progress_window, text="0%", font=('TkDefaultFont', 9))
		percent_label.pack(pady=5)
		
		# Cancel button (initially disabled during critical phases)
		cancel_button = ttk.Button(progress_window, text="Cancel", state='disabled')
		cancel_button.pack(pady=10)
		
		# Variables for thread communication
		installation_cancelled = threading.Event()
		
		def update_progress(message, progress):
			"""Update progress bar and status in UI thread"""
			def update_ui():
				if progress >= 0:
					progress_var.set(progress)
					percent_label.config(text=f"{int(progress)}%")
					status_label.config(text=message)
					
					# Enable cancel button only during non-critical phases
					if progress < 70 and not installation_cancelled.is_set():
						cancel_button.config(state='normal')
					else:
						cancel_button.config(state='disabled')
				else:
					# Error case
					status_label.config(text=message, foreground='red')
					cancel_button.config(text="Close", state='normal')
				
				progress_window.update()
			
			if not installation_cancelled.is_set():
				self.root.after(0, update_ui)
		
		def cancel_installation():
			"""Cancel the installation process"""
			if not installation_cancelled.is_set():
				installation_cancelled.set()
				progress_window.destroy()
		
		cancel_button.config(command=cancel_installation)
		
		def install_in_thread():
			"""Run installation in background thread with progress updates"""
			try:
				success = install_playwright_browsers(progress_callback=update_progress)
				if not installation_cancelled.is_set():
					self.root.after(0, lambda: installation_complete(success, None))
			except Exception as e:
				if not installation_cancelled.is_set():
					self.root.after(0, lambda: installation_complete(False, str(e)))
		
		def installation_complete(success, error_msg):
			"""Handle installation completion"""
			if installation_cancelled.is_set():
				return
				
			try:
				progress_window.destroy()
			except:
				pass  # Window might already be destroyed
			
			if success:
				messagebox.showinfo("Success", "Browsers installed successfully!\n\nYou can now start the server and begin scraping.")
				logging.info("Playwright browsers installed successfully")
			else:
				error_text = f"Browser installation failed: {error_msg}" if error_msg else "Browser installation failed"
				messagebox.showerror("Installation Failed", error_text)
				logging.error(f"Browser installation failed: {error_msg}")
		
		# Start installation in background thread
		install_thread = threading.Thread(target=install_in_thread, daemon=True)
		install_thread.start()
	
	def start_server(self):
		"""Start the scraper server"""
		
		if not self.validate_config():
			messagebox.showerror("Configuration Error", "Please configure and save settings first")
			return
		
		if self.is_server_running:
			messagebox.showwarning("Server Warning", "Server is already running")
			return
		
		# Check if browsers are available using the persistent manager
		status = get_persistent_browser_status()
		browsers_available = status["available"]
		
		if not browsers_available:
			if status["bundled_found"] and not status["persistent_found"]:
				message = f"Bundled browsers found but not accessible.\n\nStatus: {status['status']}\n\nWould you like to install/setup browsers now?"
			else:
				message = f"Browsers are required for scraping but not available.\n\nStatus: {status['status']}\n\nWould you like to install them now?"
				
			result = messagebox.askquestion(
				"Browsers Required",
				message,
				icon='question'
			)
			if result == 'yes':
				self.install_browsers()
			return
		
		self.update_environment()
		# Mark admin active when starting the server
		try:
			db_manager = DatabaseManager()
			db_manager.mark_admin_active()
		except Exception as e:
			logging.warning(f"Failed to mark admin active on start: {e}")
		
		def run_server():
			try:
				self.server = ProductionServer()
				host = self.config["server_host"]
				port = int(self.config["server_port"])
				self.server.run(host=host, port=port)
			except Exception as e:
				logging.error(f"Server error: {e}")
				self.root.after(0, lambda: self.server_stopped_callback(str(e)))
		
		# Start server in separate thread
		self.server_thread = threading.Thread(target=run_server, daemon=True)
		self.server_thread.start()
		
		# Update UI
		self.is_server_running = True
		self.update_server_status()
		self.update_server_info()
		
		logging.info("Server starting...")
	
	def stop_server(self):
		"""Stop the scraper server"""
		
		if not self.is_server_running:
			messagebox.showwarning("Server Warning", "Server is not running")
			return
		
		# Note: Flask development server doesn't have a clean shutdown method
		# In a production setup, you'd want to use a proper WSGI server
		logging.warning("Server stop requested - restart the application to fully stop the server")
		messagebox.showinfo("Server Stop", "To fully stop the server, please restart the application.")
		
		# Mark admin inactive when stopping the server
		try:
			db_manager = DatabaseManager()
			db_manager.mark_admin_inactive()
		except Exception as e:
			logging.warning(f"Failed to mark admin inactive on stop: {e}")
		self.is_server_running = False
		self.update_server_status()
	
	def restart_server(self):
		"""Restart the scraper server"""
		
		self.stop_server()
		self.root.after(2000, self.start_server)  # Wait 2 seconds before restart
	
	def server_stopped_callback(self, error_msg):
		"""Callback when server stops unexpectedly"""
		
		# Mark admin inactive on unexpected stop
		try:
			db_manager = DatabaseManager()
			db_manager.mark_admin_inactive()
		except Exception as e:
			logging.warning(f"Failed to mark admin inactive on crash: {e}")
		self.is_server_running = False
		self.update_server_status()
		messagebox.showerror("Server Error", f"Server stopped unexpectedly: {error_msg}")
	
	def update_server_status(self):
		"""Update server status display"""
		
		if self.is_server_running:
			self.status_label.config(text="Server is running", foreground="green")
			self.status_bar.config(text="Server Status: Running")
			server_url = f"http://{self.config['server_host']}:{self.config['server_port']}"
			self.server_url_label.config(text=f"Server URL: {server_url}")
			
			self.start_button.config(state=tk.DISABLED)
			self.stop_button.config(state=tk.NORMAL)
			self.restart_button.config(state=tk.NORMAL)
		else:
			self.status_label.config(text="Server is stopped", foreground="red")
			self.status_bar.config(text="Server Status: Stopped")
			self.server_url_label.config(text="Server URL: Not running")
			
			self.start_button.config(state=tk.NORMAL)
			self.stop_button.config(state=tk.DISABLED)
			self.restart_button.config(state=tk.DISABLED)
	
	def update_server_info(self):
		"""Update server information display"""
		
		info = f"""Google Maps Scraper Server - Admin Panel

Version: 6.1.0 - N8N Integration with GUI
Author: Advanced Scraping Solutions

Current Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Database Settings:
• Supabase URL: {self.config.get('supabase_url', 'Not configured')[:50]}...
• Admin ID: {self.config.get('admin_id', 'Not configured')}

Server Settings:
• Host: {self.config.get('server_host', 'Not configured')}
• Port: {self.config.get('server_port', 'Not configured')}
• Max Results: {self.config.get('max_results', 'Not configured')}

N8N Integration:
• Webhook URL: {self.config.get('n8n_webhook', 'Not configured')}

Available Endpoints:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• GET  /health - Health check with integration status
• POST /scrape-single - N8N job processing endpoint  
• POST /test-webhook - Test webhook connection

Features:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ N8N Workflow Integration
✅ Database-driven Job Processing
✅ Webhook Completion Notifications  
✅ Dynamic Scroll Container Detection
✅ Viewport-Based Auto-Scroll
✅ Two-Phase Extraction (List + Detail)
✅ Enhanced Error Handling & Retry Logic
✅ Regex-Based Data Parsing
✅ GUI Configuration Management
✅ Real-time Log Monitoring

Usage Instructions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Configure your database and N8N settings in the Configuration tab
2. Test your connections to ensure everything is working
3. Start the server from the Server Control tab
4. Copy the server URL and use it in your N8N workflow
5. Monitor server activity in the Server Logs tab

Support: For technical support and updates, contact your system administrator.
"""
		
		self.info_text.delete(1.0, tk.END)
		self.info_text.insert(1.0, info)
	
	def open_server_browser(self):
		"""Open server health check in browser"""
		
		if not self.is_server_running:
			messagebox.showwarning("Server Warning", "Server is not running")
			return
		
		url = f"http://{self.config['server_host']}:{self.config['server_port']}/health"
		if self.config['server_host'] == '0.0.0.0':
			url = f"http://localhost:{self.config['server_port']}/health"
		
		webbrowser.open(url)
	
	def copy_server_url(self):
		"""Copy server URL to clipboard"""
		
		if not self.is_server_running:
			messagebox.showwarning("Server Warning", "Server is not running")
			return
		
		url = f"http://{self.config['server_host']}:{self.config['server_port']}"
		if self.config['server_host'] == '0.0.0.0':
			url = f"http://localhost:{self.config['server_port']}"
		
		self.root.clipboard_clear()
		self.root.clipboard_append(url)
		messagebox.showinfo("Copied", f"Server URL copied to clipboard:\n{url}")
	
	def view_health_check(self):
		"""Show health check information"""
		
		if not self.is_server_running:
			messagebox.showwarning("Server Warning", "Server is not running")
			return
		
		try:
			import requests
			url = f"http://localhost:{self.config['server_port']}/health"
			response = requests.get(url, timeout=5)
			health_data = response.json()
			
			# Format health data
			health_info = f"""Server Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: {health_data.get('status', 'Unknown')}
Service: {health_data.get('service', 'Unknown')}
Version: {health_data.get('version', 'Unknown')}
Timestamp: {health_data.get('timestamp', 'Unknown')}

Database Connected: {health_data.get('database_connected', 'Unknown')}
Webhook Configured: {health_data.get('webhook_configured', 'Unknown')}
Admin ID: {health_data.get('admin_id', 'Unknown')}

Features:
{chr(10).join(['• ' + feature for feature in health_data.get('features', [])])}
"""
			
			# Show in new window
			health_window = tk.Toplevel(self.root)
			health_window.title("Server Health Check")
			health_window.geometry("600x500")
			
			health_text = scrolledtext.ScrolledText(health_window, wrap=tk.WORD, font=("Consolas", 10))
			health_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
			health_text.insert(1.0, health_info)
			health_text.config(state=tk.DISABLED)
			
		except Exception as e:
			messagebox.showerror("Health Check Error", f"Failed to get health check: {e}")
	
	def clear_logs(self):
		"""Clear log display"""
		
		self.log_text.delete(1.0, tk.END)
		self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Logs cleared\n")
	
	def export_logs(self):
		"""Export logs to file"""
		
		from tkinter import filedialog
		
		filename = filedialog.asksaveasfilename(
			defaultextension=".txt",
			filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
			title="Save logs as..."
		)
		
		if filename:
			try:
				with open(filename, 'w') as f:
					f.write(self.log_text.get(1.0, tk.END))
				messagebox.showinfo("Success", f"Logs exported to {filename}")
			except Exception as e:
				messagebox.showerror("Export Error", f"Failed to export logs: {e}")
	
	def on_closing(self):
		"""Handle window closing"""
		
		# Attempt to mark admin inactive on GUI close
		try:
			db_manager = DatabaseManager()
			db_manager.mark_admin_inactive()
		except Exception as e:
			logging.warning(f"Failed to mark admin inactive on close: {e}")
		if self.is_server_running:
			if messagebox.askokcancel("Quit", "Server is running. Do you want to quit anyway?"):
				self.root.destroy()
		else:
			self.root.destroy()
	
	def run(self):
		"""Run the GUI application"""
		
		self.root.mainloop()


def main():
	"""Main entry point"""
	
	try:
		app = ScraperGUI()
		app.run()
	except Exception as e:
		print(f"Application error: {e}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	main()