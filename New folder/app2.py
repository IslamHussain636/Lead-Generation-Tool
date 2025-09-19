from playwright.sync_api import sync_playwright
import csv
import re
import requests

def scrape_emails_from_site(url):
    try:
        html = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
        return list(set(emails))
    except:
        return []

def scrape_angellist():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://angel.co/companies?keywords=software", timeout=60000)
        page.wait_for_timeout(5000)  # wait for JS to load

        companies = []
        cards = page.locator("div.styles_component__2a5e1")  # company cards
        count = cards.count()

        for i in range(min(5, count)):  # limit to 5
            card = cards.nth(i)
            name = card.locator("div.name").inner_text() if card.locator("div.name").count() else "N/A"
            website = None
            if card.locator("a.website-link").count():
                website = card.locator("a.website-link").get_attribute("href")

            emails = scrape_emails_from_site(website) if website else []
            companies.append({
                "Company": name,
                "Website": website if website else "N/A",
                "Emails": ", ".join(emails) if emails else "N/A"
            })

        browser.close()
        return companies

def run_pipeline():
    leads = scrape_angellist()
    with open("leads2.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Company", "Website", "Emails"])
        writer.writeheader()
        writer.writerows(leads)
    print("✅ Leads saved to leads.csv")

if __name__ == "__main__":
    run_pipeline()
