#!/usr/bin/env python3
"""
Smart start script for Railway deployment
Detects service type and starts appropriate process
"""

import os
import subprocess
import sys

def main():
    """Start appropriate service based on Railway service name"""
    
    # Get Railway service name from environment
    service_name = os.getenv('RAILWAY_SERVICE_NAME', '').lower()
    
    print(f"Railway service name: {service_name}")
    
    # Set up environment
    os.environ.setdefault('PYTHONPATH', '/app')
    
    if 'worker' in service_name:
        # Start Celery worker
        print("Starting Celery worker...")
        cmd = [
            'celery', 
            '-A', 'src.classifier.async_classifier.celery_app', 
            'worker', 
            '--loglevel=info',
            '--concurrency=2'
        ]
    else:
        # Start Flask web app (default)
        print("Starting Flask web app...")
        cmd = [
            'gunicorn', 
            '-w', '2', 
            '-b', '0.0.0.0:5000', 
            'src.app:app'
        ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Process failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Process stopped")
        sys.exit(0)

if __name__ == '__main__':
    main()
