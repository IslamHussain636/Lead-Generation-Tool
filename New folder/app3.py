import requests
import csv
import re

def scrape_emails_from_site(url):
    try:
        html = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
        return list(set(emails))
    except:
        return []

def get_companies_from_opencorporates():
    url = "https://api.opencorporates.com/companies/search?q=software&per_page=5"
    res = requests.get(url).json()
    companies = []
    for item in res.get("results", {}).get("companies", []):
        name = item["company"]["name"]
        website = item["company"].get("homepage_url")
        emails = scrape_emails_from_site(website) if website else []
        companies.append({
            "Company": name,
            "Website": website if website else "N/A",
            "Emails": ", ".join(emails) if emails else "N/A"
        })
    return companies

def run_pipeline():
    leads = get_companies_from_opencorporates()
    with open("leads3.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Company", "Website", "Emails"])
        writer.writeheader()
        writer.writerows(leads)
    print("✅ Leads saved to leads2.csv")

if __name__ == "__main__":
    run_pipeline()
