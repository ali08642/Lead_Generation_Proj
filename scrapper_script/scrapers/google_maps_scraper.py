#!/usr/bin/env python3
"""
Optimized Google Maps Scraper with smart auto-scroll and two-phase extraction
"""

import asyncio
import random
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from scrapers.base_scraper import BaseScraper
from browser_manager import EnhancedBrowserPool, BrowserContextManager
from extractors.scroll_manager import SmartScrollManager
from extractors.data_extractor import OptimizedDataExtractor
from config import OptimizedSelectorsConfig

logger = logging.getLogger(__name__)

class OptimizedGoogleMapsScraper(BaseScraper):
    """Optimized scraper with smart auto-scroll and two-phase extraction"""
    
    def __init__(self):
        super().__init__()
        self.browser_pool = EnhancedBrowserPool(pool_size=1)
        self.config = OptimizedSelectorsConfig()
        self.scroll_manager = SmartScrollManager(self.config)
        self.extractor = OptimizedDataExtractor(self.config)
        self._request_count = 0  # Track requests for detection avoidance
        
    async def initialize(self):
        """Initialize the scraper"""
        if not self._initialized:
            await self.browser_pool.initialize()
            self._initialized = True
            logger.info("Optimized Google Maps Scraper V6 initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        if self._initialized:
            await self.browser_pool.cleanup()
            self._initialized = False
            logger.info("Scraper cleaned up")
    
    def build_search_url(self, search_term: str, area_name: str) -> str:
        """Build Google Maps search URL"""
        search_formatted = search_term.replace(' ', '+')
        area_formatted = area_name.replace(' ', '+')
        return f"https://www.google.com/maps/search/{search_formatted}+in+{area_formatted}"
        
    async def _create_fresh_browser(self):
        """Create completely fresh browser instance to avoid detection"""
        try:
            # Create a completely new playwright and browser instance
            playwright = await async_playwright().start()
            
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--window-size=1920,1080'
                ]
            )
            
            logger.info("Created fresh browser instance to avoid detection")
            return browser, playwright
        except Exception as e:
            logger.error(f"Failed to create fresh browser: {e}")
            raise
    
    async def scrape(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main scraping method - alias for scrape_single_search"""
        return await self.scrape_single_search(request_data)
    
    async def scrape_single_search(self, search_request: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced scraping with fresh browser approach"""
        search_term = search_request.get('search_term', '')
        area_name = search_request.get('area_name', '')
        max_results = search_request.get('max_results', 20)
        max_retries = search_request.get('max_retries', 2)
        
        if not search_term or not area_name:
            return {
                "success": False,
                "error": "search_term and area_name are required",
                "businesses": []
            }

        # Always use a completely fresh browser instance for each request
        # This mimics a server restart which helps avoid detection
        browser = None
        playwright = None
        businesses = []
        retry_count = 0
        last_error = None
        
        try:
            # For each retry, use a completely fresh browser
            while retry_count <= max_retries:
                try:
                    if retry_count > 0:
                        logger.info(f"Retry attempt {retry_count}/{max_retries} for: {search_term} in {area_name}")
                        # Wait longer between retries to avoid rate limiting
                        await asyncio.sleep(random.uniform(5.0, 10.0))
                    
                    # Close previous browser if it exists
                    if browser:
                        try:
                            await browser.close()
                            await playwright.stop()
                        except:
                            pass
                    
                    # Create totally fresh browser for this attempt
                    browser, playwright = await self._create_fresh_browser()
                    
                    # Create completely fresh context with randomized settings
                    context = await BrowserContextManager.create_stealth_context(browser)
                    page = await context.new_page()
                    
                    # Add anti-detection measures
                    await BrowserContextManager.apply_stealth_measures(page)
                    
                    # Navigate with random delay
                    url = self.build_search_url(search_term, area_name)
                    logger.info(f"Scraping: {search_term} in {area_name}")
                    
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    
                    # Random wait to mimic human behavior
                    base_wait = 4000 + (retry_count * 1000)
                    random_wait = random.uniform(base_wait * 0.8, base_wait * 1.2)
                    await page.wait_for_timeout(int(random_wait))
                    
                    # Check if we're being blocked
                    is_blocked = await BrowserContextManager.check_if_blocked(page)
                    if is_blocked:
                        logger.warning(f"Detected blocking on attempt {retry_count + 1}")
                        await context.close()
                        if retry_count < max_retries:
                            retry_count += 1
                            continue
                        else:
                            return {
                                "success": False,
                                "error": "Google Maps is blocking requests",
                                "businesses": [],
                                "search_term": search_term,
                                "area_name": area_name,
                                "note": "Rate limited or detected as bot"
                            }
                    
                    # Make scrollManager use this page's container
                    self.scroll_manager.scroll_container = None
                    
                    # Phase 1: Load all cards via auto-scroll
                    total_cards_loaded = await self.scroll_manager.auto_scroll_load_all_cards(page, max_results)
                    logger.info(f"Phase 1 complete: {total_cards_loaded} cards loaded")
                    
                    # If no cards found, implement more aggressive retry strategy
                    if total_cards_loaded == 0:
                        logger.info("No cards found, implementing aggressive retry strategy...")
                        
                        # Strategy 1: Try different search variations
                        search_variations = [
                            f"{search_term} {area_name}",
                            f"{search_term.replace(' ', '+')}+{area_name.replace(' ', '+')}",
                            f"{area_name} {search_term}",
                        ]
                        
                        for variation in search_variations:
                            logger.info(f"Trying search variation: {variation}")
                            variation_url = f"https://www.google.com/maps/search/{variation.replace(' ', '+')}"
                
                            try:
                                await page.goto(variation_url, wait_until='domcontentloaded', timeout=60000)
                                await page.wait_for_timeout(random.uniform(3000, 6000))
                
                                # Try scrolling again
                                self.scroll_manager.scroll_container = None
                                total_cards_loaded = await self.scroll_manager.auto_scroll_load_all_cards(page, max_results)
                                if total_cards_loaded > 0:
                                    logger.info(f"Success with variation: {total_cards_loaded} cards loaded")
                                    break
                            except Exception as e:
                                logger.debug(f"Variation {variation} failed: {e}")
                                continue
                        
                        # If still no results and we have retries left
                        if total_cards_loaded == 0 and retry_count < max_retries:
                            logger.warning(f"No results on attempt {retry_count + 1}, will retry with fresh browser")
                            await context.close()
                            retry_count += 1
                            continue
                        
                        # If this is the final attempt and still no results
                        if total_cards_loaded == 0:
                            await context.close()
                            return {
                                "success": True,
                                "businesses": [],
                                "total_found": 0,
                                "cards_loaded": 0,
                                "search_term": search_term,
                                "area_name": area_name,
                                "extraction_method": "Two-Phase (Scroll + Sequential Detail Extraction)",
                                "note": "No results found after multiple attempts and search variations",
                                "retry_count": retry_count
                            }
            
                    # Phase 2: Extract business details
                    try:
                        businesses = await self._extract_all_cards_sequentially(page, search_term, max_results)
                    except Exception as extraction_error:
                        logger.warning(f"Error during card extraction: {extraction_error}")
                    
                    await context.close()
                    
                    # Success - return results
                    return {
                        "success": True,
                        "businesses": businesses,
                        "total_found": len(businesses),
                        "cards_loaded": total_cards_loaded,
                        "search_term": search_term,
                        "area_name": area_name,
                        "extraction_method": "Two-Phase (Scroll + Sequential Detail Extraction)",
                        "retry_count": retry_count,
                        "fresh_browser": True
                    }
                    
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"Scraping failed (attempt {retry_count + 1}): {e}")
                    
                    try:
                        await context.close()
                    except:
                        pass
                    
                    if retry_count >= max_retries:
                        break
                        
                    retry_count += 1
                    await asyncio.sleep(random.uniform(3.0, 7.0))
            
            # All retries failed
            return {
                "success": False,
                "error": last_error or "All retry attempts failed",
                "businesses": businesses,
                "cards_loaded": len(businesses),
                "search_term": search_term,
                "area_name": area_name,
                "retry_count": retry_count
            }
        
        finally:
            # Always clean up browser instances
            if browser:
                try:
                    await browser.close()
                    if playwright:
                        await playwright.stop()
                except:
                    pass
    
    async def _extract_all_cards_sequentially(self, page: Page, search_term: str, max_results: int) -> List[Dict[str, Any]]:
        """Phase 2: Visit each card sequentially to extract details"""
        businesses = []
        
        try:
            # Get all loaded cards after scrolling
            cards = await page.query_selector_all(self.config.selectors["business_cards"])
            
            # Check if we have any cards to process
            if not cards or len(cards) == 0:
                logger.warning("No cards available for extraction - could be due to no results or scrolling failure")
                # Try one more direct check - sometimes cards appear but scrolling fails
                await asyncio.sleep(2.0)  # Wait a bit more
                cards = await page.query_selector_all(self.config.selectors["business_cards"])
                if not cards or len(cards) == 0:
                    logger.warning("Confirmed no cards available after additional check")
                    return []
                else:
                    logger.info(f"Found {len(cards)} cards on second check")
                    
            cards_to_process = min(len(cards), max_results)
            
            logger.info(f"Phase 2: Processing {cards_to_process} cards sequentially")
            
            processed_names = set()
            successful_extractions = 0
            
            for i in range(cards_to_process):
                try:
                    logger.info(f"Processing card {i+1}/{cards_to_process}")
                    
                    # Re-fetch cards each time (DOM may have changed)
                    current_cards = await page.query_selector_all(self.config.selectors["business_cards"])
                    if i >= len(current_cards):
                        logger.warning(f"Card {i+1} no longer exists, skipping")
                        continue
                    
                    card = current_cards[i]
                    
                    # Scroll card into view
                    await card.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    
                    # Click the card to open detail pane
                    await card.click()
                    
                    # Wait for detail pane to load
                    try:
                        await page.wait_for_selector('.TIHn2', timeout=8000)
                        await asyncio.sleep(2.0)  # Wait for content to render
                    except:
                        logger.warning(f"Detail pane failed to load for card {i+1}")
                        await self._return_to_list_safe(page)
                        continue
                    
                    # Extract details from the detail pane
                    business = await self._extract_from_detail_pane_precise(page, search_term)
                    
                    if business and business.get('name') and not business.get('error'):
                        # Check for duplicates
                        name_lower = business['name'].lower()
                        if name_lower not in processed_names:
                            processed_names.add(name_lower)
                            businesses.append(business)
                            successful_extractions += 1
                            
                            # Log extraction success
                            has_address = bool(business.get('address'))
                            has_phone = bool(business.get('phone'))
                            has_website = bool(business.get('website'))
                            logger.info(f"✅ {business['name']} | A:{has_address} P:{has_phone} W:{has_website}")
                        else:
                            logger.debug(f"Skipped duplicate: {business['name']}")
                    else:
                        error_msg = business.get('error', 'Unknown error') if business else 'No data extracted'
                        logger.warning(f"❌ Card {i+1} failed: {error_msg}")
                    
                    # Return to list view
                    await self._return_to_list_safe(page)
                    
                    # Small delay between cards
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    
                except Exception as e:
                    logger.warning(f"Failed to process card {i+1}: {e}")
                    await self._return_to_list_safe(page)
                    continue
            
            success_rate = (successful_extractions / cards_to_process) * 100 if cards_to_process > 0 else 0
            logger.info(f"Phase 2 complete: {successful_extractions} successful extractions ({success_rate:.1f}% success rate)")
            
            return businesses
            
        except Exception as e:
            logger.error(f"Sequential card extraction failed: {e}")
            return []
    
    async def _extract_from_detail_pane_precise(self, page: Page, search_term: str) -> Dict[str, Any]:
        """Extract all data from the currently open detail pane using exact selectors from JS"""
        business = {}
        
        try:
            # Check if detail pane is present
            detail_root = await page.query_selector('.TIHn2')
            if not detail_root:
                return {"error": "No detail pane root found"}
            
            # ---- Zone 1: Inside .TIHn2 ----
            # Extract name
            business['name'] = await self._safe_extract_text(page, '.TIHn2 .DUwDvf')
            if not business['name']:
                return {"error": "No business name found in detail pane"}
            
            # Extract category
            business['category'] = await self._safe_extract_text(page, '.TIHn2 button[jsaction*="category"]')
            
            # Extract rating and reviews from .skqShb
            rating_block = await page.query_selector('.TIHn2 .skqShb')
            if rating_block:
                # Extract rating
                rating_text = await self._safe_extract_text(page, '.TIHn2 .skqShb .F7nice span[aria-hidden="true"]')
                if rating_text:
                    try:
                        business['rating'] = float(rating_text)
                    except:
                        business['rating'] = None
                
                # Extract review count
                reviews_text = await self._safe_extract_text(page, '.TIHn2 .skqShb span[aria-label*="review"]')
                if reviews_text:
                    try:
                        # Extract digits only
                        digits = re.sub(r'[^\d]', '', reviews_text)
                        if digits:
                            business['review_count'] = int(digits)
                    except:
                        business['review_count'] = None
            
            # ---- Zone 2: Global .RcCsl... block ----
            # Extract all info elements in the correct container
            info_elements = await page.query_selector_all(
                '.RcCsl.fVHpi.w4vB1d.NOE9ve.M0S7ae.AG25L .Io6YTe.fontBodyMedium.kR99db.fdkmkc'
            )
            
            # Extract text from each element
            info_texts = []
            for element in info_elements:
                try:
                    text = await element.inner_text()
                    if text and text.strip():
                        info_texts.append(text.strip())
                except:
                    continue
            
            # Process info elements to identify address, phone, website
            for text in info_texts:
                # Address: contains commas and numbers
                if not business.get('address') and ',' in text and re.search(r'\d', text):
                    business['address'] = text
                    continue
                
                # Phone: starts with + and contains digits
                elif not business.get('phone') and text.startswith('+') and re.search(r'\d', text):
                    business['phone'] = text
                    continue
                
                # Website: contains dot, no spaces, doesn't start with +
                elif not business.get('website') and '.' in text and ' ' not in text and not text.startswith('+'):
                    if not text.startswith(('http://', 'https://')):
                        text = 'https://' + text
                    business['website'] = text
                    continue
            
            # Store raw info elements for debugging
            business['raw_info_elements'] = info_texts
            
            # Extract coordinates from current URL
            current_url = page.url
            lat, lng = await self._extract_coordinates_from_url(current_url)
            business['latitude'] = lat
            business['longitude'] = lng
            
            # Add inferred category if not found
            if not business.get('category'):
                business['category'] = self._infer_category(search_term)
            
            return business
            
        except Exception as e:
            logger.warning(f"Detail pane extraction failed: {e}")
            return {"error": f"Detail extraction failed: {str(e)}"}
    
    async def _safe_extract_text(self, page: Page, selector: str) -> Optional[str]:
        """Safely extract text from an element"""
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                if text:
                    return text.strip()
        except:
            pass
        return None
    
    async def _return_to_list_safe(self, page: Page):
        """Safely return to list view from detail pane"""
        try:
            # Method 1: Try Escape key
            await page.keyboard.press('Escape')
            await asyncio.sleep(1.0)
            
            # Verify we're back to list
            try:
                await page.wait_for_selector('.Nv2PK', timeout=3000)
                return  # Success
            except:
                pass
            
            # Method 2: Try back button
            back_button = await page.query_selector('[aria-label*="Back"], [data-value="back"]')
            if back_button:
                await back_button.click()
                await asyncio.sleep(1.0)
                
                # Verify we're back to list
                try:
                    await page.wait_for_selector('.Nv2PK', timeout=3000)
                    return  # Success
                except:
                    pass
            
            # Method 3: Click outside detail pane
            await page.click('body', position={'x': 100, 'y': 100})
            await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.debug(f"Return to list failed: {e}")
            # Continue anyway - next card click will handle it
    
    async def _extract_coordinates_from_url(self, url: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract coordinates from the place URL using regex"""
        try:
            # Try pattern 1: !3d31.4802937!4d74.3837626
            match = re.search(self.config.patterns["coordinates_3d4d"], url)
            if match:
                lat, lng = float(match.group(1)), float(match.group(2))
                if self._validate_coordinates(lat, lng):
                    return lat, lng
            
            # Try pattern 2: @31.4802937,74.3837626,15z
            match = re.search(self.config.patterns["coordinates_at"], url)
            if match:
                lat, lng = float(match.group(1)), float(match.group(2))
                if self._validate_coordinates(lat, lng):
                    return lat, lng
            
            return None, None
            
        except:
            return None, None
    
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
            'diagnostic center': 'Diagnostic Center',
            'bank': 'Bank',
            'gas station': 'Gas Station',
            'grocery': 'Grocery Store'
        }
        
        for key, value in category_mappings.items():
            if key in search_lower:
                return value
        
        return "Business"
    
    def _validate_coordinates(self, lat: float, lng: float) -> bool:
        """Validate coordinate ranges"""
        return -90 <= lat <= 90 and -180 <= lng <= 180 