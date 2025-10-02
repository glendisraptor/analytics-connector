# Analytics Connector - Flask Application

A comprehensive Flask application for managing database connections, document extraction, and Apache Superset integration.

## Features

- **User Authentication**: Registration, login, JWT-based authentication
- **Database Connections**: Connect to PostgreSQL, MySQL databases
- **Document Extraction**: Extract structured data from PDFs and images using Groq AI
- **Apache Superset Integration**: Sync databases and create datasets in Superset
- **ETL Scheduling**: Schedule automated data extraction jobs
- **Audit Logging**: Track all user actions and system events

## Project Structure

```
analytics-connector/
├── app.py                          # Main application entry point
├── models.py                       # Database models
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── .env                           # Your environment variables (create this)
├── models/
│   ├── __init__.py
│   └── models.py
├── routes/
│   ├── __init__.py
│   ├── auth.py                    # Authentication routes
│   ├── database_connections.py    # Database connection management
│   ├── document_extraction.py     # Document extraction routes
│   ├── superset.py                # Superset integration
│   └── etl.py                     # ETL job management
├── uploads/                        # Uploaded documents storage
└── results/                        # Extraction results storage
```

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Tesseract OCR (for image extraction)
- Apache Superset (optional, for analytics)

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd analytics-connector
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install Tesseract OCR**
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

5. **Setup PostgreSQL Database**
```bash
# Connect to PostgreSQL
psql -U postgres

# Run the SQL setup script
\i analytics_connector_setup.sql
```

6. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

7. **Generate encryption key**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Add the generated key to your `.env` file as `ENCRYPTION_KEY`

8. **Initialize the database**
```bash
python app.py
# This will create all necessary tables
```

## Configuration

### Environment Variables

Edit `.env` file with your configuration:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/analytics_connector

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
ENCRYPTION_KEY=your-fernet-encryption-key-here

# Groq API (for document extraction)
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.1-8b-instant

# Superset (optional)
SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin
```

### Get Groq API Key

1. Visit https://console.groq.com
2. Sign up or log in
3. Create an API key
4. Add it to your `.env` file

## Usage

### Start the Application

```bash
python app.py
```

The API will be available at `http://localhost:8000`

### API Endpoints:

## Authentication Routes (`/api/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login and get JWT tokens | No |
| POST | `/api/auth/refresh` | Refresh access token | Yes (refresh token) |
| POST | `/api/auth/logout` | Logout and blacklist token | Yes |
| GET | `/api/auth/me` | Get current user profile | Yes |
| PUT | `/api/auth/me` | Update current user profile | Yes |
| POST | `/api/auth/change-password` | Change user password | Yes |
| GET | `/api/auth/settings` | Get user settings | Yes |
| PUT | `/api/auth/settings` | Update user settings | Yes |

## Database Connections Routes (`/api/connections`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/connections/` | List all connections | Yes |
| GET | `/api/connections/<id>` | Get specific connection | Yes |
| POST | `/api/connections/` | Create new connection | Yes |
| PUT | `/api/connections/<id>` | Update connection | Yes |
| DELETE | `/api/connections/<id>` | Delete connection (soft) | Yes |
| POST | `/api/connections/<id>/test` | Test connection | Yes |
| GET | `/api/connections/<id>/schema` | Get database schema | Yes |

## Document Extraction Routes (`/api/documents`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/documents/tables` | List document tables | Yes |
| GET | `/api/documents/tables/<table_id>` | Get table configuration | Yes |
| POST | `/api/documents/tables` | Create/update table | Yes |
| DELETE | `/api/documents/tables/<table_id>` | Delete table | Yes |
| POST | `/api/documents/extract` | Extract data from document | Yes |
| GET | `/api/documents/results` | List extraction results | Yes |
| GET | `/api/documents/results/<id>` | Get specific result | Yes |
| DELETE | `/api/documents/results/<id>` | Delete result | Yes |
| POST | `/api/documents/results/<id>/re-extract` | Re-extract document | Yes |

