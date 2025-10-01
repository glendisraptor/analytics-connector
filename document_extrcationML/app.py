import os
import json
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

# Env & DB
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB

# Files/OCR/HTTP
import PyPDF2
from PIL import Image
import pytesseract
import requests

# -----------------------------
# Env & App setup
# -----------------------------
load_dotenv()  # loads .env into environment

app = Flask(__name__)
CORS(app)

# Folders
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
RESULTS_FOLDER = os.getenv("RESULTS_FOLDER", "results")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# External APIs
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment.")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -----------------------------
# Models
# -----------------------------
# Continue from previous response - Add these to your Flask app

# Add new models (continue)
class DocumentTable(db.Model):
    __tablename__ = "document_tables"
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_configured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    fields = db.relationship('DocumentField', backref='document_table', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            "id": self.id,
            "table_id": self.table_id,
            "name": self.name,
            "description": self.description,
            "is_configured": self.is_configured,
            "is_active": self.is_active,
            "fields": [f.to_dict() for f in self.fields],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentField(db.Model):
    __tablename__ = "document_fields"
    
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.String(100), nullable=False)
    document_table_id = db.Column(db.Integer, db.ForeignKey('document_tables.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    validation_rules = db.Column(JSONB)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "field_id": self.field_id,
            "name": self.name,
            "field_type": self.field_type,
            "is_required": self.is_required,
            "display_order": self.display_order,
        }


# Update DocumentResult model to include new fields
class DocumentResult(db.Model):
    __tablename__ = "document_results"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(512), nullable=False)
    stored_path = db.Column(db.String(1024), nullable=True)
    file_hash = db.Column(db.String(64))
    file_size = db.Column(db.Integer)
    
    # Link to document table
    document_table_id = db.Column(db.Integer, db.ForeignKey('document_tables.id', ondelete='SET NULL'))
    table_id = db.Column(db.String(255), nullable=True)
    table_name = db.Column(db.String(255), nullable=True)
    
    # Extraction results
    fields_mapped = db.Column(JSONB, nullable=True)
    fields_by_name = db.Column(JSONB, nullable=True)
    extracted_text = db.Column(db.Text)
    
    # Processing metadata
    model_id = db.Column(db.String(255), nullable=True)
    extraction_method = db.Column(db.String(50), default='groq')
    processing_time_ms = db.Column(db.Integer)
    confidence_score = db.Column(db.Numeric(3, 2))
    
    # Status
    status = db.Column(db.String(50), default='completed')
    error_message = db.Column(db.Text)
    owner_id = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "stored_path": self.stored_path,
            "document_table_id": self.document_table_id,
            "table_id": self.table_id,
            "table_name": self.table_name,
            "fields_mapped": self.fields_mapped,
            "fields_by_name": self.fields_by_name,
            "extracted_text": self.extracted_text,
            "model_id": self.model_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# -----------------------------
# Helpers
# -----------------------------
def hash_fields(field_names):
    """Generate a stable-ish hash from field names list."""
    field_str = json.dumps(sorted(field_names))
    return str(abs(hash(field_str)) % (10 ** 10))


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                # Some PDFs return None for extract_text()
                text.append(page.extract_text() or "")
            return "\n".join(text).strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


def extract_text_from_image(file_path: str) -> str:
    """Extract text from image using OCR"""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Image extraction error: {e}")
        return ""


