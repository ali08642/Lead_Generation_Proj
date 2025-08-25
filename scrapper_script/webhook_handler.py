#!/usr/bin/env python3
"""
Webhook handler for n8n integration
"""

import os
import logging
import requests
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handles webhook notifications to n8n workflow"""
    
    def __init__(self):
        self.completion_webhook_url = os.getenv('N8N_WEBHOOK_C')
        self.test_webhook_url = os.getenv('N8N_WEBHOOK_T')
        
        if not self.completion_webhook_url:
            logger.warning("N8N_WEBHOOK_C not set - job completion notifications disabled")
        else:
            logger.info(f"Job completion webhook initialized: {self.completion_webhook_url}")
            
        if not self.test_webhook_url:
            logger.warning("N8N_WEBHOOK_T not set - test webhook disabled")
        else:
            logger.info(f"Test webhook initialized: {self.test_webhook_url}")
    
    def notify_job_completion(self, job_data: Dict[str, Any], success: bool, 
                            businesses_found: int = 0, processing_time: float = 0,
                            error_message: str = None) -> bool:
        """Send job completion notification to n8n webhook"""
        
        if not self.completion_webhook_url:
            logger.debug("Completion webhook URL not configured, skipping notification")
            return False
        
        try:
            payload = {
                'job_id': job_data.get('job_id'),
                'area_id': job_data.get('area_id'),
                'admin_id': job_data.get('admin_id'),
                'keyword': job_data.get('keyword', job_data.get('search_term')),
                'area_name': job_data.get('area_name'),
                'success': success,
                'businesses_found': businesses_found,
                'processing_time': round(processing_time, 2),
                'completed_at': datetime.now().isoformat(),
                'error_message': error_message if not success else None
            }
            
            logger.info(f"Sending webhook notification for job {job_data.get('job_id')}")
            logger.debug(f"Webhook payload: {payload}")
            
            response = requests.post(
                self.completion_webhook_url,
                json=payload,
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()
            logger.info(f"Webhook notification sent successfully for job {job_data.get('job_id')}")
            return True
            
        except requests.exceptions.Timeout:
            logger.error(f"Webhook notification timeout for job {job_data.get('job_id')}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook notification failed for job {job_data.get('job_id')}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook for job {job_data.get('job_id')}: {e}")
            return False
    
    def test_webhook_connection(self) -> bool:
        """Test webhook connection"""
        if not self.test_webhook_url:
            logger.error("Test webhook URL not configured")
            return False
        
        try:
            test_payload = {
                'status_code': 200,
                'message': 'Test successful'
            }
            
            response = requests.post(
                self.test_webhook_url,
                json=test_payload,
                timeout=20,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("Webhook connection test successful")
                return True
            else:
                logger.error(f"Webhook test failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook connection test failed: {e}")
            return False
