#!/usr/bin/env python3
"""
Enhanced Business Lead Extractor using OpenStreetMap + External Data Sources
- Modern interface-compatible lead generation tool
- Industry-specific targeting with comprehensive keywords
- Enhanced data collection with revenue estimation
- Email extraction and validation
- Professional CSV output with stats
"""

import requests
import time
import csv
import re
import json
import random
from urllib.parse import urlencode, urlparse
from datetime import datetime
import os

# CONFIGURATION
CITY = "New York, USA"
MAX_RESULTS = 250
SELECTED_INDUSTRIES = ["Technology & Software", "Data & Analytics", "Marketing & Advertising"]

# Enhanced industry mapping with comprehensive keywords
INDUSTRY_KEYWORDS = {
    'Technology & Software': [
        'software', 'tech', 'technology', 'app', 'saas', 'it', 'digital', 'cyber',
        'development', 'developer', 'programming', 'coding', 'startup', 'innovation'
    ],
    'Data & Analytics': [
        'data', 'analytics', 'business intelligence', 'big data', 'database', 
        'ai', 'ml', 'machine learning', 'artificial intelligence', 'analysis',
        'statistics', 'research', 'insights', 'metrics'
    ],
    'E-commerce & Retail': [
        'ecommerce', 'retail', 'online store', 'marketplace', 'shopping', 'commerce',
        'e-commerce', 'trade', 'sales', 'merchandise', 'fashion', 'goods'
    ],
    'Healthcare & Medical': [
        'healthcare', 'medical', 'health', 'clinic', 'hospital', 'pharma', 'biotech',
        'medicine', 'therapy', 'wellness', 'care', 'treatment', 'diagnostic'
    ],
    'Financial Services': [
        'finance', 'fintech', 'banking', 'investment', 'insurance', 'accounting',
        'financial', 'credit', 'loan', 'wealth', 'advisory', 'capital'
    ],
    'Marketing & Advertising': [
        'marketing', 'advertising', 'agency', 'digital marketing', 'seo', 'social media',
        'branding', 'promotion', 'campaign', 'creative', 'media', 'communications'
    ],
    'Consulting & Professional': [
        'consulting', 'professional services', 'advisory', 'consulting firm',
        'business consulting', 'strategy', 'management', 'expertise', 'solutions'
    ],
    'Manufacturing & Industrial': [
        'manufacturing', 'industrial', 'factory', 'production', 'engineering',
        'automotive', 'machinery', 'equipment', 'fabrication', 'assembly'
    ],
    'Real Estate & Construction': [
        'real estate', 'construction', 'property', 'building', 'architecture',
        'developer', 'contractor', 'residential', 'commercial', 'infrastructure'
    ],
    'Education & Training': [
        'education', 'training', 'school', 'university', 'learning', 'educational',
        'teaching', 'academic', 'course', 'certification', 'coaching'
    ],
    'Media & Entertainment': [
        'media', 'entertainment', 'broadcasting', 'publishing', 'gaming',
        'content', 'production', 'creative', 'film', 'music', 'streaming'
    ],
    'Food & Beverage': [
        'food', 'restaurant', 'catering', 'beverage', 'culinary', 'hospitality',
        'dining', 'kitchen', 'cuisine', 'bar', 'cafe', 'nutrition'
    ]
}

# API Configuration
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "BusinessLeadExtractor/2.0 (contact@example.com)"

HEADERS = {"User-Agent": USER_AGENT}

# Enhanced bbox fallback dictionary
HARDCODED_BBOX = {
    "New York, USA": (40.477399, -74.259090, 40.917577, -73.700272),
    "Los Angeles, USA": (33.7037, -118.6681, 34.3373, -118.1553),
    "Chicago, USA": (41.6445, -87.9401, 42.0230, -87.5240),
    "London, UK": (51.286760, -0.510375, 51.691874, 0.334015),
    "Paris, France": (48.815573, 2.224199, 48.902145, 2.469921),
    "Berlin, Germany": (52.3382, 13.0883, 52.6755, 13.7611),
    "Tokyo, Japan": (35.5281, 139.3184, 35.8617, 139.8728),
    "Sydney, Australia": (-34.1692, 150.5023, -33.5780, 151.3431),
    "Toronto, Canada": (43.5810, -79.6390, 43.8554, -79.1168),
    "Dubai, UAE": (24.9526, 54.9297, 25.3464, 55.5731),
    "Singapore": (1.1496, 103.5675, 1.4784, 104.1147),
    "Mumbai, India": (18.8800, 72.7800, 19.2800, 72.9800),
    "São Paulo, Brazil": (-23.8277, -46.8754, -23.3565, -46.3657),
    "Mexico City, Mexico": (19.2465, -99.3570, 19.5921, -98.9462),
    "Karachi, Pakistan": (24.789, 66.845, 25.021, 67.157),
    "Istanbul, Turkey": (40.8023, 28.5900, 41.2061, 29.1815)
}

