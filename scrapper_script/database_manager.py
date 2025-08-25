#!/usr/bin/env python3
"""
Database manager for Supabase integration with n8n workflow
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the scraper"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.admin_id = os.getenv('ADMIN_ID', '1')  # Default admin ID (now supports UUID)
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"Database manager initialized for admin ID: {self.admin_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def mark_admin_busy(self, job_id: int) -> bool:
        """Mark admin as busy and update job assignment"""
        try:
            # First check current job status to avoid invalid transitions
            job_check = self.client.table('scrape_jobs').select('status').eq('id', job_id).execute()
            
            if job_check.data and len(job_check.data) > 0:
                current_status = job_check.data[0]['status']
                logger.debug(f"Job {job_id} current status: {current_status}")
                
                # Only update if not already in a final state
                if current_status in ['completed', 'failed']:
                    logger.warning(f"Job {job_id} already in final state: {current_status}")
                    return False
                    
                # Only update if not already running
                if current_status == 'running':
                    logger.info(f"Job {job_id} already running, skipping status update")
                    # Still mark admin as busy
                    admin_response = self.client.table('admins').update({
                        'status': 'busy'
                    }).eq('id', self.admin_id).execute()
                    return admin_response.data is not None
            
            # Update admin status to busy
            admin_response = self.client.table('admins').update({
                'status': 'busy'
            }).eq('id', self.admin_id).execute()
            
            if admin_response.data:
                logger.info(f"Admin {self.admin_id} marked as busy for job {job_id}")
                
                # Update job status to running only if it's pending
                job_response = self.client.table('scrape_jobs').update({
                    'status': 'running',
                    'assigned_to_uuid': self.admin_id,
                    'started_at': datetime.now().isoformat()
                }).eq('id', job_id).eq('status', 'pending').execute()
                
                if job_response.data:
                    logger.info(f"Job {job_id} marked as running")
                    return True
                else:
                    logger.warning(f"Job {job_id} may already be running or completed")
                    return True  # Admin is still marked busy, which is what matters
            else:
                logger.warning(f"Failed to mark admin {self.admin_id} as busy")
                return False
                
        except Exception as e:
            logger.error(f"Error marking admin as busy: {e}")
            return False
    
    def mark_admin_active(self) -> bool:
        """Mark admin as active (available for new jobs)"""
        try:
            response = self.client.table('admins').update({
                'status': 'active'
            }).eq('id', self.admin_id).execute()
            
            if response.data:
                logger.info(f"Admin {self.admin_id} marked as active")
                return True
            else:
                logger.warning(f"Failed to mark admin {self.admin_id} as active")
                return False
                
        except Exception as e:
            logger.error(f"Error marking admin as active: {e}")
            return False

    def mark_admin_inactive(self) -> bool:
        """Mark admin as inactive (not available for new jobs)"""
        try:
            response = self.client.table('admins').update({
                'status': 'inactive'
            }).eq('id', self.admin_id).execute()

            if response.data:
                logger.info(f"Admin {self.admin_id} marked as inactive")
                return True
            else:
                logger.warning(f"Failed to mark admin {self.admin_id} as inactive")
                return False

        except Exception as e:
            logger.error(f"Error marking admin as inactive: {e}")
            return False
    
    def update_job_status(self, job_id: int, status: str, businesses_found: int = 0, 
                         processing_time_seconds: float = 0, completed_at: str = None,
                         error_message: str = None, logs: str = None) -> bool:
        """Update job status and completion details"""
        try:
            # First check current status to avoid invalid transitions
            job_check = self.client.table('scrape_jobs').select('status').eq('id', job_id).execute()
            
            if job_check.data and len(job_check.data) > 0:
                current_status = job_check.data[0]['status']
                logger.debug(f"Job {job_id} current status: {current_status}, updating to: {status}")
                
                # Avoid updating if already in the target status
                if current_status == status:
                    logger.info(f"Job {job_id} already in status: {status}, skipping update")
                    return True
                    
                # Prevent invalid transitions to final states
                if current_status in ['completed', 'failed'] and status in ['completed', 'failed']:
                    logger.warning(f"Job {job_id} already in final state: {current_status}, cannot update to: {status}")
                    return True  # Don't treat this as an error since the job is already done
            
            update_data = {
                'status': status,
                'businesses_found': businesses_found,
                'processing_time_seconds': int(processing_time_seconds)
            }
            
            if completed_at:
                update_data['completed_at'] = completed_at
            
            if error_message:
                update_data['error_message'] = error_message
            
            if logs:
                # Store logs as JSON
                update_data['logs'] = {'extraction_method': logs, 'timestamp': datetime.now().isoformat()}
            
            response = self.client.table('scrape_jobs').update(update_data).eq('id', job_id).execute()
            
            if response.data:
                logger.info(f"Job {job_id} status updated to {status}")
                return True
            else:
                logger.warning(f"Failed to update job {job_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            return False
    
    def store_businesses(self, job_id: int, area_id: int, businesses: List[Dict[str, Any]]) -> bool:
        """Store scraped businesses in the database"""
        try:
            if not businesses:
                logger.warning(f"No businesses to store for job {job_id}")
                return True
            
            # Prepare business records for insertion
            business_records = []
            for i, business in enumerate(businesses):
                try:
                    # Clean and validate business data
                    record = {
                        'area_id': area_id,
                        'scrape_job_id': job_id,
                        'name': business.get('name', '').strip()[:255] if business.get('name') else f'Unknown Business {i+1}',
                        'address': business.get('address', '').strip()[:500] if business.get('address') else None,
                        'phone': business.get('phone', '').strip()[:50] if business.get('phone') else None,
                        'website': business.get('website', '').strip()[:500] if business.get('website') else None,
                        'category': business.get('category', '').strip()[:100] if business.get('category') else None,
                        'rating': self._validate_rating(business.get('rating')),
                        'review_count': self._validate_review_count(business.get('review_count')),
                        'latitude': self._validate_coordinate(business.get('latitude')),
                        'longitude': self._validate_coordinate(business.get('longitude')),
                        'raw_info': business,  # Store complete raw data as JSONB
                        'status': 'new',
                        'contact_status': 'not_contacted',
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    # Only add if we have a valid name
                    if record['name'] and not record['name'].startswith('Unknown Business'):
                        business_records.append(record)
                    elif record['name'].startswith('Unknown Business') and len(business_records) == 0:
                        # Include at least one record even if name is unknown
                        business_records.append(record)
                        
                except Exception as record_error:
                    logger.warning(f"Failed to prepare business record {i+1}: {record_error}")
                    continue
            
            if not business_records:
                logger.warning(f"No valid businesses to store for job {job_id}")
                return True
            
            # Insert businesses in smaller batches to avoid timeout and improve reliability
            batch_size = 10
            total_inserted = 0
            failed_batches = 0
            
            for i in range(0, len(business_records), batch_size):
                batch = business_records[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                try:
                    logger.debug(f"Inserting batch {batch_num} with {len(batch)} businesses for job {job_id}")
                    
                    response = self.client.table('businesses').insert(batch).execute()
                    
                    if response.data:
                        inserted_count = len(response.data)
                        total_inserted += inserted_count
                        logger.info(f"Inserted batch {batch_num} of {inserted_count} businesses for job {job_id}")
                    else:
                        logger.warning(f"Failed to insert batch {batch_num} for job {job_id} - no data returned")
                        failed_batches += 1
                        
                except Exception as batch_error:
                    logger.error(f"Error inserting batch {batch_num} for job {job_id}: {batch_error}")
                    failed_batches += 1
                    continue
            
            success_rate = (total_inserted / len(business_records)) * 100 if business_records else 0
            logger.info(f"Successfully stored {total_inserted}/{len(business_records)} businesses for job {job_id} ({success_rate:.1f}% success rate)")
            
            # Consider it a success if we inserted at least 50% of the businesses
            return total_inserted >= (len(business_records) * 0.5)
            
        except Exception as e:
            logger.error(f"Error storing businesses for job {job_id}: {e}")
            return False
    
    def update_area_last_scraped(self, area_id: int) -> bool:
        """Update the last_scraped_at timestamp for an area"""
        try:
            response = self.client.table('areas').update({
                'last_scraped_at': datetime.now().isoformat()
            }).eq('id', area_id).execute()
            
            if response.data:
                logger.info(f"Area {area_id} last_scraped_at updated")
                return True
            else:
                logger.warning(f"Failed to update area {area_id} last_scraped_at")
                return False
                
        except Exception as e:
            logger.error(f"Error updating area last_scraped_at: {e}")
            return False
    
    def get_admin_info(self) -> Optional[Dict[str, Any]]:
        """Get current admin information"""
        try:
            response = self.client.table('admins').select('*').eq('id', self.admin_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                logger.warning(f"Admin {self.admin_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting admin info: {e}")
            return None
    
    def get_job_details(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job details with area and city information"""
        try:
            response = self.client.table('scrape_jobs').select(
                '*, areas(name, cities(name, countries(name)))'
            ).eq('id', job_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                logger.warning(f"Job {job_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return None
    
    def _validate_rating(self, rating) -> Optional[float]:
        """Validate and clean rating value"""
        if rating is None:
            return None
        
        try:
            rating_float = float(rating)
            if 0 <= rating_float <= 5:
                return rating_float
            else:
                logger.warning(f"Invalid rating value: {rating}")
                return None
        except (ValueError, TypeError):
            return None
    
    def _validate_review_count(self, review_count) -> Optional[int]:
        """Validate and clean review count"""
        if review_count is None:
            return None
        
        try:
            count_int = int(review_count)
            if count_int >= 0:
                return count_int
            else:
                logger.warning(f"Invalid review count: {review_count}")
                return None
        except (ValueError, TypeError):
            return None
    
    def _validate_coordinate(self, coordinate) -> Optional[float]:
        """Validate and clean coordinate value"""
        if coordinate is None:
            return None
        
        try:
            coord_float = float(coordinate)
            # Basic coordinate validation (latitude: -90 to 90, longitude: -180 to 180)
            if -180 <= coord_float <= 180:
                return coord_float
            else:
                logger.warning(f"Invalid coordinate value: {coordinate}")
                return None
        except (ValueError, TypeError):
            return None
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Try to fetch admin info as a connection test
            admin_info = self.get_admin_info()
            return admin_info is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