def extract_with_regex(text, fields):
    """Fallback extraction using simple regex patterns."""
    extracted = {}

    for field in fields:
        field_name = field["name"]
        field_type = field.get("type", "string")
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
    """Use Groq API to extract structured data based on field configuration."""

    # Build field descriptions for the prompt
    field_descriptions = [f"  - {f['name']}: {f.get('type', 'string')}" for f in fields]
    field_list = "\n".join(field_descriptions)

    # Expected JSON skeleton
    expected_json = "{\n" + ",\n".join([f'  "{f["name"]}": "value"' for f in fields]) + "\n}"

    # Truncate large docs for token safety
    max_text_length = 4000
    truncated_text = document_text[:max_text_length]
    if len(document_text) > max_text_length:
        truncated_text += "\n... (document truncated)"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a data extraction assistant. Extract information from documents and "
                    "return ONLY valid JSON. No explanations, no markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Extract the following fields from this document:\n\n{field_list}\n\n"
                    f"Document text:\n{truncated_text}\n\n"
                    f"Return ONLY this JSON format (use null for missing values):\n{expected_json}"
                ),
            },
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
        "top_p": 1,
        "stream": False,
    }

    try:
        print("Calling Groq API…")
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()
            content = content.replace("```json", "").replace("```", "").strip()

            # Try extracting top-level JSON object
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())

                # normalize: ensure all fields exist
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
    """Map extracted data to field IDs for the frontend"""
    mapped = {}
    for f in fields:
        mapped[f["id"]] = extracted_data.get(f["name"], None)
    return mapped

# Add new API endpoints

@app.route("/api/tables", methods=["GET"])
def list_tables():
    """List all document tables with their field configurations"""
    try:
        tables = DocumentTable.query.filter_by(is_active=True).all()
        return jsonify([t.to_dict() for t in tables]), 200
    except Exception as e:
        print(f"Error listing tables: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tables", methods=["POST"])