# Revenue estimation patterns
REVENUE_INDICATORS = {
    'enterprise': '$50M+',
    'corporation': '$25M-50M',
    'inc': '$10M-25M',
    'llc': '$5M-10M',
    'ltd': '$1M-5M',
    'co': '$1M-5M'
}

class BusinessLeadExtractor:
    def __init__(self, city, industries, max_results=250):
        self.city = city
        self.industries = industries if isinstance(industries, list) else [industries]
        self.max_results = max_results
        self.results = []
        self.stats = {
            'total_found': 0,
            'with_emails': 0,
            'with_websites': 0,
            'with_phones': 0,
            'with_addresses': 0
        }

    def get_bbox_for_city(self):
        """Get bounding box for the specified city"""
        try:
            params = {"q": self.city, "format": "json", "limit": 1}
            r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            if not data:
                raise RuntimeError("City not found via Nominatim.")
            
            bbox = data[0]["boundingbox"]  # [south, north, west, east] as strings
            return float(bbox[0]), float(bbox[2]), float(bbox[1]), float(bbox[3])
            
        except Exception as e:
            print(f"[!] Nominatim failed ({e}), using fallback bbox for {self.city}")
            if self.city in HARDCODED_BBOX:
                return HARDCODED_BBOX[self.city]
            else:
                raise SystemExit(f"No fallback bbox available for {self.city}. Please add it to HARDCODED_BBOX.")

    def build_overpass_query(self, south, west, north, east):
        """Build comprehensive Overpass query for multiple industries"""
        all_keywords = []
        for industry in self.industries:
            if industry in INDUSTRY_KEYWORDS:
                all_keywords.extend(INDUSTRY_KEYWORDS[industry])
        
        # Remove duplicates and escape special characters
        unique_keywords = list(set(all_keywords))
        escaped_keywords = [re.escape(k.lower()) for k in unique_keywords]
        kw_regex = "|".join(escaped_keywords)
        
        # Enhanced query with multiple business types
        query = f"""[out:json][timeout:120];
(
  // Business names containing keywords
  node["name"~"{kw_regex}",i]({south},{west},{north},{east});
  way["name"~"{kw_regex}",i]({south},{west},{north},{east});
  relation["name"~"{kw_regex}",i]({south},{west},{north},{east});
  
  // Office types
  node["office"~"company|business|it|financial|consulting|marketing",i]({south},{west},{north},{east});
  way["office"~"company|business|it|financial|consulting|marketing",i]({south},{west},{north},{east});
  relation["office"~"company|business|it|financial|consulting|marketing",i]({south},{west},{north},{east});
  
  // Shop types
  node["shop"~"computer|electronics|mobile_phone|software",i]({south},{west},{north},{east});
  way["shop"~"computer|electronics|mobile_phone|software",i]({south},{west},{north},{east});
  
  // Amenity types
  node["amenity"~"bank|clinic|hospital|restaurant|cafe|school|university",i]({south},{west},{north},{east});
  way["amenity"~"bank|clinic|hospital|restaurant|cafe|school|university",i]({south},{west},{north},{east});
  
  // Industrial and commercial
  node["industrial"]({south},{west},{north},{east});
  way["industrial"]({south},{west},{north},{east});
  node["commercial"]({south},{west},{north},{east});
  way["commercial"]({south},{west},{north},{east});
);
out center {self.max_results};"""
        
        return query

    def query_overpass(self, query):
        """Execute Overpass API query with enhanced error handling"""
        print(f"[+] Querying Overpass API...")
        try:
            response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=180)
            
            if response.status_code == 429:
                print("[!] Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=180)
            
            if response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}: {response.text[:200]}...")
                return {"elements": []}
            
            return response.json()
            
        except Exception as e:
            print(f"[ERROR] Overpass query failed: {e}")
            return {"elements": []}

    def estimate_revenue(self, name, tags):
        """Estimate company revenue based on name and tags"""
        if not name:
            return "Undisclosed"
        
        name_lower = name.lower()
        
        # Check for revenue indicators in company name
        for indicator, revenue_range in REVENUE_INDICATORS.items():
            if indicator in name_lower:
                return revenue_range
        
        # Check for enterprise indicators
        enterprise_indicators = ['enterprise', 'corporation', 'international', 'global', 'holdings']
        if any(indicator in name_lower for indicator in enterprise_indicators):
            return '$25M-50M'
        
        # Check business type in tags
        business_type = tags.get('office', '')
        if business_type == 'company':
            return '$10M-25M'
        elif business_type == 'business':
            return '$5M-10M'
        
        # Default estimation based on presence of website
        if tags.get('website') or tags.get('contact:website'):
            return '$1M-5M'
        
        return 'Undisclosed'

    def determine_industry(self, name, tags):
        """Determine most likely industry based on name and tags"""
        if not name:
            return "Other"
        
        name_lower = name.lower()
        
        # Check against industry keywords
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            if any(keyword.lower() in name_lower for keyword in keywords):
                return industry
        
        # Check tags for industry hints
        office_type = tags.get('office', '').lower()
        shop_type = tags.get('shop', '').lower()
        amenity_type = tags.get('amenity', '').lower()
        
        if office_type in ['it', 'software']:
            return 'Technology & Software'
        elif shop_type in ['computer', 'electronics', 'software']:
            return 'Technology & Software'
        elif amenity_type in ['bank']:
            return 'Financial Services'
        elif amenity_type in ['clinic', 'hospital']:
            return 'Healthcare & Medical'
        elif amenity_type in ['restaurant', 'cafe']:
            return 'Food & Beverage'
        elif amenity_type in ['school', 'university']:
            return 'Education & Training'
        
        return "Other"

    def scrape_emails_from_website(self, url):
        """Enhanced email scraping with better patterns and validation"""
        if not url:
            return []
        
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Enhanced email regex pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
            emails = set(re.findall(email_pattern, response.text, re.IGNORECASE))
            
            # Filter out common false positives
            filtered_emails = []
            exclude_patterns = ['example.com', 'test.com', 'lorem.ipsum', '@sentry.io', '@google-analytics.com']
            
            for email in emails:
                email_lower = email.lower()
                if not any(pattern in email_lower for pattern in exclude_patterns):
                    filtered_emails.append(email)
            
            return filtered_emails[:3]  # Return top 3 emails
            
        except Exception as e:
            print(f"[DEBUG] Email scraping failed for {url}: {e}")
            return []

    def process_element(self, elem):
        """Process OSM element into business lead record"""
        tags = elem.get("tags", {})
        name = tags.get("name", "").strip()
        
        if not name:
            return None
        
        # Extract contact information
        website = tags.get("website") or tags.get("contact:website") or tags.get("url")
        phone = tags.get("phone") or tags.get("contact:phone") or tags.get("telephone")
        
        # Build address
        address_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:city", ""),
            tags.get("addr:postcode", ""),
            tags.get("addr:country", "")
        ]
        address = ", ".join(filter(None, address_parts)) or tags.get("addr:full", "")
        
        # Determine industry and estimate revenue
        industry = self.determine_industry(name, tags)
        revenue = self.estimate_revenue(name, tags)
        
        # Create record
        record = {
            "osm_type": elem.get("type", ""),
            "osm_id": elem.get("id", ""),
            "name": name,
            "industry": industry,
            "location": address or f"{self.city}",
            "website": website or "",
            "phone": phone or "",
            "revenue": revenue,
            "emails_found": "",
            "extraction_date": datetime.now().strftime("%Y-%m-%d"),
            "tags": json.dumps(tags, separators=(',', ':'))
        }
        
        return record

    def extract_leads(self):
        """Main extraction process"""
        print(f"[+] Starting lead extraction for {self.city}")
        print(f"[+] Target industries: {', '.join(self.industries)}")
        print(f"[+] Maximum results: {self.max_results}")
        
        # Get city boundaries
        try:
            south, west, north, east = self.get_bbox_for_city()
            print(f"[+] City bbox: {south:.4f}, {west:.4f}, {north:.4f}, {east:.4f}")
        except Exception as e:
            print(f"[ERROR] Could not get city boundaries: {e}")
            return []
        
        # Build and execute query
        query = self.build_overpass_query(south, west, north, east)
        data = self.query_overpass(query)
        
        elements = data.get("elements", [])
        print(f"[+] Found {len(elements)} potential leads")
        
        if not elements:
            print("[!] No elements found. Try adjusting industries or location.")
            return []
        
        # Process elements
        processed_leads = []
        seen_names = set()
        
        for i, elem in enumerate(elements):
            if len(processed_leads) >= self.max_results:
                break
                
            print(f"[+] Processing lead {i+1}/{len(elements)}")
            
            record = self.process_element(elem)
            if not record or not record["name"]:
                continue
            
            # Avoid duplicates
            name_key = record["name"].lower().strip()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)
            
            # Extract emails from website
            if record["website"]:
                print(f"    Extracting emails from: {record['website']}")
                emails = self.scrape_emails_from_website(record["website"])
                record["emails_found"] = "; ".join(emails) if emails else ""
                if emails:
                    self.stats['with_emails'] += 1
            
            processed_leads.append(record)
            
            # Update stats
            if record["website"]:
                self.stats['with_websites'] += 1
            if record["phone"]:
                self.stats['with_phones'] += 1
            if record["location"] and record["location"] != self.city:
                self.stats['with_addresses'] += 1
            
            # Be respectful to websites
            time.sleep(0.5)
        
        self.results = processed_leads
        self.stats['total_found'] = len(processed_leads)
        return processed_leads

    def save_to_csv(self, filename=None):
        """Save results to CSV file with enhanced format"""
        if not self.results:
            print("[!] No results to save.")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_city = re.sub(r'[^a-zA-Z0-9]', '_', self.city.lower())
            filename = f"business_leads_{safe_city}_{timestamp}.csv"
        
        fieldnames = [
            "name", "industry", "location", "email", "revenue", 
            "website", "phone", "extraction_date"
        ]
        
        print(f"[+] Saving {len(self.results)} leads to {filename}")
        
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in self.results:
                # Prepare row for CSV (flatten emails)
                csv_row = {
                    "name": record["name"],
                    "industry": record["industry"],
                    "location": record["location"],
                    "email": record["emails_found"],
                    "revenue": record["revenue"],
                    "website": record["website"],
                    "phone": record["phone"],
                    "extraction_date": record["extraction_date"]
                }
                writer.writerow(csv_row)
        
        print(f"[+] Results saved to {filename}")
        return filename

    def print_stats(self):
        """Print extraction statistics"""
        print("\n" + "="*60)
        print("📊 EXTRACTION STATISTICS")
        print("="*60)
        print(f"🎯 Total Companies Found: {self.stats['total_found']}")
        print(f"📧 With Email Addresses: {self.stats['with_emails']} ({(self.stats['with_emails']/max(self.stats['total_found'], 1)*100):.1f}%)")
        print(f"🌐 With Websites: {self.stats['with_websites']} ({(self.stats['with_websites']/max(self.stats['total_found'], 1)*100):.1f}%)")
        print(f"📞 With Phone Numbers: {self.stats['with_phones']} ({(self.stats['with_phones']/max(self.stats['total_found'], 1)*100):.1f}%)")
        print(f"🏢 With Detailed Addresses: {self.stats['with_addresses']} ({(self.stats['with_addresses']/max(self.stats['total_found'], 1)*100):.1f}%)")
        print(f"🏭 Target Industries: {', '.join(self.industries)}")
        print(f"📍 Location: {self.city}")
        print("="*60)

