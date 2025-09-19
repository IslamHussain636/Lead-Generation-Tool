import requests
from bs4 import BeautifulSoup
import csv
import re

# -------------------
# STEP 1: Seed Leads (AngelList)
# -------------------
def get_companies_from_angellist():
    url = "https://angel.co/companies?locations[]=Worldwide&keywords=software"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    soup = BeautifulSoup(html, "html.parser")

    companies = []
    for card in soup.select("div.component_2a5e1"):
        name = card.select_one("div.name")
        website = card.select_one("a.website-link")
        if name:
            companies.append({
                "company": name.get_text(strip=True),
                "website": website["href"] if website else None
            })
    return companies[:5]


# -------------------
# STEP 2: Grab emails from website
# -------------------
def scrape_emails_from_site(url):
    try:
        html = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
        return list(set(emails))
    except:
        return []


# -------------------
# STEP 3: Run Pipeline
# -------------------
def run_pipeline():
    leads = get_companies_from_angellist()
    enriched = []

    for lead in leads:
        emails = scrape_emails_from_site(lead["website"]) if lead["website"] else []
        enriched.append({
            "Company": lead["company"],
            "Website": lead["website"] if lead["website"] else "N/A",
            "Emails": ", ".join(emails) if emails else "N/A"
        })

    # Save to CSV
    with open("leads1.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Company", "Website", "Emails"])
        writer.writeheader()
        writer.writerows(enriched)

    print("✅ Leads saved to leads.csv")


if __name__ == "__main__":
    run_pipeline()