## ETL Jobs Routes (`/api/etl`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/etl/jobs` | List ETL jobs | Yes |
| GET | `/api/etl/jobs/<id>` | Get job details | Yes |
| POST | `/api/etl/jobs/run/<connection_id>` | Run ETL job manually | Yes |
| GET | `/api/etl/schedules` | List ETL schedules | Yes |
| POST | `/api/etl/schedules` | Create schedule | Yes |
| PUT | `/api/etl/schedules/<id>` | Update schedule | Yes |
| DELETE | `/api/etl/schedules/<id>` | Delete schedule | Yes |

## Superset Integration Routes (`/api/superset`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/superset/status` | Check Superset connection | Yes |
| POST | `/api/superset/sync/<connection_id>` | Sync connection to Superset | Yes |
| GET | `/api/superset/databases` | List Superset databases | Yes |
| GET | `/api/superset/datasets` | List Superset datasets | Yes |
| POST | `/api/superset/datasets/create` | Create dataset in Superset | Yes |

## Health Check Route

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health` | Application health check | No |

## Total: 36 API Endpoints

**Breakdown by category:**
- Authentication: 9 endpoints
- Database Connections: 7 endpoints
- Document Extraction: 9 endpoints
- ETL Jobs: 7 endpoints
- Superset Integration: 5 endpoints
- Health Check: 1 endpoint

**Authentication methods:**
- JWT Bearer token for all protected routes
- Token blacklist for logout
- Refresh token support

All endpoints return JSON responses and include proper error handling with appropriate HTTP status codes (200, 201, 400, 401, 403, 404, 500).

### Example API Calls

#### Register User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

#### Create Database Connection
```bash
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Production Database",
    "database_type": "postgresql",
    "credentials": {
      "host": "localhost",
      "port": 5432,
      "database": "company_finance",
      "username": "postgres",
      "password": "password"
    },
    "sync_frequency": "daily"
  }'
```

#### Extract Document
```bash
curl -X POST http://localhost:8000/api/documents/extract \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@invoice.pdf" \
  -F 'table={
    "id": "financial",
    "name": "Financial Documents",
    "fields": [
      {"field_id": "amount", "name": "Amount", "field_type": "currency"},
      {"field_id": "date", "name": "Date", "field_type": "date"}
    ]
  }'
```

## Database Schema

The application uses the following main tables:

- **users**: User accounts and authentication
- **user_settings**: User preferences and configuration
- **database_connections**: Customer database connections
- **document_tables**: Document table configurations
- **document_fields**: Field definitions for document tables
- **document_results**: Extracted document data
- **etl_jobs**: ETL job execution history
- **etl_schedules**: Scheduled ETL jobs
- **audit_logs**: System activity logs

## Security Features

- Password hashing with bcrypt
- JWT-based authentication
- Encrypted database credentials (Fernet)
- Token blacklisting for logout
- Audit logging for all actions
- IP address and user agent tracking

## Development

### Run in Development Mode

```bash
export FLASK_ENV=development
python app.py
```

### Database Migrations

When you modify models, you'll need to update the database schema manually or use a migration tool like Alembic.

## Testing

Create test database connection using the sample `company_finance` database:

```bash
psql -U postgres
\c company_finance
# Tables with sample data are already created by the SQL script
```

## Troubleshooting

### Common Issues

1. **Database connection error**
   - Check `DATABASE_URL` in `.env`
   - Ensure PostgreSQL is running
   - Verify credentials

2. **Groq API errors**
   - Check `GROQ_API_KEY` is valid
   - Verify API quota/limits
   - Check network connectivity

3. **Tesseract not found**
   - Install Tesseract OCR
   - Add to PATH if on Windows

4. **Port already in use**
   - Change port in `app.py`: `app.run(port=5001)`

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y tesseract-ocr

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

### Environment Variables for Production

- Use strong SECRET_KEY and JWT_SECRET_KEY
- Use production database credentials
- Enable HTTPS
- Set up proper logging
- Configure CORS appropriately

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub or contact support.