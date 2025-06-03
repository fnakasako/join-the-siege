from flask import Flask, request, jsonify
from src.classifier import classify_file
from src.classifier.categories import get_all_industries
import os
import time
from dotenv import load_dotenv

# Import async classifier
from src.async_classifier import (
    submit_classification_task,
    get_task_result
)
ASYNC_ENABLED = True


# Load environment variables
load_dotenv()

app = Flask(__name__)

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff',  # Images and PDFs
    'doc', 'docx',  # Word documents
    'xls', 'xlsx',  # Excel spreadsheets
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/classify_file_async', methods=['POST'])
def classify_file_async_route():
    """Async classification endpoint"""
    
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

# Initialize app start time for metrics
app.start_time = time.time()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
