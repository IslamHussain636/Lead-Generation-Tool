import requests
from bs4 import BeautifulSoup
import subprocess
import re
import csv

# -------------------
# STEP 1: Seed Leads (RemoteOK Job Board)
# -------------------
def get_companies_from_remoteok():
    url = "https://remoteok.com/remote-software-jobs"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    soup = BeautifulSoup(html, "html.parser")

    companies = []
    for job in soup.select("tr.job"):
        company = job.get("data-company")
        link = job.get("data-url")
        if company and link:
            companies.append({"company": company, "link": "https://remoteok.com" + link})
    return companies[:5]  # limit to 5 for demo


# -------------------
# STEP 2: Enrich (Tech stack with Wappalyzer CLI)
# -------------------
def get_tech_stack(url):
    try:
        # Run wappalyzer CLI (make sure you installed it with npm install -g wappalyzer)
        result = subprocess.run(
            ["wappalyzer", url, "--quiet"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


# -------------------
# STEP 3: Grab emails from website (simple regex)
# -------------------
def scrape_emails_from_site(url):
    try:
        html = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
        return list(set(emails))
    except:
        return []


# -------------------
# STEP 4: Run Pipeline
# -------------------
def run_pipeline():
    leads = get_companies_from_remoteok()
    enriched = []

    for lead in leads:
        company_url = lead["link"]
        tech_stack = get_tech_stack(company_url)
        emails = scrape_emails_from_site(company_url)

        enriched.append({
            "Company": lead["company"],
            "Website": company_url,
            "TechStack": tech_stack,
            "Emails": ", ".join(emails) if emails else "N/A",
        })

    # Save to CSV
    with open("leads.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Company", "Website", "TechStack", "Emails"])
        writer.writeheader()
        writer.writerows(enriched)

    print("✅ Leads saved to leads.csv")


if __name__ == "__main__":
    run_pipeline()
