#!/usr/bin/env python3
"""
Flask API for Google Maps Business Scraper
⚠️ Educational use only - scraping Google Maps may violate Terms of Service.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import threading
import uuid
import os
import io
import csv
from datetime import datetime
import time

# Import your Google Maps scraper
from google_map_business import MapsToWebsiteScraper

app = Flask(__name__)
CORS(app)

# Store scraping jobs in memory
scraping_jobs = {}

class ScrapingJob:
    def __init__(self, job_id, location, country, state, business_type, max_results):
        self.job_id = job_id
        self.location = location
        self.country = country
        self.state = state
        self.business_type = business_type
        self.max_results = max_results
        self.status = 'pending'  # pending, running, completed, failed
        self.progress = 0
        self.results = []
        self.error_message = None
        self.created_at = datetime.now()
        self.completed_at = None

def run_scraping_job(job):
    """Run scraping in background thread"""
    try:
        job.status = 'running'
        job.progress = 10
        
        # Build query string
        if job.state and job.country:
            query = f"{job.business_type} in {job.location}, {job.state}, {job.country}"
        elif job.country:
            query = f"{job.business_type} in {job.location}, {job.country}"
        else:
            query = f"{job.business_type} in {job.location}"
        
        print(f"[Job {job.job_id}] Starting scrape: {query}")
        
        # Initialize scraper with website visiting enabled
        scraper = MapsToWebsiteScraper(headless=True, visit_websites=True)
        job.progress = 20
        
        try:
            # Set max results
            scraper.set_max_results(job.max_results)
            
            # Search on maps
            scraper.search_on_maps(query)
            job.progress = 40
            
            # Extract data with progress updates
            results = scraper.scroll_hover_and_extract()
            job.progress = 90
            
            # Clean results - ensure all required fields exist
            cleaned_results = []
            for result in results:
                cleaned_result = {
                    'name': result.get('name', ''),
                    'rating': result.get('rating', ''),
                    'category': result.get('category', ''),
                    'address': result.get('address', ''),
                    'phone': result.get('phone', ''),
                    'website': result.get('website', ''),
                    'email': result.get('email', ''),
                    'linkedin': result.get('linkedin', '')
                }
                cleaned_results.append(cleaned_result)
            
            job.results = cleaned_results
            job.status = 'completed'
            job.progress = 100
            job.completed_at = datetime.now()
            
            # Print summary statistics
            total_results = len(cleaned_results)
            with_emails = sum(1 for r in cleaned_results if r.get('email'))
            with_websites = sum(1 for r in cleaned_results if r.get('website'))
            with_linkedin = sum(1 for r in cleaned_results if r.get('linkedin'))
            
            print(f"[Job {job.job_id}] Completed: {total_results} results")
            print(f"[Job {job.job_id}] Statistics: {with_emails} emails, {with_websites} websites, {with_linkedin} LinkedIn")
            
        finally:
            scraper.close()
            
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.progress = 0
        print(f"[Job {job.job_id}] Failed: {e}")

@app.route('/')
def index():
    """Serve the HTML frontend"""
    try:
        with open('gamp_forntend.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>Google Maps Scraper API</h1>
        <p>API Server is running successfully!</p>
        <p>Available endpoints:</p>
        <ul>
            <li><a href="/api/health">/api/health</a> - Health check</li>
            <li><a href="/api/countries">/api/countries</a> - Get countries</li>
            <li><a href="/api/business-types">/api/business-types</a> - Get business types</li>
            <li>POST /api/scrape - Start scraping</li>
            <li>GET /api/status/{job_id} - Check job status</li>
            <li>GET /api/results/{job_id} - Get results</li>
            <li>GET /api/download/{job_id} - Download CSV</li>
        </ul>
        <p><strong>Note:</strong> Place your gamp_forntend.html file in the same directory as this script.</p>
        <p><strong>Warning:</strong> This scraper may violate Google Maps Terms of Service.</p>
        <p><strong>Features:</strong> Now includes email extraction from business websites!</p>
        """