def main():
    """Main execution function with enhanced interface"""
    print("🎯 Enhanced Business Lead Extractor")
    print("="*50)
    
    # Get user input or use defaults
    city = input(f"Enter target city [{CITY}]: ").strip() or CITY
    
    print("\nAvailable Industries:")
    for i, industry in enumerate(INDUSTRY_KEYWORDS.keys(), 1):
        print(f"{i:2d}. {industry}")
    
    print(f"\nDefault selection: {', '.join(SELECTED_INDUSTRIES)}")
    use_default = input("Use default industry selection? (y/n) [y]: ").strip().lower()
    
    if use_default != 'n':
        industries = SELECTED_INDUSTRIES
    else:
        industry_input = input("Enter industry numbers (comma-separated): ").strip()
        if industry_input:
            try:
                industry_list = list(INDUSTRY_KEYWORDS.keys())
                selected_indices = [int(x.strip()) - 1 for x in industry_input.split(",")]
                industries = [industry_list[i] for i in selected_indices if 0 <= i < len(industry_list)]
            except (ValueError, IndexError):
                print("[!] Invalid selection. Using default industries.")
                industries = SELECTED_INDUSTRIES
        else:
            industries = SELECTED_INDUSTRIES
    
    max_results_input = input(f"Maximum results [{MAX_RESULTS}]: ").strip()
    max_results = int(max_results_input) if max_results_input.isdigit() else MAX_RESULTS
    
    # Initialize and run extractor
    extractor = BusinessLeadExtractor(city, industries, max_results)
    
    try:
        leads = extractor.extract_leads()
        
        if leads:
            extractor.print_stats()
            filename = extractor.save_to_csv()
            print(f"\n✅ Extraction complete! Check {filename} for results.")
        else:
            print("\n❌ No leads found. Try adjusting your parameters.")
            
    except KeyboardInterrupt:
        print("\n[!] Extraction interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")

if __name__ == "__main__":
    main()