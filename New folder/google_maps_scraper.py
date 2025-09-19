#!/usr/bin/env python3
"""
Google Maps Selenium Scraper - API Compatible Version
Keeps the original working scraping logic but adds API integration features
"""

import time
import random
import re
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


class MapsToWebsiteScraper:
    def __init__(self, headless=True, visit_websites=True):
        """
        headless: True = run without showing the browser
        visit_websites: if True will open company websites to search for emails/linkedin (slower, optional)
        """
        self.visit_websites = visit_websites
        self.max_results = None
        self.setup_driver(headless)
        self.results = []

    def setup_driver(self, headless=True):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Performance optimizations for API usage
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        self.actions = ActionChains(self.driver)

    def search_on_maps(self, query):
        """Open Google Maps and search"""
        print(f"🔎 Searching Google Maps for: {query}")
        self.driver.get("https://www.google.com/maps")

        search_box = self.wait.until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
        search_box.clear()
        search_box.send_keys(query)

        search_button = self.driver.find_element(By.ID, "searchbox-searchbutton")
        search_button.click()

        # wait for results to appear
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Nv2PK')))
        time.sleep(random.uniform(4, 7))

    def scrape_all_results(self):
        """Scroll results panel until the very end"""
        print("📜 Scrolling to collect all business results...")
        results_panel = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )

        last_height = -1
        same_count = 0

        while True:
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK')
            print(f"➡️ Loaded {len(cards)} business cards so far...")

            # Check if we've reached max results
            if self.max_results and len(cards) >= self.max_results:
                print(f"🎯 Reached maximum results limit: {self.max_results}")
                break

            # scroll a bit further
            self.driver.execute_script("arguments[0].scrollTop += 1000;", results_panel)
            time.sleep(random.uniform(3, 6))

            new_height = self.driver.execute_script("return arguments[0].scrollTop", results_panel)

            if new_height == last_height:
                same_count += 1
            else:
                same_count = 0

            if same_count >= 3:  # no new content after 3 tries
                break

            last_height = new_height

        # Limit results if max_results is set
        if self.max_results and len(cards) > self.max_results:
            cards = cards[:self.max_results]

        print(f"✅ Finished scrolling. Found {len(cards)} business cards")
        return cards

    def process_business(self, card):
        """Open business details and try to extract info"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
            self.actions.move_to_element(card).perform()
            time.sleep(random.uniform(1, 2))
            card.click()
            time.sleep(random.uniform(3, 6))

            # Business name
            try:
                name = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf'))
                ).text.strip()
            except:
                name = ""

            # Rating
            rating = ""
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, 'span.MW4etd')
                rating = rating_element.text.strip()
            except:
                pass

            # Category/address/phone
            category = ""
            address = ""
            phone = ""
            try:
                info_sections = self.driver.find_elements(By.CSS_SELECTOR, 'div.Io6YTe.fontBodyMedium')
                if len(info_sections) > 0:
                    category = info_sections[0].text.strip()
                if len(info_sections) > 1:
                    # Could be address or phone, need to distinguish
                    second_info = info_sections[1].text.strip()
                    if re.search(r'[\d\-\+\(\)\s]{7,}', second_info):
                        phone = second_info
                    else:
                        address = second_info
                if len(info_sections) > 2:
                    address = info_sections[2].text.strip()
            except:
                pass

            # Try to get address from address button
            if not address:
                try:
                    address_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]')
                    address = address_button.text.strip()
                except:
                    pass

            # Try to get phone from phone button
            if not phone:
                try:
                    phone_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Call"]')
                    phone = phone_button.text.strip()
                except:
                    pass

            # Website
            website = ""
            try:
                website_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
                website = website_button.get_attribute("href")
            except:
                pass

            # Extract email & LinkedIn from website
            email, linkedin = "", ""
            if website and self.visit_websites:
                try:
                    self.driver.execute_script("window.open(arguments[0]);", website)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(7)

                    page_source = self.driver.page_source
                    
                    # Extract emails
                    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", page_source)
                    # Filter out common false positives
                    valid_emails = [email for email in emails 
                                  if not any(exclude in email.lower() 
                                           for exclude in ['example.com', 'test.com', 'noreply', 'no-reply'])]
                    if valid_emails:
                        email = valid_emails[0]
                    
                    # Extract LinkedIn
                    linkedin_matches = re.findall(r"https?://[^\s'\"]*linkedin\.com[^\s'\"<]*", page_source)
                    if linkedin_matches:
                        linkedin = linkedin_matches[0]

                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                except Exception as e:
                    print(f"❌ Error extracting from website {website}: {e}")
                    # Make sure we're back on the main window
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                    except:
                        pass

            # Create data in API-compatible format
            data = {
                "name": name,
                "rating": rating,
                "category": category,
                "address": address,
                "phone": phone,
                "website": website,
                "email": email,
                "linkedin": linkedin
            }
            
            self.results.append(data)
            print(f"✔ Extracted: {name} - {category}")
            return data

        except Exception as e:
            print(f"❌ Error processing business: {e}")
            return None

    def scroll_hover_and_extract(self):
        """API-compatible method that combines scraping and extraction"""
        cards = self.scrape_all_results()
        
        print(f"🔄 Processing {len(cards)} businesses...")
        processed_count = 0
        
        for idx, card in enumerate(cards, start=1):
            if self.max_results and processed_count >= self.max_results:
                break
                
            print(f"\n➡️ Processing business {idx}/{len(cards)}")
            result = self.process_business(card)
            if result:
                processed_count += 1
            
            # Small delay between businesses
            time.sleep(random.uniform(1, 3))
        
        print(f"✅ Extraction complete: {len(self.results)} businesses processed")
        return self.results

    def set_max_results(self, max_results):
        """Set maximum number of results to extract"""
        self.max_results = max_results
        print(f"📊 Maximum results set to: {max_results}")

    def save_to_csv(self, filename=None):
        """Save results to CSV"""
        if not self.results:
            return None

        if not filename:
            filename = f"businesses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        fieldnames = ["name", "rating", "category", "address", "phone", "website", "email", "linkedin"]
        
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for business in self.results:
                writer.writerow({field: business.get(field, "") for field in fieldnames})
        
        print(f"📁 Results saved to {filename}")
        return filename

    def close(self):
        """Close the browser"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
            print("🔒 Browser closed successfully")
        except Exception as e:
            print(f"❌ Error closing browser: {e}")


