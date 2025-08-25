#!/usr/bin/env python3
"""
Production server for optimized scraper with n8n integration
"""

import time
import logging
import os
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from utils.async_manager import AsyncEventLoopManager
from utils.file_saver import FileSaver
from scrapers.google_maps_scraper import OptimizedGoogleMapsScraper
from database_manager import DatabaseManager
from webhook_handler import WebhookHandler

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ProductionServer:
    """Production server for optimized scraper with n8n integration"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.scraper = None
        self.event_loop_manager = AsyncEventLoopManager()
        self.db_manager = DatabaseManager()
        self.webhook_handler = WebhookHandler()
        self._setup_routes()
        self._setup_error_handlers()
        
        # Configuration from environment
        self.DEFAULT_MAX_RESULTS = int(os.getenv('DEFAULT_MAX_RESULTS', 50))
        self.CACHE_TTL_MINUTES = int(os.getenv('CACHE_TTL_MINUTES', 0))
        
        # Disable caching for job processing by default
        self.result_cache = {} if self.CACHE_TTL_MINUTES > 0 else None
        self.CACHE_DURATION = self.CACHE_TTL_MINUTES * 60
        
    def _make_docker_compatible_response(self, data, status_code=200):
        """Create Docker-compatible response with proper headers"""
        response = jsonify(data)
        response.status_code = status_code
        
        # Add headers for Docker networking compatibility
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Connection'] = 'close'  # Force connection close
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return self._make_docker_compatible_response({
                "status": "healthy",
                "service": "Optimized Google Maps Scraper V6 - N8N Integrated",
                "timestamp": datetime.now().isoformat(),
                "version": "6.1.0 - N8N Job Processing Integration",
                "features": [
                    "N8N Workflow Integration",
                    "Database-driven Job Processing", 
                    "Webhook Completion Notifications",
                    "Dynamic Scroll Container Detection",
                    "Viewport-Based Auto-Scroll",
                    "Two-Phase Extraction (List + Detail)",
                    "Enhanced Error Handling & Retry Logic",
                    "Regex-Based Data Parsing"
                ],
                "database_connected": self.db_manager is not None,
                "webhook_configured": self.webhook_handler.completion_webhook_url is not None and self.webhook_handler.test_webhook_url is not None,
                "admin_id": self.db_manager.admin_id if self.db_manager else None
            })
        
        @self.app.route('/scrape-single', methods=['POST', 'OPTIONS'])
        def scrape_single():
            if request.method == 'OPTIONS':
                return self._handle_options_request()
            return self._handle_scrape_single()
        
        @self.app.route('/test-webhook', methods=['POST'])
        def test_webhook():
            """Test webhook connection"""
            success = self.webhook_handler.test_webhook_connection()
            return self._make_docker_compatible_response({
                "webhook_test": "success" if success else "failed",
                "webhook_url": self.webhook_handler.webhook_url,
                "timestamp": datetime.now().isoformat()
            })

    def _handle_options_request(self):
        """Handle CORS preflight OPTIONS requests"""
        response = self._make_docker_compatible_response({"status": "ok"})
        return response
    
    def _handle_scrape_single(self):
        """Handle single scraping request from n8n workflow"""
        start_time = time.time()
        
        try:
            data = request.get_json()
            if not data:
                return self._make_docker_compatible_response({
                    "success": False,
                    "error": "No data provided",
                    "businesses": []
                }, 400)
            
            # Extract job data from n8n payload
            job_id = data.get('job_id')
            area_id = data.get('area_id')
            admin_id = data.get('admin_id')
            search_term = data.get('search_term', data.get('keyword', ''))
            area_name = data.get('area_name', '')
            max_results = data.get('max_results', self.DEFAULT_MAX_RESULTS)
            
            # Validate required fields
            if not all([job_id, area_id, search_term, area_name]):
                return self._make_docker_compatible_response({
                    "success": False,
                    "error": "Missing required fields: job_id, area_id, search_term, area_name",
                    "businesses": []
                }, 400)
            
            logger.info(f"Processing n8n job {job_id}: '{search_term}' in '{area_name}'")
            
            # Step 1: Mark admin as busy
            success = self.db_manager.mark_admin_busy(job_id)
            if not success:
                logger.warning(f"Failed to mark admin as busy for job {job_id}, continuing anyway")
            
            # Step 2: Send immediate response to n8n (prevents timeout)
            response_data = {
                "success": True,
                "job_id": job_id,
                "message": "Job processing started",
                "admin_id": admin_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Step 3: Start background processing (asynchronous - no waiting)
            import threading
            processing_thread = threading.Thread(
                target=self._process_job_in_background,
                args=(data, start_time),
                daemon=True
            )
            processing_thread.start()
            
            # Return immediate response to N8N
            return self._make_docker_compatible_response(response_data)
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Request handling failed: {error_message}")
            
            # Ensure admin is marked as active on any error
            try:
                self.db_manager.mark_admin_active()
            except:
                pass
            
            return self._make_docker_compatible_response({
                "success": False,
                "error": error_message,
                "businesses": []
            }, 500)
    
    def _process_job_in_background(self, data, start_time):
        """Process job in background thread to avoid blocking HTTP response"""
        job_id = data.get('job_id')
        area_id = data.get('area_id')
        
        try:
            # Run async processing in the background
            scraper_result = self.event_loop_manager.run_async(
                self._process_job_async(data),
                timeout=8000.0  # 10 minute timeout for scraping
            )
            
            processing_time = time.time() - start_time
            businesses_found = len(scraper_result.get('businesses', []))
            
            # Store results in database
            if scraper_result.get('success') and businesses_found > 0:
                storage_success = self.db_manager.store_businesses(
                    job_id=job_id,
                    area_id=area_id, 
                    businesses=scraper_result.get('businesses', [])
                )
                
                if storage_success:
                    # Update job as completed
                    self.db_manager.update_job_status(
                        job_id=job_id,
                        status='completed',
                        businesses_found=businesses_found,
                        processing_time_seconds=processing_time,
                        completed_at=datetime.now().isoformat(),
                        logs=scraper_result.get('extraction_method', 'two_phase')
                    )
                    
                    # Update area last scraped
                    self.db_manager.update_area_last_scraped(area_id)
                    
                    logger.info(f"Job {job_id} completed successfully: {businesses_found} businesses found")
                else:
                    # Storage failed but scraping succeeded
                    error_msg = "Business data storage failed"
                    self.db_manager.update_job_status(
                        job_id=job_id,
                        status='failed',
                        error_message=error_msg,
                        businesses_found=0,
                        processing_time_seconds=processing_time,
                        completed_at=datetime.now().isoformat()
                    )
                    
                    logger.error(f"Job {job_id} failed during storage: {error_msg}")
                    scraper_result['success'] = False
                    scraper_result['error'] = error_msg
                    
            else:
                # Update job as failed
                error_msg = scraper_result.get('error', 'No businesses found')
                self.db_manager.update_job_status(
                    job_id=job_id,
                    status='failed',
                    error_message=error_msg,
                    businesses_found=0,
                    processing_time_seconds=processing_time,
                    completed_at=datetime.now().isoformat()
                )
                
                logger.warning(f"Job {job_id} failed: {error_msg}")
            
            # Send webhook notification to n8n
            self.webhook_handler.notify_job_completion(
                job_data=data,
                success=scraper_result.get('success', False),
                businesses_found=businesses_found,
                processing_time=processing_time,
                error_message=scraper_result.get('error') if not scraper_result.get('success') else None
            )
            
        except Exception as processing_error:
            processing_time = time.time() - start_time
            error_message = str(processing_error)
            
            logger.error(f"Job {job_id} processing failed: {error_message}")
            
            # Update job as failed
            self.db_manager.update_job_status(
                job_id=job_id,
                status='failed',
                error_message=error_message,
                businesses_found=0,
                processing_time_seconds=processing_time,
                completed_at=datetime.now().isoformat()
            )
            
            # Send failure webhook
            self.webhook_handler.notify_job_completion(
                job_data=data,
                success=False,
                businesses_found=0,
                processing_time=processing_time,
                error_message=error_message
            )
        
        finally:
            # Always mark admin as active again
            self.db_manager.mark_admin_active()
    
    async def _process_job_async(self, job_data):
        """Process job asynchronously with fresh browser approach"""
        # Create a new scraper for each request to ensure completely fresh state
        scraper = OptimizedGoogleMapsScraper()
        
        try:
            # Prepare scraper request data
            scraper_request = {
                'search_term': job_data.get('search_term', job_data.get('keyword')),
                'area_name': job_data.get('area_name'),
                'max_results': job_data.get('max_results', self.DEFAULT_MAX_RESULTS)
            }
            
            result = await scraper.scrape_single_search(scraper_request)
            
            # Enhance result with job information
            result['job_id'] = job_data.get('job_id')
            result['area_id'] = job_data.get('area_id')
            result['admin_id'] = job_data.get('admin_id')
            
            return result
            
        except Exception as e:
            logger.error(f"Scraper error for job {job_data.get('job_id')}: {str(e)}")
            return {
                "success": False,
                "error": f"Scraper error: {str(e)}",
                "search_term": job_data.get('search_term', job_data.get('keyword', '')),
                "area_name": job_data.get('area_name', ''),
                "businesses": [],
                "job_id": job_data.get('job_id'),
                "area_id": job_data.get('area_id'),
                "admin_id": job_data.get('admin_id'),
                "timestamp": datetime.now().isoformat()
            }
    
    def _setup_error_handlers(self):
        """Setup error handlers"""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return self._make_docker_compatible_response({"error": "Endpoint not found"}, 404)
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return self._make_docker_compatible_response({"error": "Internal server error"}, 500)
    
    def run(self, host='0.0.0.0', port=5000):
        """Run the server"""
        # Get host and port from environment if available
        host = os.getenv('SERVER_HOST', host)
        port = int(os.getenv('SERVER_PORT', port))
        
        logger.info("🚀 Starting Optimized Google Maps Scraper V6 - N8N Integrated...")
        logger.info("🎯 Features: N8N workflow integration + Smart auto-scroll + Two-phase extraction")
        logger.info("� Database: Connected to Supabase")
        logger.info("📡 Webhook: Configured for n8n completion notifications")
        logger.info("� Admin ID: %s", self.db_manager.admin_id)
        
        # Log caching configuration
        if self.result_cache is not None:
            cache_minutes = self.CACHE_DURATION // 60
            logger.info(f"💾 Result caching ENABLED - Results cached for {cache_minutes} minutes")
        else:
            logger.info("💾 Result caching DISABLED - Job processing mode")
        
        logger.info("Available endpoints:")
        logger.info("  GET  /health - Health check with integration status")
        logger.info("  POST /scrape-single - N8N job processing endpoint")
        logger.info("  POST /test-webhook - Test webhook connection")
        
        # Test database and webhook connections on startup
        try:
            logger.info("🔍 Testing database connection...")
            # Mark admin as active on startup
            self.db_manager.mark_admin_active()
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
        
        try:
            logger.info("🔍 Testing webhook connection...")
            webhook_test = self.webhook_handler.test_webhook_connection()
            if webhook_test:
                logger.info("✅ Webhook connection successful")
            else:
                logger.warning("⚠️  Webhook connection test failed")
        except Exception as e:
            logger.error(f"❌ Webhook test failed: {e}")
        
        logger.info(f"🌐 Server starting on {host}:{port}")
        # Configure server timeout via WSGI server to prevent connection drops during long scraping operations
        from werkzeug.serving import WSGIRequestHandler
        WSGIRequestHandler.timeout = 900  # 15 minutes to exceed scraping timeout of 600 seconds
        
        self.app.run(host=host, port=port, debug=False, threaded=True) 