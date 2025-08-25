#!/usr/bin/env python3
"""
Configuration and selectors for Google Maps Scraper
"""

import re
from typing import Dict, Any

class OptimizedSelectorsConfig:
    """Refined selectors based on JavaScript testing insights"""
    
    def __init__(self):
        self.selectors = {
            # List view selectors (Phase 1)
            "business_cards": ".Nv2PK",  # All business cards
            "card_link": "a.hfpxzc[href*='/place/']",  # Clickable detail link
            "list_name": ".qBF1Pd, .fontHeadlineSmall",  # Name fallback
            "list_rating": "span[aria-label*='star'], span[role='img'][aria-label*='star']",
            
            # Detail pane selectors (Phase 2) - Updated based on browser analysis
            "detail_name": ".qBF1Pd, .fontHeadlineSmall, .DUwDvf",
            "detail_address": ".Io6YTe.fontBodyMedium.kR99db.fdkmkc",  # MAIN ADDRESS - confirmed working
            "detail_phone": "[href^='tel:'], .fontBodyMedium",  # Updated to match fontBodyMedium
            "detail_website": "a[data-value='Website'], a[href^='http']:not([href*='maps.google']), .fontBodyMedium a[href^='http']",
            "detail_category": "button.DkEaL",  # Updated based on browser analysis
            "detail_rating": "span[aria-label*='star'], span[aria-hidden='true']",
            
            # Container detection
            "potential_containers": [
                "[role='feed']",  # Primary: role="feed" 
                ".m6QErb",        # Backup class patterns
                ".DxyBCb",
                "[aria-label*='Results']"
            ],
            
            # Close/dismiss selectors
            "close_detail": ".widget-pane-dismiss, [data-value='back'], [aria-label*='Back']"
        }
        
        # Regex patterns for data extraction
        self.patterns = {
            "review_count": r'\((\d+(?:,\d+)*)\)',  # Extract from "(122)" or "(1,234)"
            "rating_value": r'(\d+\.?\d*)',         # Extract numeric rating
            "coordinates_3d4d": r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)',  # !3d31.4802937!4d74.3837626
            "coordinates_at": r'@(-?\d+\.?\d*),(-?\d+\.?\d*),',       # @31.4802937,74.3837626,15z
            "phone_digits": r'[^\d\+]',             # For phone cleaning
        }

# Default configuration instance
DEFAULT_CONFIG = OptimizedSelectorsConfig() 