@app.route('/api/countries', methods=['GET'])
def get_countries():
    """Get list of supported countries"""
    countries = [
        "USA", "Canada", "United Kingdom", "Australia", "Germany", 
        "France", "Italy", "Spain", "Netherlands", "Sweden",
        "India", "Japan", "South Korea", "Singapore", "UAE",
        "Brazil", "Mexico", "Argentina", "South Africa", "Pakistan"
    ]
    return jsonify({
        'success': True,
        'countries': countries
    })

@app.route('/api/business-types', methods=['GET'])
def get_business_types():
    """Get list of common business types"""
    business_types = [
        "Software companies", "Tech startups", "Digital agencies",
        "Marketing agencies", "Consulting firms", "Law firms",
        "Accounting firms", "Real estate agencies", "Construction companies",
        "Healthcare clinics", "Dental practices", "Fitness centers",
        "Restaurants", "Cafes", "Retail stores", "E-commerce businesses",
        "Manufacturing companies", "Financial services", "Insurance agencies",
        "Educational institutions", "Non-profit organizations", "Media companies"
    ]
    return jsonify({
        'success': True,
        'business_types': business_types
    })

@app.route('/api/scrape', methods=['POST'])
def start_scraping():
    """Start scraping job"""
    try:
        data = request.get_json()
        
        # Validate input
        location = data.get('location', '').strip()
        country = data.get('country', '').strip()
        state = data.get('state', '').strip()
        business_type = data.get('business_type', '').strip()
        max_results = int(data.get('max_results', 50))
        
        if not location:
            return jsonify({'success': False, 'error': 'Location is required'}), 400
        
        if not business_type:
            return jsonify({'success': False, 'error': 'Business type is required'}), 400
        
        if max_results not in [10, 20, 50, 80, 100]:
            return jsonify({'success': False, 'error': 'Invalid max_results value'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        job = ScrapingJob(job_id, location, country, state, business_type, max_results)
        scraping_jobs[job_id] = job
        
        # Start scraping in background thread
        thread = threading.Thread(target=run_scraping_job, args=(job,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Scraping started with email extraction enabled'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get scraping job status"""
    job = scraping_jobs.get(job_id)
    
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    response = {
        'success': True,
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'created_at': job.created_at.isoformat(),
    }
    
    if job.status == 'completed':
        # Add statistics
        total_results = len(job.results)
        with_emails = sum(1 for r in job.results if r.get('email'))
        with_websites = sum(1 for r in job.results if r.get('website'))
        
        response.update({
            'completed_at': job.completed_at.isoformat(),
            'results_count': total_results,
            'emails_found': with_emails,
            'websites_found': with_websites
        })
    elif job.status == 'failed':
        response['error_message'] = job.error_message
    
    return jsonify(response)

@app.route('/api/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get scraping results"""
    job = scraping_jobs.get(job_id)
    
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed yet'}), 400
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'results': job.results,
        'statistics': {
            'total': len(job.results),
            'with_emails': sum(1 for r in job.results if r.get('email')),
            'with_websites': sum(1 for r in job.results if r.get('website')),
            'with_linkedin': sum(1 for r in job.results if r.get('linkedin'))
        }
    })

@app.route('/api/download/<job_id>', methods=['GET'])
def download_csv(job_id):
    """Download results as CSV"""
    job = scraping_jobs.get(job_id)
    
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed yet'}), 400
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = ['name', 'rating', 'category', 'address', 'phone', 'website', 'email', 'linkedin']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for result in job.results:
        writer.writerow({field: result.get(field, '') for field in fieldnames})
    
    # Convert to bytes
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()
    
    # Generate filename
    safe_location = job.location.replace(' ', '_').replace(',', '')
    safe_business = job.business_type.replace(' ', '_').replace(',', '')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'gmaps_businesses_{safe_location}_{safe_business}_{timestamp}.csv'
    
    return send_file(
        mem,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Google Maps Scraper API is running',
        'features': ['Email extraction from websites', 'LinkedIn profile detection'],
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("⚠️  WARNING: This scraper may violate Google Maps Terms of Service")
    print("🚀 Starting Google Maps Scraper API with Email Extraction...")
    print("🌐 Frontend will be served at: http://localhost:5000")
    print("🔗 API endpoints available at: http://localhost:5000/api/")
    print("📧 Email extraction from business websites: ENABLED")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)