#!/usr/bin/env python3
"""
Simple lead extractor using OpenStreetMap (Nominatim + Overpass).
- Gets bbox for a city via Nominatim (fallback: hardcoded bbox).
- Queries Overpass for nodes/ways/relations whose name contains keywords (software|data|tech|dev).
- Collects name, tags (website, phone, addr), and tries simple email scraping from website.
- Writes csv 'osm_leads.csv'.
"""

import requests, time, csv, re
from urllib.parse import urlencode

# CONFIG
CITY = "New York, USA"        # <- change to target city/location
KEYWORDS = ["software","tech","data","developer","development","analytics","ai","ml","machine learning"]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "lead-gen-bot/1.0 (islam.stablesystem@gmail.com)"  # ✅ updated

HEADERS = {"User-Agent": USER_AGENT}

# Hardcoded bbox fallback dictionary
HARDCODED_BBOX = {
    "New York, USA": (40.477399, -74.259090, 40.917577, -73.700272),  # south, west, north, east
    "Karachi, Pakistan": (24.789, 66.845, 25.021, 67.157),
    "London, UK": (51.286760, -0.510375, 51.691874, 0.334015)
}

def get_bbox_for_city(city):
    try:
        params = {"q": city, "format": "json", "limit": 1}
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            raise RuntimeError("City not found via Nominatim.")
        bbox = data[0]["boundingbox"]  # [south, north, west, east] as strings
        return float(bbox[0]), float(bbox[2]), float(bbox[1]), float(bbox[3])
    except Exception as e:
        print(f"[!] Nominatim failed ({e}), using fallback bbox for {city}")
        if city in HARDCODED_BBOX:
            return HARDCODED_BBOX[city]
        else:
            raise SystemExit("No fallback bbox available. Please add it in HARDCODED_BBOX.")

def build_overpass_query(south, west, north, east, keywords, limit=200):
    # Escape special regex characters and create pattern
    escaped_keywords = [re.escape(k.lower()) for k in keywords]
    kw_regex = "|".join(escaped_keywords)
    
    # Build the query with proper formatting
    q = f"""[out:json][timeout:60];
(
  node["name"~"{kw_regex}",i]({south},{west},{north},{east});
  way["name"~"{kw_regex}",i]({south},{west},{north},{east});
  relation["name"~"{kw_regex}",i]({south},{west},{north},{east});
  node["office"~"company|business",i]({south},{west},{north},{east});
  way["office"~"company|business",i]({south},{west},{north},{east});
  relation["office"~"company|business",i]({south},{west},{north},{east});
  node["shop"~"computer|electronics",i]({south},{west},{north},{east});
  way["shop"~"computer|electronics",i]({south},{west},{north},{east});
);
out center {limit};"""
    
    return q

def query_overpass(q):
    print(f"[DEBUG] Sending query:\n{q}")
    try:
        r = requests.post(OVERPASS_URL, data={"data": q}, headers=HEADERS, timeout=120)
        print(f"[DEBUG] Response status: {r.status_code}")
        if r.status_code != 200:
            print(f"[DEBUG] Response content: {r.text[:500]}...")
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP Error: {e}")
        print(f"[ERROR] Response content: {r.text}")
        raise
    except Exception as e:
        print(f"[ERROR] Other error: {e}")
        raise

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)

def scrape_emails_from_website(url):
    try:
        if not url:
            return []
        if not url.startswith("http"):
            url = "http://" + url
        r = requests.get(url, headers=HEADERS, timeout=10)
        text = r.text
        emails = set(re.findall(EMAIL_RE, text))
        return list(emails)[:5]
    except Exception as e:
        print(f"[DEBUG] Email scraping failed for {url}: {e}")
        return []

def element_to_record(elem):
    tags = elem.get("tags", {})
    name = tags.get("name")
    website = tags.get("website") or tags.get("contact:website")
    phone = tags.get("phone") or tags.get("contact:phone")
    addr = ", ".join(filter(None, [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
        tags.get("addr:country")
    ]))
    return {
        "osm_type": elem.get("type"),
        "osm_id": elem.get("id"),
        "name": name,
        "website": website,
        "phone": phone,
        "address": addr or tags.get("addr:full") or "",
        "tags": tags
    }

def run():
    print(f"[+] Getting bbox for: {CITY}")
    south, west, north, east = get_bbox_for_city(CITY)
    print(f"    bbox: {south}, {west}, {north}, {east}")

    q = build_overpass_query(south, west, north, east, KEYWORDS, limit=500)
    print("[+] Querying Overpass API (this may take a few seconds)...")
    
    try:
        data = query_overpass(q)
    except Exception as e:
        print(f"[ERROR] Overpass query failed: {e}")
        return

    elements = data.get("elements", [])
    print(f"[+] Elements returned: {len(elements)}")

    if len(elements) == 0:
        print("[!] No elements found. Try adjusting keywords or checking the bbox.")
        return

    records = []
    seen = set()
    for i, elem in enumerate(elements):
        print(f"[+] Processing element {i+1}/{len(elements)}")
        rec = element_to_record(elem)
        key = (rec["name"] or "") + "|" + (rec["website"] or "")
        if key in seen:
            continue
        seen.add(key)
        
        if rec["website"]:
            print(f"    Scraping emails from: {rec['website']}")
            emails = scrape_emails_from_website(rec["website"])
            rec["emails_found"] = ";".join(emails) if emails else ""
        else:
            rec["emails_found"] = ""
            
        records.append(rec)
        time.sleep(0.3)  # Be nice to websites

    outfile = "osm_leads.csv"
    print(f"[+] Writing {len(records)} records to {outfile}")
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["osm_type","osm_id","name","website","phone","address","emails_found"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print("[+] Done. Open osm_leads.csv")

if __name__ == "__main__":
    run()