def main():
    """Standalone usage - keeps your original functionality"""
    print("⚠️ WARNING: This scraper violates Google's Terms of Service")
    state = input("Enter US state (e.g., California, Texas, New York): ").strip()
    business_types = input("Enter business type (e.g., plumbers, software houses): ").strip()
    if not business_types:
        business_types = "Software houses"

    max_results = input("Maximum results (10-100) [50]: ").strip()
    try:
        max_results = int(max_results) if max_results else 50
        max_results = max(10, min(100, max_results))
    except ValueError:
        max_results = 50

    visit_websites = input("Visit websites to extract emails/LinkedIn? (y/n) [y]: ").strip().lower()
    visit_websites = visit_websites != 'n'

    scraper = MapsToWebsiteScraper(headless=False, visit_websites=visit_websites)
    try:
        scraper.set_max_results(max_results)
        query = f"{business_types} in {state}"
        scraper.search_on_maps(query)
        results = scraper.scroll_hover_and_extract()
        filename = scraper.save_to_csv()
        
        print(f"\n🎉 Scraping completed!")
        print(f"📁 Results saved to: {filename}")
        print(f"📊 Total businesses: {len(results)}")

    finally:
        input("Press Enter to close browser...")
        scraper.close()


if __name__ == "__main__":
    main()