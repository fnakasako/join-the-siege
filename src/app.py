from flask import Flask, request, jsonify
from src.classifier import classify_file
from src.classifier.categories import get_all_industries
import os
import asyncio
import time
from dotenv import load_dotenv

# Import async functionality
try:
    from src.async_classifier import (
        submit_classification_task,
        get_task_result,
        get_queue_statistics,
        health_check as async_health_check
    )
    ASYNC_ENABLED = True
except ImportError:
    ASYNC_ENABLED = False
    print("Warning: Async functionality not available. Install redis and celery dependencies.")

# Load environment variables
load_dotenv()

# Debug environment variables
print(f"Debug: OPENAI_API_KEY found in app.py: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
if os.getenv('OPENAI_API_KEY'):
    print(f"Debug: API key in app.py starts with: {os.getenv('OPENAI_API_KEY')[:10]}...")

app = Flask(__name__)

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff',  # Images and PDFs
    'doc', 'docx',  # Word documents
    'xls', 'xlsx',  # Excel spreadsheets
    'ppt', 'pptx',  # PowerPoint presentations
    'txt', 'csv'    # Text files
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/classify_file', methods=['POST'])
def classify_file_route():
    """Enhanced endpoint with industry parameter support"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed"}), 400

    # Get industry parameter from request (default to 'finance')
    industry = request.form.get('industry', 'finance').lower()
    
    # Validate industry
    available_industries = get_all_industries()
    if industry not in available_industries and industry != 'default':
        return jsonify({
            "error": f"Invalid industry. Available: {available_industries}"
        }), 400

    # Classify with industry context
    result = classify_file(file, industry=industry)
    
    return jsonify({
        "file_class": result.get('classification', 'unknown'),
        "confidence": result.get('confidence', 0.0),
        "industry": result.get('industry', industry),
        "reasoning": result.get('reasoning', ''),
        "metadata": result.get('metadata', {})
    }), 200

@app.route('/industries', methods=['GET'])
def get_industries():
    """Endpoint to get available industries"""
    return jsonify({
        "industries": get_all_industries()
    }), 200

@app.route('/categories/<industry>', methods=['GET'])
def get_categories(industry):
    """Endpoint to get categories for a specific industry"""
    try:
        from src.classifier.categories import get_categories_for_industry
        categories = get_categories_for_industry(industry)
        return jsonify({
            "industry": industry,
            "categories": categories
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/debug', methods=['GET'])
def debug_env():
    """Debug endpoint to check environment variables"""
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"DEBUG ENDPOINT: API key found: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"DEBUG ENDPOINT: API key starts with: {api_key[:10]}...")
    
    return jsonify({
        "api_key_found": bool(api_key),
        "api_key_prefix": api_key[:10] + "..." if api_key else None,
        "all_env_vars": dict(os.environ)
    }), 200

@app.route('/classify_file_async', methods=['POST'])
def classify_file_async_route():
    """Async classification endpoint with caching"""
    
    if not ASYNC_ENABLED:
        return jsonify({
            "error": "Async processing not available. Please install redis and celery dependencies."
        }), 503
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed"}), 400

    # Get industry parameter
    industry = request.form.get('industry', 'finance').lower()
    
    # Validate industry
    available_industries = get_all_industries()
    if industry not in available_industries and industry != 'default':
        return jsonify({
            "error": f"Invalid industry. Available: {available_industries}"
        }), 400

    # Read file data
    file_data = file.read()
    
    # Submit to queue for processing
    try:
        task_id = submit_classification_task(file_data, file.filename, industry)
        
        return jsonify({
            "task_id": task_id,
            "status": "processing",
            "estimated_time": "30-60 seconds",
            "check_url": f"/classification_result/{task_id}"
        }), 202
    except Exception as e:
        return jsonify({
            "error": f"Failed to submit classification task: {str(e)}"
        }), 500

@app.route('/classification_result/<task_id>', methods=['GET'])
def get_classification_result(task_id):
    """Get async classification result"""
    
    if not ASYNC_ENABLED:
        return jsonify({
            "error": "Async processing not available"
        }), 503
    
    try:
        result = get_task_result(task_id)
        
        if result['status'] == 'completed':
            return jsonify(result), 200
        elif result['status'] == 'failed':
            return jsonify(result), 500
        else:
            return jsonify(result), 202
            
    except Exception as e:
        return jsonify({
            "error": f"Failed to get task result: {str(e)}",
            "task_id": task_id
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancer"""
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "instance_id": os.getenv('INSTANCE_ID', 'unknown'),
        "version": "1.0.0"
    }
    
    # Check async system health if enabled
    if ASYNC_ENABLED:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async_health = loop.run_until_complete(async_health_check())
            loop.close()
            
            health_status["async_system"] = async_health
            
            if async_health["status"] != "healthy":
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["async_system"] = {"error": str(e)}
            health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes"""
    
    # Basic readiness checks
    checks = {
        "openai_key": bool(os.getenv('OPENAI_API_KEY')),
        "categories_loaded": True,  # Could add actual check
    }
    
    if ASYNC_ENABLED:
        try:
            # Quick Redis ping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async_health = loop.run_until_complete(async_health_check())
            loop.close()
            
            checks["redis"] = async_health["redis"]["healthy"]
            checks["celery"] = async_health["celery"]["healthy"]
        except Exception:
            checks["redis"] = False
            checks["celery"] = False
    
    all_ready = all(checks.values())
    
    return jsonify({
        "ready": all_ready,
        "checks": checks,
        "timestamp": time.time()
    }), 200 if all_ready else 503

@app.route('/metrics', methods=['GET'])
def metrics():
    """Metrics endpoint for monitoring"""
    
    metrics_data = {
        "timestamp": time.time(),
        "instance_id": os.getenv('INSTANCE_ID', 'unknown'),
        "uptime": time.time() - app.start_time if hasattr(app, 'start_time') else 0
    }
    
    if ASYNC_ENABLED:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            queue_stats = loop.run_until_complete(get_queue_statistics())
            loop.close()
            
            metrics_data["queue"] = queue_stats
        except Exception as e:
            metrics_data["queue_error"] = str(e)
    
    return jsonify(metrics_data), 200

@app.route('/debug-openai', methods=['GET'])
def debug_openai():
    """Debug endpoint to test OpenAI client initialization"""
    from openai import OpenAI
    
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"DEBUG OPENAI: API key found: {'Yes' if api_key else 'No'}")
    
    try:
        client = OpenAI(api_key=api_key)
        print("DEBUG OPENAI: Client initialized successfully")
        return jsonify({
            "client_initialized": True,
            "api_key_found": bool(api_key),
            "error": None
        }), 200
    except Exception as e:
        print(f"DEBUG OPENAI: Client initialization failed: {e}")
        print(f"DEBUG OPENAI: Exception type: {type(e).__name__}")
        return jsonify({
            "client_initialized": False,
            "api_key_found": bool(api_key),
            "error": str(e),
            "error_type": type(e).__name__
        }), 200


# Initialize app start time for metrics
app.start_time = time.time()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
