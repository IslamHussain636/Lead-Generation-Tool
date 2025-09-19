#!/usr/bin/env python3
"""
Flask API Backend for Business Lead Extractor
Connects the HTML frontend to the Python lead extraction script
"""

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import json
import threading
import uuid
import os
from datetime import datetime
import csv
import io

# Import the enhanced lead extractor
from enhanced_lead_extractor import BusinessLeadExtractor, INDUSTRY_KEYWORDS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Store extraction jobs in memory (use Redis/database in production)
extraction_jobs = {}

class ExtractionJob:
    def __init__(self, job_id, city, industries, max_results):
        self.job_id = job_id
        self.city = city
        self.industries = industries
        self.max_results = max_results
        self.status = 'pending'  # pending, running, completed, failed
        self.progress = 0
        self.results = []
        self.stats = {}
        self.error_message = None
        self.created_at = datetime.now()
        self.completed_at = None

def run_extraction(job):
    """Run extraction in background thread"""
    try:
        job.status = 'running'
        job.progress = 10
        
        # Initialize extractor
        extractor = BusinessLeadExtractor(job.city, job.industries, job.max_results)
        job.progress = 20
        
        # Run extraction
        leads = extractor.extract_leads()
        job.progress = 90
        
        # Store results
        job.results = leads
        job.stats = extractor.stats
        job.status = 'completed'
        job.progress = 100
        job.completed_at = datetime.now()
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.progress = 0

@app.route('/')
def index():
    """Serve the HTML frontend"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>Business Lead Extractor API</h1>
        <p>API Server is running successfully!</p>
        <p>Available endpoints:</p>
        <ul>
            <li><a href="/api/health">/api/health</a> - Health check</li>
            <li><a href="/api/industries">/api/industries</a> - Get available industries</li>
            <li>POST /api/extract - Start extraction</li>
            <li>GET /api/status/{job_id} - Check job status</li>
            <li>GET /api/results/{job_id} - Get results</li>
            <li>GET /api/download/{job_id} - Download CSV</li>
        </ul>
        <p><strong>Note:</strong> Place your index.html file in the same directory as this script to serve the frontend.</p>
        """

@app.route('/api/industries', methods=['GET'])
def get_industries():
    """Get available industries"""
    return jsonify({
        'success': True,
        'industries': list(INDUSTRY_KEYWORDS.keys())
    })

@app.route('/api/extract', methods=['POST'])
def start_extraction():
    """Start lead extraction job"""
    try:
        data = request.get_json()
        
        # Validate input
        city = data.get('city', '').strip()
        industries = data.get('industries', [])
        max_results = int(data.get('maxResults', 250))
        
        if not city:
            return jsonify({'success': False, 'error': 'City is required'}), 400
        
        if not industries:
            return jsonify({'success': False, 'error': 'At least one industry must be selected'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        job = ExtractionJob(job_id, city, industries, max_results)
        extraction_jobs[job_id] = job
        
        # Start extraction in background thread
        thread = threading.Thread(target=run_extraction, args=(job,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Extraction started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get extraction job status"""
    job = extraction_jobs.get(job_id)
    
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
        response.update({
            'completed_at': job.completed_at.isoformat(),
            'results_count': len(job.results),
            'stats': job.stats
        })
    elif job.status == 'failed':
        response['error_message'] = job.error_message
    
    return jsonify(response)

@app.route('/api/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get extraction results"""
    job = extraction_jobs.get(job_id)
    
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed yet'}), 400
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'results': job.results,
        'stats': job.stats
    })

@app.route('/api/download/<job_id>', methods=['GET'])
def download_csv(job_id):
    """Download results as CSV"""
    job = extraction_jobs.get(job_id)
    
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed yet'}), 400
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = ['name', 'industry', 'location', 'email', 'revenue', 'website', 'phone', 'extraction_date']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for result in job.results:
        csv_row = {
            'name': result.get('name', ''),
            'industry': result.get('industry', ''),
            'location': result.get('location', ''),
            'email': result.get('emails_found', ''),
            'revenue': result.get('revenue', ''),
            'website': result.get('website', ''),
            'phone': result.get('phone', ''),
            'extraction_date': result.get('extraction_date', '')
        }
        writer.writerow(csv_row)
    
    # Convert to bytes
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()
    
    # Generate filename
    safe_city = job.city.replace(' ', '_').replace(',', '')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'business_leads_{safe_city}_{timestamp}.csv'
    
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
        'message': 'Lead Extractor API is running',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Lead Extractor API Server...")
    print("📡 API will be available at: http://localhost:5000")
    print("🔗 Frontend will be served at: http://localhost:5000")
    print("📋 API endpoints available at: http://localhost:5000/api/")
    print("="*60)
    
    # Run Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)