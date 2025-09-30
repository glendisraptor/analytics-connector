from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import os
from pathlib import Path
import PyPDF2
from PIL import Image
import pytesseract
import requests
import re

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Groq API Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def hash_fields(field_names):
    """Generate hash from field names"""
    field_str = json.dumps(sorted(field_names))
    return str(abs(hash(field_str)) % (10 ** 10))

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

def extract_text_from_image(file_path):
    """Extract text from image using OCR"""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Image extraction error: {e}")
        return ""

def extract_with_groq(document_text, fields):
    """Use Groq API to extract structured data based on field configuration"""
    
    # Build field descriptions
    field_descriptions = []
    for field in fields:
        field_descriptions.append(f"  - {field['name']}: {field['type']}")
    
    field_list = "\n".join(field_descriptions)
    
    # Build expected JSON structure
    expected_json = "{\n"
    for i, field in enumerate(fields):
        expected_json += f'  "{field["name"]}": "value"'
        if i < len(fields) - 1:
            expected_json += ","
        expected_json += "\n"
    expected_json += "}"
    
    # Truncate document text to fit in context
    max_text_length = 4000
    truncated_text = document_text[:max_text_length]
    if len(document_text) > max_text_length:
        truncated_text += "\n... (document truncated)"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are a data extraction assistant. Extract information from documents and return ONLY valid JSON. Do not include any explanations, markdown formatting, or additional text."
            },
            {
                "role": "user",
                "content": f"""Extract the following fields from this document:

{field_list}

Document text:
{truncated_text}

Return ONLY this JSON format (use null for missing values):
{expected_json}"""
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
        "top_p": 1,
        "stream": False
    }
    
    try:
        print("Calling Groq API...")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            print(f"Groq response: {content}")
            
            # Clean up response - remove markdown code blocks
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Try to extract JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted_data = json.loads(json_str)
                
                # Ensure all fields are present
                result_data = {}
                for field in fields:
                    result_data[field['name']] = extracted_data.get(field['name'], None)
                
                print(f"Extracted data: {result_data}")
                return result_data
        
        elif response.status_code == 401:
            print("Groq API authentication failed. Check your API key.")
            return extract_with_regex(document_text, fields)
        
        else:
            print(f"Groq API error: {response.status_code} - {response.text}")
            return extract_with_regex(document_text, fields)
        
        # Fallback to regex if JSON parsing fails
        return extract_with_regex(document_text, fields)
        
    except requests.exceptions.Timeout:
        print("Groq API timeout")
        return extract_with_regex(document_text, fields)
    except Exception as e:
        print(f"Groq API error: {e}")
        return extract_with_regex(document_text, fields)

def extract_with_regex(text, fields):
    """Fallback: Pattern-based extraction for each configured field"""
    extracted = {}
    
    for field in fields:
        field_name = field['name']
        field_type = field['type']
        value = None
        
        # Search for the field name in the text
        field_pattern = re.compile(rf'{re.escape(field_name)}[:\s]*([^\n]+)', re.IGNORECASE)
        field_match = field_pattern.search(text)
        
        if field_match:
            potential_value = field_match.group(1).strip()
            
            # Clean based on type
            if field_type == 'currency':
                currency_match = re.search(r'[R$€£]?\s*[\d,]+\.?\d*', potential_value)
                value = currency_match.group().strip() if currency_match else potential_value
                
            elif field_type == 'number':
                number_match = re.search(r'[\d,]+\.?\d*', potential_value)
                value = number_match.group().strip() if number_match else potential_value
                
            elif field_type == 'email':
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', potential_value)
                value = email_match.group() if email_match else potential_value
                
            elif field_type == 'date':
                date_match = re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}', potential_value)
                value = date_match.group() if date_match else potential_value
                
            else:
                value = potential_value[:100]
        
        else:
            # Try generic patterns based on type
            if field_type == 'currency':
                matches = re.findall(r'[R$€£]\s*[\d,]+\.?\d{2}', text)
                value = matches[0] if matches else None
                
            elif field_type == 'email':
                matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                value = matches[0] if matches else None
                
            elif field_type == 'date':
                matches = re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', text)
                value = matches[0] if matches else None
        
        extracted[field_name] = value
    
    return extracted

