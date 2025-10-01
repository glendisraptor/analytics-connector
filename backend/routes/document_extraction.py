"""
Document Extraction Routes
Handles document table configuration and extraction operations
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from models import DocumentTable, DocumentField, DocumentResult, AuditLog
from datetime import datetime
import os
import json
import re
from pathlib import Path
import hashlib

# Import extraction utilities
import PyPDF2
from PIL import Image
import pytesseract
import requests

document_extraction_bp = Blueprint('document_extraction', __name__)

# Extraction helper functions
def hash_fields(field_names):
    """Generate a stable hash from field names list"""
    field_str = json.dumps(sorted(field_names))
    return str(abs(hash(field_str)) % (10 ** 10))

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text).strip()
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

def extract_with_regex(text, fields):
    """Fallback extraction using simple regex patterns"""
    extracted = {}

    for field in fields:
        field_name = field["name"]
        field_type = field.get("field_type", "string")
        value = None

        # direct "FieldName: value" pattern
        field_pattern = re.compile(rf"{re.escape(field_name)}[:\s]*([^\n]+)", re.IGNORECASE)
        field_match = field_pattern.search(text)

        if field_match:
            potential_value = field_match.group(1).strip()

            if field_type == "currency":
                currency_match = re.search(r"[R$€£]?\s*[\d,]+\.?\d*", potential_value)
                value = currency_match.group().strip() if currency_match else potential_value

            elif field_type == "number":
                number_match = re.search(r"[\d,]+\.?\d*", potential_value)
                value = number_match.group().strip() if number_match else potential_value

            elif field_type == "email":
                email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", potential_value)
                value = email_match.group() if email_match else potential_value

            elif field_type == "date":
                date_match = re.search(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}", potential_value)
                value = date_match.group() if date_match else potential_value

            else:
                value = potential_value[:200]
        else:
            # try generic by type
            if field_type == "currency":
                matches = re.findall(r"[R$€£]\s*[\d,]+\.?\d{2}", text)
                value = matches[0] if matches else None

            elif field_type == "email":
                matches = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
                value = matches[0] if matches else None

            elif field_type == "date":
                matches = re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", text)
                value = matches[0] if matches else None

        extracted[field_name] = value

    return extracted

def extract_with_groq(document_text, fields):
    """Use Groq API to extract structured data"""
    field_descriptions = [f"  - {f['name']}: {f.get('field_type', 'text')}" for f in fields]
    field_list = "\n".join(field_descriptions)
    expected_json = "{\n" + ",\n".join([f'  "{f["name"]}": "value"' for f in fields]) + "\n}"
    
    max_text_length = 4000
    truncated_text = document_text[:max_text_length]
    if len(document_text) > max_text_length:
        truncated_text += "\n... (document truncated)"
    
    headers = {
        "Authorization": f"Bearer {current_app.config['GROQ_API_KEY']}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": current_app.config['GROQ_MODEL'],
        "messages": [
            {
                "role": "system",
                "content": "You are a data extraction assistant. Extract information from documents and return ONLY valid JSON. No explanations, no markdown."
            },
            {
                "role": "user",
                "content": f"Extract the following fields from this document:\n\n{field_list}\n\nDocument text:\n{truncated_text}\n\nReturn ONLY this JSON format (use null for missing values):\n{expected_json}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
        "top_p": 1,
        "stream": False
    }
    
    try:
        print("Calling Groq API…")
        resp = requests.post(current_app.config['GROQ_API_URL'], headers=headers, json=payload, timeout=30)
        
        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()
            content = content.replace("```json", "").replace("```", "").strip()
            
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
                normalized = {f["name"]: extracted_data.get(f["name"], None) for f in fields}
                print(f"Extracted via Groq: {normalized}")
                return normalized
            
            print("Groq JSON parse failed; falling back to regex.")
            return extract_with_regex(document_text, fields)
        
        elif resp.status_code == 401:
            print("Groq API auth failed – check GROQ_API_KEY. Falling back to regex.")
            return extract_with_regex(document_text, fields)
        
        else:
            print(f"Groq error {resp.status_code}: {resp.text}. Falling back to regex.")
            return extract_with_regex(document_text, fields)
    
    except requests.exceptions.Timeout:
        print("Groq API timeout. Falling back to regex.")
        return extract_with_regex(document_text, fields)
    except Exception as e:
        print(f"Groq error: {e}. Falling back to regex.")
        return extract_with_regex(document_text, fields)

def map_extracted_to_field_ids(extracted_data, fields):
    """Map extracted data to field IDs"""
    mapped = {}
    for f in fields:
        mapped[f["field_id"]] = extracted_data.get(f["name"], None)
    return mapped


# Table Management Routes
@document_extraction_bp.route('/tables', methods=['GET'])
def list_tables():
    """List all document tables"""
    try:
        tables = DocumentTable.query.filter_by(is_active=True).all()
        return jsonify([t.to_dict() for t in tables]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/tables/<string:table_id>', methods=['GET'])
def get_table(table_id):
    """Get specific table configuration"""
    try:
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        
        if not table:
            return jsonify({'error': 'Table not found'}), 404
        
        return jsonify(table.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/tables', methods=['POST'])
def create_or_update_table():
    """Create or update document table configuration"""
    try:
        data = request.get_json()
        
        table_id = data.get('table_id')
        name = data.get('name')
        fields = data.get('fields', [])
        
        if not table_id or not name:
            return jsonify({'error': 'table_id and name are required'}), 400
        
        # Check if table exists
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        
        if table:
            # Update existing table
            table.name = name
            table.description = data.get('description')
            table.is_configured = len(fields) > 0
            table.updated_at = datetime.utcnow()
            
            # Delete old fields
            DocumentField.query.filter_by(document_table_id=table.id).delete()
        else:
            # Create new table
            table = DocumentTable(
                table_id=table_id,
                name=name,
                description=data.get('description'),
                is_configured=len(fields) > 0,
                owner_id=1
            )
            db.session.add(table)
            db.session.flush()
        
        # Add fields
        for idx, field_data in enumerate(fields):
            field = DocumentField(
                field_id=field_data.get('field_id'),
                document_table_id=table.id,
                name=field_data.get('name'),
                field_type=field_data.get('field_type', 'text'),
                is_required=field_data.get('is_required', False),
                display_order=idx
            )
            db.session.add(field)
        
        db.session.commit()
        
        return jsonify(table.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating/updating table: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/tables/<string:table_id>', methods=['DELETE'])
def delete_table(table_id):
    """Delete a document table (soft delete)"""
    try:
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        
        if not table:
            return jsonify({'error': 'Table not found'}), 404
        
        table.is_active = False
        table.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Table deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Extraction Routes
@document_extraction_bp.route('/extract', methods=['POST'])
def extract_document():
    """Extract data from uploaded document"""
    start_time = datetime.now()
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'Empty filename'}), 400
        
        table_config_str = request.form.get('table')
        if not table_config_str:
            return jsonify({'error': 'No table configuration provided'}), 400
        
        try:
            table_config = json.loads(table_config_str)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid table configuration JSON'}), 400
        
        if 'fields' not in table_config or not table_config['fields']:
            return jsonify({'error': 'No fields configured in table'}), 400
        
        fields = table_config['fields']
        table_id = table_config.get('id', 'unknown')
        table_name = table_config.get('name', 'Unknown Table')
        model_id = request.form.get('model', current_app.config['GROQ_MODEL'])
        
        print("\n" + "=" * 60)
        print(f"Processing extraction for table: {table_name} (id={table_id})")
        print(f"Fields: {[f['name'] for f in fields]}")
        print("=" * 60 + "\n")
        
        # Get document_table_id
        doc_table = DocumentTable.query.filter_by(table_id=table_id).first()
        document_table_id = doc_table.id if doc_table else None
        
        # Save file
        field_names = [f['name'] for f in fields]
        fields_hash = hash_fields(field_names)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{fields_hash}_{file.filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)
        print(f"File saved → {file_path}")
        
        file_size = os.path.getsize(file_path)
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # Extract text
        ext = Path(file.filename).suffix.lower()
        if ext == '.pdf':
            document_text = extract_text_from_pdf(file_path)
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
            document_text = extract_text_from_image(file_path)
        else:
            return jsonify({'error': f'Unsupported file type: {ext}'}), 400
        
        if not document_text:
            return jsonify({'error': 'Failed to extract text from document'}), 500
        
        # Extract structured fields
        extracted_by_name = extract_with_groq(document_text, fields)
        mapped_fields = map_extracted_to_field_ids(extracted_by_name, fields)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Save to database
        result = DocumentResult(
            filename=file.filename,
            stored_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            document_table_id=document_table_id,
            table_id=table_id,
            table_name=table_name,
            fields_mapped=mapped_fields,
            fields_by_name=extracted_by_name,
            extracted_text=document_text[:1000],
            model_id=model_id,
            extraction_method='groq',
            processing_time_ms=int(processing_time),
            status='completed',
            owner_id=1
        )
        
        db.session.add(result)
        db.session.commit()
        
        print(f"✓ Saved result to DB (id={result.id})")
        
        return jsonify({
            'id': result.id,
            'fields': mapped_fields,
            'source': {'path': file_path, 'filename': file.filename},
            'model_id': model_id,
            'table_id': table_id,
            'table_name': table_name,
            'processing_time_ms': int(processing_time),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"✗ Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/results', methods=['GET'])
def list_results():
    """List extraction results"""
    try:
        limit = int(request.args.get('limit', '50'))
        table_id = request.args.get('table_id')
        
        query = DocumentResult.query
        
        if table_id:
            query = query.filter_by(table_id=table_id)
        
        results = query.order_by(DocumentResult.created_at.desc()).limit(limit).all()
        return jsonify([r.to_dict() for r in results]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/results/<int:result_id>', methods=['GET'])
def get_result(result_id):
    """Get specific extraction result"""
    try:
        result = DocumentResult.query.get(result_id)
        
        if not result:
            return jsonify({'error': 'Result not found'}), 404
        
        return jsonify(result.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/results/<int:result_id>', methods=['DELETE'])
def delete_result(result_id):
    """Delete extraction result"""
    try:
        result = DocumentResult.query.get(result_id)
        
        if not result:
            return jsonify({'error': 'Result not found'}), 404
        
        if result.stored_path and os.path.exists(result.stored_path):
            os.remove(result.stored_path)
        
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({'message': 'Result deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/results/<int:result_id>/re-extract', methods=['POST'])
def re_extract_result(result_id):
    """Re-extract data from existing document with updated field configuration"""
    start_time = datetime.now()
    
    try:
        result = DocumentResult.query.get(result_id)
        
        if not result:
            return jsonify({'error': 'Result not found'}), 404
        
        if not result.stored_path or not os.path.exists(result.stored_path):
            return jsonify({'error': 'Original file not found'}), 404
        
        data = request.get_json()
        fields = data.get('fields', [])
        
        if not fields:
            return jsonify({'error': 'No fields provided'}), 400
        
        print("\n" + "=" * 60)
        print(f"Re-extracting document: {result.filename}")
        print(f"New fields: {[f['name'] for f in fields]}")
        print("=" * 60 + "\n")
        
        # Extract text
        ext = Path(result.filename).suffix.lower()
        if ext == '.pdf':
            document_text = extract_text_from_pdf(result.stored_path)
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
            document_text = extract_text_from_image(result.stored_path)
        else:
            document_text = result.extracted_text or ""
        
        if not document_text:
            return jsonify({'error': 'Failed to extract text from document'}), 500
        
        # Extract with new fields
        extracted_by_name = extract_with_groq(document_text, fields)
        mapped_fields = map_extracted_to_field_ids(extracted_by_name, fields)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update result
        result.fields_mapped = mapped_fields
        result.fields_by_name = extracted_by_name
        result.processing_time_ms = int(processing_time)
        result.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        print(f"✓ Re-extracted result {result_id} (processing_time={int(processing_time)}ms)")
        
        return jsonify({
            'id': result.id,
            'fields': mapped_fields,
            'processing_time_ms': int(processing_time),
            'message': 'Re-extraction completed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Re-extraction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@document_extraction_bp.route('/tables/<string:table_id>/re-extract-all', methods=['POST'])
def re_extract_all_for_table(table_id):
    """Re-extract all documents for a table with updated field configuration"""
    try:
        # Get table configuration
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        if not table:
            return jsonify({'error': 'Table not found'}), 404
        
        # Get all results for this table
        results = DocumentResult.query.filter_by(table_id=table_id).all()
        
        if not results:
            return jsonify({'message': 'No documents to re-extract', 'processed': 0}), 200
        
        # Prepare fields configuration
        fields = [
            {
                "field_id": f.field_id,
                "name": f.name,
                "field_type": f.field_type
            }
            for f in table.fields
        ]
        
        print("\n" + "=" * 60)
        print(f"Batch re-extraction for table: {table.name}")
        print(f"Documents to process: {len(results)}")
        print(f"Fields: {[f['name'] for f in fields]}")
        print("=" * 60 + "\n")
        
        processed = 0
        failed = 0
        
        for result in results:
            try:
                # Skip if file doesn't exist
                if not result.stored_path or not os.path.exists(result.stored_path):
                    print(f"⚠ Skipping {result.filename} - file not found")
                    failed += 1
                    continue
                
                # Extract text
                ext = Path(result.filename).suffix.lower()
                if ext == '.pdf':
                    document_text = extract_text_from_pdf(result.stored_path)
                elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
                    document_text = extract_text_from_image(result.stored_path)
                else:
                    document_text = result.extracted_text or ""
                
                if not document_text:
                    print(f"⚠ Skipping {result.filename} - no text available")
                    failed += 1
                    continue
                
                # Extract with new fields
                extracted_by_name = extract_with_groq(document_text, fields)
                mapped_fields = map_extracted_to_field_ids(extracted_by_name, fields)
                
                # Update result
                result.fields_mapped = mapped_fields
                result.fields_by_name = extracted_by_name
                result.updated_at = datetime.utcnow()
                
                processed += 1
                print(f"✓ Re-extracted: {result.filename}")
                
            except Exception as e:
                print(f"✗ Failed to re-extract {result.filename}: {e}")
                failed += 1
                continue
        
        db.session.commit()
        
        print(f"\n✓ Batch re-extraction complete: {processed} processed, {failed} failed\n")
        
        return jsonify({
            'message': 'Batch re-extraction completed',
            'processed': processed,
            'failed': failed,
            'total': len(results)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Batch re-extraction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500