#!/usr/bin/env python3
"""
Google Maps Selenium Scraper - Updated for 2025
⚠️ Educational use only - violates Google's Terms of Service.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
from datetime import datetime


class MapsToWebsiteScraper:
    def __init__(self, headless=False):
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

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def search_on_maps(self, query):
        """Open Google Maps and search"""
        print(f"Searching Google Maps for: {query}")
        self.driver.get("https://www.google.com/maps")
        search_box = self.wait.until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
        search_box.clear()
        search_box.send_keys(query)

        search_button = self.driver.find_element(By.ID, "searchbox-searchbutton")
        search_button.click()
        time.sleep(random.uniform(4, 6))

    def scrape_all_results(self, max_wait_minutes=5):
        """
        Scroll results panel until the end and collect all businesses.
        Keeps scrolling until no new businesses appear or max_wait_minutes is reached.
        """
        print("Collecting business results...")
        business_cards = []
        last_count = 0
        start_time = time.time()

        results_panel = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf')
            )
        )

        while True:
            # Collect all visible cards
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK')

            if len(cards) > last_count:
                last_count = len(cards)
                business_cards = cards
                print(f" → Found {last_count} businesses so far...")

                # Scroll to the last business card (forces lazy load)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'end'});",
                    cards[-1]
                )

                # Give enough time for new results to load
                time.sleep(random.uniform(4, 7))

            else:
                # No new results loaded → possible end
                elapsed = time.time() - start_time
                if elapsed > max_wait_minutes * 60:
                    print("⏳ Max wait time reached. Stopping scroll.")
                    break

                # Try waiting a bit more before concluding
                print("Waiting for more results to load...")
                time.sleep(5)

                # Re-check if new results appeared
                new_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK')
                if len(new_cards) == last_count:
                    print("✅ Reached end of list")
                    break

        print(f"Total businesses collected: {len(business_cards)}")
        return business_cards

    def process_business(self, card):
        """Extract data directly from card"""
        try:
            # Business name
            try:
                name = card.find_element(By.CSS_SELECTOR, 'div.qBF1Pd').text.strip()
            except:
                name = ""

            # Category + address + phone
            try:
                details = card.find_elements(By.CSS_SELECTOR, 'div.W4Efsd')
                category_address = details[0].text if len(details) > 0 else ""
                phone = details[1].find_element(By.CSS_SELECTOR, 'span.UsdlK').text if len(details) > 1 else ""
            except:
                category_address, phone = "", ""

            # Website
            try:
                website_button = card.find_element(By.CSS_SELECTOR, 'a.lcr4fd')
                website = website_button.get_attribute("href")
            except:
                website = ""

            data = {
                "name": name,
                "category_address": category_address,
                "phone": phone,
                "website": website
            }
            self.results.append(data)
            print("✔ Extracted:", data)

        except Exception as e:
            print("Error processing business:", e)

    def save_to_csv(self):
        """Save results to CSV"""
        if not self.results:
            return None

        filename = f"businesses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "category_address", "phone", "website"])
            writer.writeheader()
            writer.writerows(self.results)
        print(f"Results saved to {filename}")
        return filename

    def close(self):
        self.driver.quit()


def main():
    print("⚠️ WARNING: This scraper violates Google's Terms of Service")
    state = input("Enter US state (e.g., California, Texas, New York): ").strip()
    business_types = input("Enter custom business types (comma-separated) or press Enter for default: ").strip()
    if not business_types:
        business_types = "Software houses"

    scraper = MapsToWebsiteScraper(headless=False)
    try:
        query = f"{business_types} in {state}"
        scraper.search_on_maps(query)

        cards = scraper.scrape_all_results(max_wait_minutes=8)  # waits up to 8 minutes
        for card in cards:
            scraper.process_business(card)

        scraper.save_to_csv()

    finally:
        input("Press Enter to close browser...")
        scraper.close()


if __name__ == "__main__":
    main()