def map_extracted_to_field_ids(extracted_data, fields):
    """Map extracted data to field IDs for the frontend"""
    mapped = {}
    
    for field in fields:
        field_id = field['id']
        field_name = field['name']
        mapped[field_id] = extracted_data.get(field_name, None)
    
    return mapped

@app.route('/api/extract', methods=['POST'])
def extract_document():
    """
    Extract data from document based on table configuration
    
    Expected payload:
    - file: The document file (PDF or image)
    - table: JSON object with table configuration
    - model: Optional model identifier
    """
    try:
        # Validate file upload
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400
        
        # Parse table configuration
        table_config_str = request.form.get('table')
        if not table_config_str:
            return jsonify({"error": "No table configuration provided"}), 400
        
        try:
            table_config = json.loads(table_config_str)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid table configuration JSON"}), 400
        
        # Validate table configuration
        if 'fields' not in table_config or not table_config['fields']:
            return jsonify({"error": "No fields configured in table"}), 400
        
        fields = table_config['fields']
        table_id = table_config.get('id', 'unknown')
        table_name = table_config.get('name', 'Unknown Table')
        model_id = request.form.get('model', 'llama-3.1-8b-instant')
        
        print(f"\n{'='*60}")
        print(f"Processing extraction for table: {table_name}")
        print(f"Fields to extract: {[f['name'] for f in fields]}")
        print(f"{'='*60}\n")
        
        # Save uploaded file
        field_names = [f['name'] for f in fields]
        fields_hash = hash_fields(field_names)
        
        filename = file.filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{fields_hash}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        file.save(file_path)
        
        print(f"File saved to: {file_path}")
        
        # Extract text from document
        file_extension = Path(filename).suffix.lower()
        
        if file_extension == '.pdf':
            document_text = extract_text_from_pdf(file_path)
        elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            document_text = extract_text_from_image(file_path)
        else:
            return jsonify({"error": f"Unsupported file type: {file_extension}"}), 400
        
        if not document_text:
            return jsonify({"error": "Failed to extract text from document"}), 500
        
        print(f"Extracted {len(document_text)} characters from document")
        
        # Extract fields using Groq
        extracted_by_name = extract_with_groq(document_text, fields)
        
        # Map to field IDs
        mapped_fields = map_extracted_to_field_ids(extracted_by_name, fields)
        
        print(f"\nFinal mapped fields: {mapped_fields}\n")
        
        # Prepare response
        result = {
            "fields": mapped_fields,
            "source": {
                "path": file_path,
                "filename": filename
            },
            "model_id": model_id,
            "table_id": table_id,
            "table_name": table_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save result
        result_path = os.path.join(RESULTS_FOLDER, f"{safe_filename}.json")
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✓ Extraction complete. Result saved to: {result_path}\n")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"✗ Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/poll', methods=['GET'])
def poll_result():
    """Poll for extraction result by filename"""
    try:
        filename = request.args.get('filename')
        
        if not filename:
            return jsonify({"error": "Missing filename parameter"}), 400
        
        # Search for result file
        for result_file in os.listdir(RESULTS_FOLDER):
            if filename in result_file and result_file.endswith('.json'):
                result_path = os.path.join(RESULTS_FOLDER, result_file)
                with open(result_path, 'r') as f:
                    result = json.load(f)
                return jsonify(result), 200
        
        return jsonify({"status": "not_ready"}), 403
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    api_key_configured = GROQ_API_KEY and GROQ_API_KEY != 'your_groq_api_key_here'
    
    return jsonify({
        "status": "healthy",
        "extraction_method": "groq",
        "api_configured": api_key_configured,
        "model": "llama-3.1-8b-instant"
    }), 200

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Document Extraction API with Groq")
    print("="*60)
    
    if GROQ_API_KEY == 'your_groq_api_key_here':
        print("\n⚠️  WARNING: Groq API key not configured!")
        print("Set GROQ_API_KEY environment variable or update the code.")
        print("Get your key from: https://console.groq.com\n")
    else:
        print("\n✓ Groq API key configured")
    
    print(f"✓ Upload folder: {UPLOAD_FOLDER}")
    print(f"✓ Results folder: {RESULTS_FOLDER}")
    print("\nStarting server on http://0.0.0.0:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')