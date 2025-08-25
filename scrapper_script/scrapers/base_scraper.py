#!/usr/bin/env python3
"""
Base scraper class for web scraping operations
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for web scrapers"""
    
    def __init__(self):
        self._initialized = False
    
    @abstractmethod
    async def initialize(self):
        """Initialize the scraper"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up resources"""
        pass
    
    @abstractmethod
    async def scrape(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main scraping method"""
        pass
    
    async def _check_if_blocked(self, page: Page) -> bool:
        """Check if the page is blocking requests"""
        try:
            # Check for common blocking indicators
            blocked_indicators = [
                'text="Our systems have detected unusual traffic"',
                'text="unusual traffic from your computer network"',
                'text="automated requests"',
                '[id*="captcha"]',
                '.g-recaptcha',
                'text="blocked"',
            ]
            
            for indicator in blocked_indicators:
                element = await page.query_selector(indicator)
                if element:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Block detection failed: {e}")
            return False
    
    def _validate_request_data(self, request_data: Dict[str, Any]) -> bool:
        """Validate request data"""
        required_fields = ['search_term', 'area_name']
        for field in required_fields:
            if not request_data.get(field):
                return False
        return True 