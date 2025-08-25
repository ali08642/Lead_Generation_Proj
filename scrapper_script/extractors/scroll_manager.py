#!/usr/bin/env python3
"""
Smart auto-scroll based on JavaScript testing insights
"""

import logging
from typing import Optional
from playwright.async_api import Page
from config import OptimizedSelectorsConfig

logger = logging.getLogger(__name__)

class SmartScrollManager:
    """Smart auto-scroll based on JavaScript testing insights"""
    
    def __init__(self, config: OptimizedSelectorsConfig):
        self.config = config
        self.scroll_container = None
        
    async def find_scrollable_container(self, page: Page) -> bool:
        """Dynamically find the scrollable container using the exact JavaScript from the user"""
        try:
            # First, make sure there are some businesses on the page
            cards = await page.query_selector_all('.Nv2PK')
            if not cards:
                logger.warning("No business cards found on page")
                # First check if we need to dismiss any modals/overlays
                try:
                    dialogs = await page.query_selector_all('button[aria-label*="Dismiss"], button[aria-label*="dismiss"], button[aria-label*="Close"], button[aria-label*="close"]')
                    if dialogs:
                        logger.info("Found potential dialog/overlay to dismiss")
                        await dialogs[0].click()
                        await page.wait_for_timeout(1000)
                except Exception as e:
                    logger.debug(f"Dialog check: {e}")
                return False
                
            logger.info(f"Found {len(cards)} business cards, looking for scrollable container...")
            
            # Strategy 1: Primary approach using JavaScript detection
            result = await page.evaluate("""
                (function findScrollContainer() {
                  const card = document.querySelector('.Nv2PK');
                  if (!card) { console.warn('No cards found.'); return null; }

                  let el = card.parentElement;
                  while (el && el !== document.body) {
                    const sh = el.scrollHeight;
                    const ch = el.clientHeight;
                    const style = getComputedStyle(el);
                    if (sh > ch && (style.overflowY === 'auto' || style.overflowY === 'scroll')) {
                      console.log('✅ Found scrollable container:', el);
                      window._mapsListContainer = el; // expose globally
                      return {
                        tag: el.tagName,
                        className: el.className,
                        scrollHeight: sh,
                        clientHeight: ch,
                        hasRoleFeed: el.getAttribute('role') === 'feed'
                      };
                    }
                    el = el.parentElement;
                  }
                  console.warn('❌ No scrollable container found');
                  return null;
                })();
            """)
            
            if result:
                logger.info(f"✅ Found scrollable container: {result['tag']}.{result['className'][:50]}...")
                logger.info(f"   ScrollHeight: {result['scrollHeight']}, ClientHeight: {result['clientHeight']}")
                self.scroll_container = True
                return True
                
            # Strategy 2: Try direct selector approach if JavaScript method fails
            for container_selector in self.config.selectors["potential_containers"]:
                try:
                    container = await page.query_selector(container_selector)
                    if container:
                        # Check if it contains cards
                        cards_in_container = await container.query_selector_all('.Nv2PK')
                        if cards_in_container and len(cards_in_container) > 0:
                            # Set as global in page context
                            await page.evaluate(f"""
                                window._mapsListContainer = document.querySelector('{container_selector}');
                                console.log('Found container via direct selector: {container_selector}');
                            """)
                            logger.info(f"✅ Found scrollable container via direct selector: {container_selector}")
                            self.scroll_container = True
                            return True
                except Exception as container_error:
                    logger.debug(f"Container selector {container_selector} failed: {container_error}")
            
            logger.warning("❌ No scrollable container found with any strategy")
            return False
                
        except Exception as e:
            logger.error(f"Failed to find scrollable container: {e}")
            return False
    
    async def auto_scroll_load_all_cards(self, page: Page, max_results: int = 100) -> int:
        """Auto-scroll to load all cards using the exact JavaScript from the user"""
        # Add multiple retries to find scrollable container
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            if not self.scroll_container:
                logger.info(f"Finding scrollable container (attempt {retry_count+1}/{max_retries})")
                if not await self.find_scrollable_container(page):
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Waiting and retrying container detection...")
                        await page.wait_for_timeout(3000)  # Wait 3 seconds before retry
                        # Refresh the page state if needed
                        try:
                            await page.evaluate("window.scrollTo(0, 0);")
                        except:
                            pass
                        continue
                    else:
                        logger.error("Failed to find scrollable container after multiple attempts")
                        return 0
                else:
                    break  # Found container, exit retry loop
            else:
                break  # Container was already found
        
        if not self.scroll_container:
            logger.error("Cannot scroll without finding container")
            return 0
        
        logger.info("✅ Starting smart auto-scroll...")
        
        try:
            # Use the exact JavaScript code provided by the user
            total_cards = await page.evaluate("""
                (async function(){
                  const listContainer = window._mapsListContainer;
                  if(!listContainer){ console.warn("❌ No list container"); return 0; }
                  console.log("✅ Auto-scroll started…");

                  let prevCount = 0;
                  let stableRounds = 0;
                  let totalRounds = 0;

                  while (stableRounds < 3 && totalRounds < 50) {
                    totalRounds++;
                    const cards = document.querySelectorAll('.Nv2PK');
                    const count = cards.length;
                    
                    if (count >= %d) {
                      console.log(`✅ Reached target: ${count} cards`);
                      break;
                    }
                    
                    if (count > prevCount) {
                      console.log(`✨ New cards: ${count - prevCount}, Total: ${count}`);
                      prevCount = count;
                      stableRounds = 0;
                    } else {
                      stableRounds++;
                      console.log(`⏸️  No new cards (${stableRounds}/3)`);
                    }

                    listContainer.scrollBy(0, listContainer.clientHeight - 50);
                    await new Promise(r => setTimeout(r, 1500));
                  }

                  console.log("✅ Auto-scroll complete. Total cards loaded:", document.querySelectorAll('.Nv2PK').length);
                  return document.querySelectorAll('.Nv2PK').length;
                })();
            """ % max_results)
            
            logger.info(f"✅ Auto-scroll complete. Loaded {total_cards} business cards")
            return total_cards
            
        except Exception as e:
            logger.error(f"Auto-scroll failed: {e}")
            # Fallback: count current cards
            try:
                cards = await page.query_selector_all(self.config.selectors["business_cards"])
                return len(cards)
            except:
                return 0 