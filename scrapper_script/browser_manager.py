#!/usr/bin/env python3
"""
Browser pool and context management
"""

import asyncio
import random
import logging
from typing import List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from persistent_browser_manager import setup_persistent_browsers

logger = logging.getLogger(__name__)

# Ensure persistent browsers are setup before using Playwright
setup_persistent_browsers()

class EnhancedBrowserPool:
    """Optimized browser pool"""
    
    def __init__(self, pool_size: int = 1):
        self.pool_size = pool_size
        self.browsers: List[Browser] = []
        self.available_browsers = asyncio.Queue()
        self.playwright = None
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize browser pool"""
        async with self._lock:
            if self._initialized:
                return
                
            try:
                self.playwright = await async_playwright().start()
                
                for i in range(self.pool_size):
                    browser = await self._create_browser()
                    if browser:
                        self.browsers.append(browser)
                        await self.available_browsers.put(browser)
                
                self._initialized = True
                logger.info(f"Initialized browser pool with {len(self.browsers)} browsers")
                
            except Exception as e:
                logger.error(f"Failed to initialize browser pool: {e}")
                raise
    
    async def _create_browser(self) -> Browser:
        """Create optimized browser"""
        browser = await self.playwright.chromium.launch(
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
        return browser
    
    async def get_browser(self) -> Browser:
        """Get browser from pool"""
        if not self._initialized:
            await self.initialize()
        return await self.available_browsers.get()
    
    async def return_browser(self, browser: Browser):
        """Return browser to pool"""
        await self.available_browsers.put(browser)
    
    async def cleanup(self):
        """Clean up browser pool with timeout protection"""
        cleanup_tasks = []
        
        # Close browsers with timeout
        for browser in self.browsers:
            try:
                cleanup_tasks.append(asyncio.wait_for(browser.close(), timeout=10.0))
            except:
                pass
        
        # Execute all cleanup tasks concurrently with timeout
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Browser cleanup timed out: {e}")
        
        # Stop playwright with timeout
        if self.playwright:
            try:
                await asyncio.wait_for(self.playwright.stop(), timeout=5.0)
            except Exception as e:
                logger.warning(f"Playwright stop timed out: {e}")
        
        self._initialized = False

class BrowserContextManager:
    """Manages browser context creation with stealth measures"""
    
    @staticmethod
    async def create_stealth_context(browser: Browser) -> BrowserContext:
        """Create browser context with stealth measures"""
        # Randomize viewport to avoid fingerprinting
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1440, 'height': 900},
            {'width': 1536, 'height': 864},
        ]
        viewport = random.choice(viewports)
        
        # Randomize user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        user_agent = random.choice(user_agents)
        
        # Common context options
        context_options = {
            'viewport': viewport,
            'user_agent': user_agent,
            # Add some realistic headers
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
        }
        
        # Create context with options
        try:
            context = await browser.new_context(**context_options)
            return context
        except Exception as e:
            logger.warning(f"Failed to create context: {e}")
            raise
    
    @staticmethod
    async def apply_stealth_measures(page: Page):
        """Apply stealth measures to avoid detection"""
        try:
            # Override navigator properties to avoid detection
            await page.add_init_script("""
                // Override webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Override automation properties
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Override Chrome object
                window.chrome = {
                    runtime: {},
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
        except Exception as e:
            logger.debug(f"Stealth measures failed: {e}")
    
    @staticmethod
    async def check_if_blocked(page: Page) -> bool:
        """Check if Google Maps is blocking the request"""
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
            
            # Check if the page loaded properly by looking for expected elements
            maps_elements = await page.query_selector_all('#searchbox, [role="main"], .maps-sprite-pane-directions')
            if len(maps_elements) == 0:
                logger.warning("Expected Maps elements not found - possible blocking")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Block detection failed: {e}")
            return False 