#!/usr/bin/env python3
"""
Google Maps Business Scraper
⚠️ For educational/research use only. Scraping Google Maps may violate ToS.
"""

import time
import random
import re
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


class MapsToWebsiteScraper:
    def __init__(self, headless=True, visit_websites=True):
        self.visit_websites = visit_websites
        self.max_results = 50
        self.results = []
        self.setup_driver(headless)

    def setup_driver(self, headless=True):
        """Setup Chrome driver with optimized options for server deployment"""
        chrome_options = Options()
        
        # Essential headless options
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Server-friendly options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        # Note: Removed --disable-javascript to allow website interaction
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        
        # Memory and performance optimizations
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Window size
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 20)
            self.actions = ActionChains(self.driver)
            print("[Driver] Chrome driver initialized successfully")
        except Exception as e:
            print(f"[Driver] Error initializing Chrome driver: {e}")
            raise

    def set_max_results(self, max_results):
        """Set maximum number of results to extract"""
        self.max_results = max_results

    def search_on_maps(self, query):
        """Search for businesses on Google Maps"""
        print(f"[Search] Searching Google Maps for: {query}")
        
        try:
            self.driver.get("https://www.google.com/maps")
            time.sleep(random.uniform(3, 5))
            
            # Wait for and click search box
            search_box = self.wait.until(
                EC.element_to_be_clickable((By.ID, "searchboxinput"))
            )
            search_box.clear()
            search_box.send_keys(query)
            
            # Click search button
            search_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "searchbox-searchbutton"))
            )
            search_button.click()
            
            # Wait for results to load
            time.sleep(random.uniform(5, 8))
            
            # Wait for results panel to appear
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed'], div.m6QErb"))
            )
            
            print("[Search] Search completed, results loaded")
            
        except TimeoutException as e:
            print(f"[Search] Timeout waiting for search elements: {e}")
            raise
        except Exception as e:
            print(f"[Search] Error during search: {e}")
            raise

    def _find_results_panel(self):
        """Find the scrollable results container with multiple fallbacks"""
        selectors = [
            "div[role='feed']",
            "div[aria-label*='Results']",
            "div[aria-label*='Businesses']",
            "div.m6QErb",
            "div.DxyBCb", 
            "div.kA9KIf"
        ]
        
        for selector in selectors:
            try:
                panel = self.driver.find_element(By.CSS_SELECTOR, selector)
                if panel:
                    print(f"[Panel] Found results panel with selector: {selector}")
                    return panel
            except NoSuchElementException:
                continue
        
        print("[Panel] No dedicated results panel found")
        return None

    def _scroll_and_load_results(self):
        """Scroll through results and collect business cards"""
        panel = self._find_results_panel()
        use_page_scroll = panel is None
        
        if use_page_scroll:
            print("[Scroll] Using page scroll fallback")
        
        last_count = 0
        idle_rounds = 0
        max_idle_rounds = 5
        
        while len(self.results) < self.max_results:
            # Find current business cards
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK, a.hfpxzc")
            current_count = len(cards)
            
            print(f"[Scroll] Found {current_count} cards, processed {len(self.results)}")
            
            # Check if we have new cards
            if current_count > last_count:
                idle_rounds = 0
                last_count = current_count
            else:
                idle_rounds += 1
            
            # Process new cards
            cards_to_process = cards[len(self.results):len(self.results) + min(5, self.max_results - len(self.results))]
            
            for card in cards_to_process:
                if len(self.results) >= self.max_results:
                    break
                self._extract_business_data(card)
            
            # Check if we should continue
            if len(self.results) >= self.max_results:
                print(f"[Scroll] Reached max results limit: {self.max_results}")
                break
                
            if idle_rounds >= max_idle_rounds:
                print("[Scroll] No new cards found after multiple attempts")
                break
            
            # Scroll for more results
            if use_page_scroll:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            else:
                try:
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", panel)
                except:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(random.uniform(2, 4))
        
        print(f"[Scroll] Completed scrolling. Total results: {len(self.results)}")

    def _extract_business_data(self, card):
        """Extract data from a business card"""
        try:
            # Scroll card into view
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
            time.sleep(random.uniform(0.5, 1))
            
            # Click on the card to open details
            try:
                link = card.find_element(By.CSS_SELECTOR, "a.hfpxzc")
                self.driver.execute_script("arguments[0].click();", link)
            except:
                try:
                    card.click()
                except:
                    print("[Extract] Could not click card, skipping")
                    return
            
            # Wait for details to load
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
                time.sleep(random.uniform(1, 2))
            except TimeoutException:
                print("[Extract] Timeout waiting for business details")
                return
            
            # Initialize data structure
            data = {
                "name": "",
                "rating": "",
                "category": "",
                "address": "",
                "phone": "",
                "website": "",
                "email": "",
                "linkedin": ""
            }
            
            # Extract business name
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, "h1")
                data["name"] = name_element.text.strip()
            except:
                print("[Extract] Could not find business name")
            
            # Extract rating
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="star"]')
                rating_text = rating_element.get_attribute("aria-label")
                if rating_text:
                    # Extract number from aria-label like "4.5 stars"
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        data["rating"] = rating_match.group(1)
            except:
                try:
                    # Alternative rating selector
                    rating_element = self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice span[aria-hidden="true"]')
                    data["rating"] = rating_element.text.strip()
                except:
                    pass
            
            # Extract category/type
            try:
                category_element = self.driver.find_element(By.CSS_SELECTOR, 'button[jsaction*="category"]')
                data["category"] = category_element.text.strip()
            except:
                try:
                    # Alternative category selector
                    category_element = self.driver.find_element(By.CSS_SELECTOR, 'div.LBgpqf div.W4Efsd:first-child span')
                    data["category"] = category_element.text.strip()
                except:
                    pass
            
            # Extract address
            try:
                address_element = self.driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]')
                data["address"] = address_element.text.strip()
            except:
                try:
                    # Alternative address selector
                    address_element = self.driver.find_element(By.CSS_SELECTOR, 'div[data-value="Address"]')
                    data["address"] = address_element.text.strip()
                except:
                    pass
            
            # Extract phone
            try:
                phone_element = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
                data["phone"] = phone_element.text.strip()
            except:
                try:
                    # Alternative phone selectors
                    phone_element = self.driver.find_element(By.CSS_SELECTOR, 'a[href^="tel:"]')
                    phone_href = phone_element.get_attribute("href")
                    if phone_href:
                        data["phone"] = phone_href.replace("tel:", "").strip()
                except:
                    pass
            
            # Extract website
            try:
                website_element = self.driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
                data["website"] = website_element.get_attribute("href")
            except:
                try:
                    # Alternative website selector
                    website_element = self.driver.find_element(By.CSS_SELECTOR, 'a[href*="http"]:not([href*="google"])')
                    data["website"] = website_element.get_attribute("href")
                except:
                    pass
            
            # Visit website for email/LinkedIn if enabled
            if self.visit_websites and data["website"]:
                self._extract_website_contacts(data)
            
            # Add to results if we have at least a name
            if data["name"]:
                self.results.append(data)
                print(f"[Extract] ✓ Extracted: {data['name']} ({len(self.results)}/{self.max_results})")
            else:
                print("[Extract] ✗ Skipped: No business name found")
                
        except Exception as e:
            print(f"[Extract] ✗ Error extracting business data: {e}")

    def _extract_website_contacts(self, data):
        """Extract email and LinkedIn from business website"""
        try:
            original_window = self.driver.current_window_handle
            
            # Open website in new tab
            self.driver.execute_script("window.open(arguments[0]);", data["website"])
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for page to load
            time.sleep(3)
            
            # Get page source and extract emails/LinkedIn
            html = self.driver.page_source.lower()
            
            # Extract emails
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
            if emails:
                # Filter out common non-business emails
                business_emails = [e for e in emails if not any(ignore in e.lower() 
                                 for ignore in ['noreply', 'no-reply', 'donotreply', 'example.com', 'test.com'])]
                if business_emails:
                    data["email"] = business_emails[0]
            
            # Extract LinkedIn
            linkedin_patterns = [
                r"https?://[^\s'\"]*linkedin\.com[^\s'\"<]*",
                r"linkedin\.com/company/[^\s'\"<]*",
                r"linkedin\.com/in/[^\s'\"<]*"
            ]
            
            for pattern in linkedin_patterns:
                linkedins = re.findall(pattern, html)
                if linkedins:
                    data["linkedin"] = linkedins[0]
                    break
            
        except Exception as e:
            print(f"[Website] Error extracting from website: {e}")
        finally:
            try:
                # Close website tab and return to maps
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
            except:
                pass

    def scroll_hover_and_extract(self):
        """Main method to scroll through results and extract data"""
        print("[Main] Starting data extraction process")
        self._scroll_and_load_results()
        print(f"[Main] Extraction completed. Found {len(self.results)} businesses")
        return self.results

    def save_to_csv(self, filename=None):
        """Save results to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"gmaps_businesses_{timestamp}.csv"
        
        if not self.results:
            print("[CSV] No results to save")
            return None
        
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                fieldnames = ['name', 'rating', 'category', 'address', 'phone', 'website', 'email', 'linkedin']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
            
            print(f"[CSV] ✓ Saved {len(self.results)} results to {filename}")
            return filename
        except Exception as e:
            print(f"[CSV] ✗ Error saving to CSV: {e}")
            return None

    def close(self):
        """Clean up and close the driver"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("[Driver] Chrome driver closed")
        except Exception as e:
            print(f"[Driver] Error closing driver: {e}")


def main():
    """Main function for standalone testing"""
    print("⚠️  WARNING: This may violate Google Maps Terms of Service. Use responsibly.")
    
    location = input("Enter location (e.g., 'New York, NY'): ").strip()
    business_type = input("Enter business type (e.g., 'Software companies'): ").strip()
    max_results = int(input("Enter max results (10-100): ").strip() or "50")
    
    if not location or not business_type:
        print("Location and business type are required!")
        return
    
    scraper = MapsToWebsiteScraper(headless=True, visit_websites=True)
    
    try:
        scraper.set_max_results(max_results)
        query = f"{business_type} in {location}"
        scraper.search_on_maps(query)
        results = scraper.scroll_hover_and_extract()
        scraper.save_to_csv()
        
        print(f"\n✓ Successfully extracted {len(results)} businesses")
        
    except Exception as e:
        print(f"✗ Error during scraping: {e}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()