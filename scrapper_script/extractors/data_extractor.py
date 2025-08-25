#!/usr/bin/env python3
"""
Enhanced data extractor with refined selectors and validation
"""

import re
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse
from playwright.async_api import Page
import phonenumbers
from config import OptimizedSelectorsConfig

logger = logging.getLogger(__name__)

class OptimizedDataExtractor:
    """Enhanced data extractor with refined selectors and validation"""
    
    def __init__(self, config: OptimizedSelectorsConfig):
        self.config = config
    
    async def extract_business_data_two_phase(self, page: Page, card_element, search_term: str) -> Dict[str, Any]:
        """Two-phase extraction: list view + detail pane"""
        business = {}
        
        try:
            # Phase 1: Extract basic data from list view
            business['name'] = await self._extract_list_name(card_element)
            if not business['name']:
                return {"error": "No business name found"}
            
            list_rating_text = await self._extract_list_rating_text(card_element)
            if list_rating_text:
                business['rating'] = self._parse_rating_value(list_rating_text)
                business['review_count'] = self._parse_review_count(list_rating_text)
            
            # Phase 2: Click into detail pane for complete data
            detail_data = await self._extract_detail_data_with_retry(page, card_element)
            if detail_data and not detail_data.get('error'):
                business.update(detail_data)
            else:
                # If detail extraction failed, note it but keep list data
                if detail_data and detail_data.get('error'):
                    business['extraction_notes'] = f"Detail extraction failed: {detail_data['error']}"
            
            # Add inferred category if not found
            if not business.get('category'):
                business['category'] = self._infer_category(search_term)
            
            return business
            
        except Exception as e:
            logger.warning(f"Business extraction failed: {e}")
            return {"error": f"Extraction failed: {str(e)}"}
    
    async def _extract_list_name(self, card_element) -> str:
        """Extract name from list view"""
        try:
            name_element = await card_element.query_selector(self.config.selectors["list_name"])
            if name_element:
                name = await name_element.inner_text()
                return name.strip() if name else ""
        except:
            pass
        return ""
    
    async def _extract_list_rating_text(self, card_element) -> str:
        """Extract full rating text from list view (contains both rating and count)"""
        try:
            rating_element = await card_element.query_selector(self.config.selectors["list_rating"])
            if rating_element:
                # Try aria-label first (more reliable)
                aria_label = await rating_element.get_attribute('aria-label')
                if aria_label:
                    return aria_label
                
                # Fallback to text content
                text = await rating_element.inner_text()
                return text if text else ""
        except:
            pass
        return ""
    
    def _parse_rating_value(self, rating_text: str) -> Optional[float]:
        """Parse numeric rating from text using regex"""
        if not rating_text:
            return None
        
        try:
            match = re.search(self.config.patterns["rating_value"], rating_text)
            if match:
                rating = float(match.group(1))
                if 0 <= rating <= 5:
                    return rating
        except:
            pass
        return None
    
    def _parse_review_count(self, rating_text: str) -> Optional[int]:
        """Parse review count from text using regex"""
        if not rating_text:
            return None
        
        try:
            match = re.search(self.config.patterns["review_count"], rating_text)
            if match:
                count_str = match.group(1).replace(',', '')
                return int(count_str)
        except:
            pass
        return None
    
    async def _extract_detail_data_with_retry(self, page: Page, card_element, max_retries: int = 2) -> Dict[str, Any]:
        """Extract detail data with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                return await self._extract_detail_data(page, card_element)
            except Exception as e:
                logger.warning(f"Detail extraction attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    # Try to close any open panes and wait before retry
                    await self._force_close_detail_pane(page)
                    await asyncio.sleep(2.0)
                else:
                    return {"error": f"All {max_retries + 1} attempts failed: {str(e)}"}
        
        return {"error": "Unexpected retry failure"}
    
    async def _extract_detail_data(self, page: Page, card_element) -> Dict[str, Any]:
        """Extract data from detail pane"""
        detail_data = {}
        
        # Find and click the detail link
        link_element = await card_element.query_selector(self.config.selectors["card_link"])
        if not link_element:
            return {"error": "No detail link found"}
        
        # Click to open detail pane
        await link_element.click()
        
        # Wait for detail pane to load using multiple strategies
        loaded = await self._wait_for_detail_pane(page)
        if not loaded:
            await self._force_close_detail_pane(page)
            return {"error": "Detail pane load timeout"}
        
        # Extract all detail fields
        detail_data['address'] = await self._extract_detail_address(page)
        detail_data['phone'] = await self._extract_detail_phone(page)
        detail_data['website'] = await self._extract_detail_website(page)
        detail_data['category'] = await self._extract_detail_category(page)
        
        # Extract coordinates
        lat, lng = await self._extract_coordinates(page)
        detail_data['latitude'] = lat
        detail_data['longitude'] = lng
        
        # Update rating from detail pane (often more accurate)
        detail_rating_text = await self._extract_detail_rating_text(page)
        if detail_rating_text:
            detail_rating = self._parse_rating_value(detail_rating_text)
            if detail_rating:
                detail_data['rating'] = detail_rating
        
        # Close detail pane
        await self._close_detail_pane(page)
        
        return detail_data
    
    async def _wait_for_detail_pane(self, page: Page, timeout: int = 8000) -> bool:
        """Wait for detail pane to load with fallback strategies"""
        try:
            # Primary: wait for address element
            await page.wait_for_selector(self.config.selectors["detail_address"], timeout=timeout)
            await asyncio.sleep(1.5)  # Additional wait for content rendering
            return True
        except:
            try:
                # Fallback: wait for any detail selector
                await page.wait_for_selector(self.config.selectors["detail_name"], timeout=3000)
                await asyncio.sleep(1.0)
                return True
            except:
                logger.debug("Detail pane load timeout")
                return False
    
    async def _extract_detail_address(self, page: Page) -> str:
        """Extract address from detail pane"""
        try:
            address_element = await page.query_selector(self.config.selectors["detail_address"])
            if address_element:
                address = await address_element.inner_text()
                if address and len(address.strip()) > 10:
                    return address.strip()
        except:
            pass
        return ""
    
    async def _extract_detail_phone(self, page: Page) -> str:
        """Extract phone from detail pane"""
        try:
            # Try multiple strategies for phone extraction
            phone_selectors = [
                "[href^='tel:']",
                ".fontBodyMedium a[href^='tel:']",
                ".fontBodyMedium"
            ]
            
            for selector in phone_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        # Try href first (tel: links)
                        href = await element.get_attribute('href')
                        if href and href.startswith('tel:'):
                            phone = href[4:]  # Remove 'tel:' prefix
                            if self._is_valid_phone(phone):
                                return self._format_phone(phone)
                        
                        # Try text content
                        text = await element.inner_text()
                        if text and self._is_valid_phone(text):
                            return self._format_phone(text)
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Phone extraction failed: {e}")
        
        return ""
    
    async def _extract_detail_website(self, page: Page) -> str:
        """Extract website from detail pane"""
        try:
            # Try multiple strategies for website extraction
            website_selectors = [
                "a[data-value='Website']",
                "a[href^='http']:not([href*='maps.google'])",
                ".fontBodyMedium a[href^='http']",
                ".fontBodyMedium a[href^='https']"
            ]
            
            for selector in website_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        href = await element.get_attribute('href')
                        if href and self._is_valid_website(href):
                            return href
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Website extraction failed: {e}")
        
        return ""
    
    async def _extract_detail_category(self, page: Page) -> str:
        """Extract category from detail pane with filtering"""
        try:
            # Try multiple strategies for category extraction
            category_selectors = [
                "button.DkEaL",
                ".W4Efsd",
                ".YhemCb",
                ".fontBodyMedium button"
            ]
            
            for selector in category_selectors:
                try:
                    category_elements = await page.query_selector_all(selector)
                    for element in category_elements:
                        category = await element.inner_text()
                        if category and self._is_valid_category(category):
                            return category.strip()
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Category extraction failed: {e}")
        
        return ""
    
    async def _extract_detail_rating_text(self, page: Page) -> str:
        """Extract rating text from detail pane"""
        try:
            rating_element = await page.query_selector(self.config.selectors["detail_rating"])
            if rating_element:
                aria_label = await rating_element.get_attribute('aria-label')
                if aria_label:
                    return aria_label
                return await rating_element.inner_text()
        except:
            pass
        return ""
    
    async def _extract_coordinates(self, page: Page) -> Tuple[Optional[float], Optional[float]]:
        """Extract coordinates using regex patterns"""
        try:
            links = await page.query_selector_all('a[href]')
            
            for link in links:
                href = await link.get_attribute('href')
                if href and ('google.com/maps' in href or 'maps' in href):
                    # Try pattern 1: !3d31.4802937!4d74.3837626
                    match = re.search(self.config.patterns["coordinates_3d4d"], href)
                    if match:
                        lat, lng = float(match.group(1)), float(match.group(2))
                        if self._validate_coordinates(lat, lng):
                            return lat, lng
                    
                    # Try pattern 2: @31.4802937,74.3837626,15z
                    match = re.search(self.config.patterns["coordinates_at"], href)
                    if match:
                        lat, lng = float(match.group(1)), float(match.group(2))
                        if self._validate_coordinates(lat, lng):
                            return lat, lng
            
            return None, None
            
        except:
            return None, None
    
    async def _close_detail_pane(self, page: Page):
        """Close detail pane gracefully"""
        try:
            # Try close button first
            close_button = await page.query_selector(self.config.selectors["close_detail"])
            if close_button:
                await close_button.click()
                await asyncio.sleep(1.0)
                return
            
            # Fallback: Escape key
            await page.keyboard.press('Escape')
            await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.debug(f"Close detail pane failed: {e}")
    
    async def _force_close_detail_pane(self, page: Page):
        """Force close detail pane (for error recovery)"""
        try:
            # Try multiple strategies
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # Click outside the detail pane
            await page.click('body', position={'x': 100, 'y': 100})
            await asyncio.sleep(0.5)
            
        except:
            pass
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone number - improved for Pakistani numbers"""
        if not phone:
            return False
        
        # Clean the phone number
        digits = re.sub(r'[^\d\+]', '', phone)
        
        # Pakistani phone number patterns
        if digits.startswith('+92'):
            # +92 format: should have 13 digits total (+92XXXXXXXXXX)
            return len(digits) >= 12
        elif digits.startswith('92'):
            # 92 format: should have 12 digits total (92XXXXXXXXXX)
            return len(digits) >= 11
        elif digits.startswith('03'):
            # Mobile format: 03XX-XXXXXXX (11 digits)
            return len(digits) == 11
        elif digits.startswith('042'):
            # Lahore landline: 042-XXXXXXX (10 digits)
            return len(digits) >= 10
        else:
            # General validation: at least 10 digits
            return len(digits) >= 10 and len(digits) <= 15
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number"""
        try:
            parsed = phonenumbers.parse(phone, None)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            return phone.strip()
    
    def _is_valid_website(self, url: str) -> bool:
        """Validate website URL"""
        if not url:
            return False
        
        skip_domains = ['google.com', 'maps.google', 'goo.gl']
        if any(domain in url.lower() for domain in skip_domains):
            return False
        
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc)
        except:
            return False
    
    def _is_valid_category(self, category: str) -> bool:
        """Validate category text (filter out rating text)"""
        if not category or len(category) > 100:
            return False
        
        # Filter out rating-like text using regex
        if re.match(r'^\d+\.?\d*\s*\(?\d+\)?', category):
            return False
        
        return True
    
    def _validate_coordinates(self, lat: float, lng: float) -> bool:
        """Validate coordinate ranges"""
        return -90 <= lat <= 90 and -180 <= lng <= 180
    
    def _infer_category(self, search_term: str) -> str:
        """Infer category from search term"""
        search_lower = search_term.lower()
        
        category_mappings = {
            'car rental': 'Car Rental Agency',
            'rent a car': 'Car Rental Agency',
            'restaurant': 'Restaurant',
            'hotel': 'Hotel',
            'pharmacy': 'Pharmacy',
            'hospital': 'Hospital',
            'clinic': 'Medical Clinic',
            'bank': 'Bank',
            'gas station': 'Gas Station',
            'grocery': 'Grocery Store'
        }
        
        for key, value in category_mappings.items():
            if key in search_lower:
                return value
        
        return "Business" 