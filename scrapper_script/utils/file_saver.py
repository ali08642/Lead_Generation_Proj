#!/usr/bin/env python3
"""
File saving utilities for scraping results
"""

import json
import csv
import os
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class FileSaver:
    """Handles saving scraping results to files"""
    
    @staticmethod
    def save_results_to_json(result: Dict[str, Any], request_type: str):
        """Save scraping results to JSON file"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if request_type == 'single':
                search_term = result.get('search_term', 'unknown')
                area_name = result.get('area_name', 'unknown')
                filename = f"{search_term.replace(' ', '_')}_{area_name.replace(' ', '_')}_{timestamp}.json"
            elif request_type == 'single_error':
                search_term = result.get('search_term', 'unknown')
                area_name = result.get('area_name', 'unknown')
                filename = f"error_{search_term.replace(' ', '_')}_{area_name.replace(' ', '_')}_{timestamp}.json"
            else:  # other error types
                filename = f"error_scrape_{timestamp}.json"
            
            # Save to current directory
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Results saved to: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save results to JSON: {e}")
    
    @staticmethod
    def save_results_to_csv(result: Dict[str, Any], request_type: str):
        """Save scraping results to CSV file"""
        try:
            businesses = result.get('businesses', [])
            
            # Generate appropriate filename prefix
            search_term = result.get('search_term', 'unknown')
            area_name = result.get('area_name', 'unknown')
            success = result.get('success', False)
            prefix = f"{search_term.replace(' ', '_')}_{area_name.replace(' ', '_')}"
            if not success:
                prefix = f"partial_{prefix}"
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.csv"
            
            # Save to current directory
            filepath = os.path.join(os.getcwd(), filename)
            
            if not businesses:
                logger.warning(f"No businesses data to save to CSV for {filename}")
                
                # For error cases, still create an empty CSV with headers
                if not result.get('success', False):
                    fieldnames = ['name', 'address', 'phone', 'website', 'category', 
                                'rating', 'review_count', 'latitude', 'longitude']
                    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                    logger.info(f"✅ Empty CSV with headers saved to: {filepath}")
                
                return
            
            # Define CSV fields
            fieldnames = ['name', 'address', 'phone', 'website', 'category', 
                          'rating', 'review_count', 'latitude', 'longitude']
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for business in businesses:
                    # Clean business data for CSV (remove non-standard fields)
                    clean_business = {}
                    for k in fieldnames:
                        value = business.get(k, '')
                        # Ensure we don't have None values
                        clean_business[k] = '' if value is None else value
                    writer.writerow(clean_business)
            
            logger.info(f"✅ CSV results saved to: {filepath} ({len(businesses)} businesses)")
            
        except Exception as e:
            logger.error(f"Failed to save results to CSV: {e}") 