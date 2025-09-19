from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import re

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Path to your chromedriver (make sure to update the path)
chrome_driver_path = "/path/to/chromedriver"

# Set up WebDriver
driver = webdriver.Chrome(service=Service(chrome_driver_path), options=chrome_options)

# Open Google Maps (searching for businesses in a specific state)
state = "California"
search_query = f"companies in {state} site:google.com/maps"
driver.get(f"https://www.google.com/maps/search/{search_query}")

# Give time for page to load
time.sleep(5)

# Scroll to load more results (optional)
for _ in range(5):
    ActionChains(driver).send_keys(Keys.END).perform()
    time.sleep(2)

# Get the page source after rendering
soup = BeautifulSoup(driver.page_source, "html.parser")

# Extract company names and website links
companies = []

# Find all elements that contain website links (adjust based on the HTML structure)
for link in soup.find_all("a", {"class": "lcr4fd"}):
    website = link.get('href')
    if website and "http" in website:
        companies.append(website)

# Output the extracted websites
for idx, website in enumerate(companies, 1):
    print(f"{idx}: {website}")

# Close the browser
driver.quit()