def create_or_update_table():
    """Create a new table or update existing table configuration"""
    try:
        data = request.json
        table_id = data.get("table_id")
        name = data.get("name")
        fields = data.get("fields", [])
        
        if not table_id or not name:
            return jsonify({"error": "table_id and name are required"}), 400
        
        # Check if table exists
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        
        if table:
            # Update existing table
            table.name = name
            table.description = data.get("description")
            table.is_configured = len(fields) > 0
            table.updated_at = datetime.utcnow()
            
            # Delete old fields
            DocumentField.query.filter_by(document_table_id=table.id).delete()
        else:
            # Create new table
            table = DocumentTable(
                table_id=table_id,
                name=name,
                description=data.get("description"),
                is_configured=len(fields) > 0,
                owner_id=1  # Default to admin
            )
            db.session.add(table)
            db.session.flush()  # Get the ID
        
        # Add fields
        for idx, field_data in enumerate(fields):
            field = DocumentField(
                field_id=field_data.get("field_id"),
                document_table_id=table.id,
                name=field_data.get("name"),
                field_type=field_data.get("field_type", "text"),
                is_required=field_data.get("is_required", False),
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
        return jsonify({"error": str(e)}), 500


@app.route("/api/tables/<string:table_id>", methods=["GET"])
def get_table(table_id: str):
    """Get a specific table configuration"""
    try:
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        if not table:
            return jsonify({"error": "Table not found"}), 404
        return jsonify(table.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tables/<string:table_id>", methods=["DELETE"])
def delete_table(table_id: str):
    """Delete a table (soft delete by setting is_active=False)"""
    try:
        table = DocumentTable.query.filter_by(table_id=table_id).first()
        if not table:
            return jsonify({"error": "Table not found"}), 404
        
        table.is_active = False
        db.session.commit()
        
        return jsonify({"message": "Table deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/results", methods=["GET"])
def list_results():
    """List latest results, with optional filters"""
    try:
        limit = int(request.args.get("limit", "50"))
        table_id = request.args.get("table_id")
        
        query = DocumentResult.query
        
        if table_id:
            query = query.filter_by(table_id=table_id)
        
        rows = query.order_by(DocumentResult.created_at.desc()).limit(limit).all()
        return jsonify([r.to_dict() for r in rows]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update the extract endpoint to link with document_table_id
@app.route("/api/extract", methods=["POST"])
def extract_document():
    """Extract data from document based on table configuration."""
    start_time = datetime.now()
    
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        table_config_str = request.form.get("table")
        if not table_config_str:
            return jsonify({"error": "No table configuration provided"}), 400

        try:
            table_config = json.loads(table_config_str)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid table configuration JSON"}), 400

        if "fields" not in table_config or not table_config["fields"]:
            return jsonify({"error": "No fields configured in table"}), 400

        fields = table_config["fields"]
        table_id = table_config.get("id", "unknown")
        table_name = table_config.get("name", "Unknown Table")
        model_id = request.form.get("model", os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))

        print("\n" + "=" * 60)
        print(f"Processing extraction for table: {table_name} (id={table_id})")
        print(f"Fields: {[f['name'] for f in fields]}")
        print("=" * 60 + "\n")

        # Get document_table_id from database
        doc_table = DocumentTable.query.filter_by(table_id=table_id).first()
        document_table_id = doc_table.id if doc_table else None

        # Save file
        field_names = [f["name"] for f in fields]
        fields_hash = hash_fields(field_names)

        filename = file.filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{fields_hash}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        file.save(file_path)
        print(f"File saved → {file_path}")

        # Get file size
        file_size = os.path.getsize(file_path)

        # Extract text
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            document_text = extract_text_from_pdf(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
            document_text = extract_text_from_image(file_path)
        else:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        if not document_text:
            return jsonify({"error": "Failed to extract text from document"}), 500

        # Extract structured fields
        extracted_by_name = extract_with_groq(document_text, fields)
        mapped_fields = map_extracted_to_field_ids(extracted_by_name, fields)

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Persist to DB
        record = DocumentResult(
            filename=filename,
            stored_path=file_path,
            file_size=file_size,
            document_table_id=document_table_id,
            table_id=table_id,
            table_name=table_name,
            fields_mapped=mapped_fields,
            fields_by_name=extracted_by_name,
            extracted_text=document_text[:1000],  # Store first 1000 chars
            model_id=model_id,
            extraction_method='groq',
            processing_time_ms=int(processing_time),
            status='completed',
            owner_id=1  # Default to admin
        )
        db.session.add(record)
        db.session.commit()

        print(f"✓ Saved result to DB (id={record.id})")

        # Response payload
        result_payload = {
            "id": record.id,
            "fields": mapped_fields,
            "source": {"path": file_path, "filename": filename},
            "model_id": model_id,
            "table_id": table_id,
            "table_name": table_name,
            "processing_time_ms": int(processing_time),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return jsonify(result_payload), 200

    except Exception as e:
        print(f"✗ Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/results/<int:result_id>", methods=["DELETE"])
def delete_result(result_id: int):
    """Delete a specific extraction result"""
    try:
        result = DocumentResult.query.get(result_id)
        if not result:
            return jsonify({"error": "Result not found"}), 404
        
        # Optionally delete the file
        if result.stored_path and os.path.exists(result.stored_path):
            os.remove(result.stored_path)
        
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({"message": "Result deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Update the health check to include table count
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    api_key_configured = bool(GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here")
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
        table_count = DocumentTable.query.filter_by(is_active=True).count()
        result_count = DocumentResult.query.count()
    except Exception:
        db_ok = False
        table_count = 0
        result_count = 0

    return jsonify(
        {
            "status": "healthy" if api_key_configured and db_ok else "degraded",
            "extraction_method": "groq+ocr_fallback",
            "api_configured": api_key_configured,
            "db_connected": db_ok,
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "tables_configured": table_count,
            "total_results": result_count,
        }
    ), 200


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" Document Extraction API (Groq + OCR) ")
    print("=" * 60)

    if GROQ_API_KEY == "your_groq_api_key_here":
        print("\n⚠️  WARNING: Groq API key not configured!")
        print("Set GROQ_API_KEY environment variable.")
        print("Get your key at: https://console.groq.com\n")
    else:
        print("✓ Groq API key configured")

    print(f"✓ Upload folder:  {UPLOAD_FOLDER}")
    print(f"✓ Results folder: {RESULTS_FOLDER}")
    print(f"✓ DB URL:         {DATABASE_URL}")
    print("\nInitializing database…")
    with app.app_context():
        db.create_all()
    print("✓ DB ready")

    print("\nStarting server on http://0.0.0.0:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5000, host="0.0.0.0")