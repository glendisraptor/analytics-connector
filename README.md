# Analytics Connector

A comprehensive application that allows customers to connect their databases and transform data for analytics using Apache Superset and other open-source tools.

## Features

- **Multi-Database Support**: Connect to PostgreSQL, MySQL, MongoDB, SQLite, Oracle, and SQL Server
- **Secure Credential Management**: Encrypted storage of database credentials
- **Automated ETL Pipelines**: Background data extraction and transformation
- **Analytics Integration**: Seamless integration with Apache Superset
- **Real-time Monitoring**: Track connection status and job progress
- **Web-based Dashboard**: Modern React interface for managing connections

## Architecture

### Backend (FastAPI)
- RESTful API with automatic documentation
- JWT authentication and authorization
- Background job processing with Celery
- Encrypted credential storage
- Database connection pooling

### Frontend (React + TypeScript)
- Modern, responsive UI with Tailwind CSS
- Real-time updates and notifications
- Secure authentication flow
- Connection management interface

### Analytics (Apache Superset)
- Pre-configured analytics platform
- Automated dataset creation
- Dashboard and visualization tools
- SQL Lab for custom queries

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd analytics-connector
```

### 2. Environment Setup
```bash
# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Generate encryption key (32 characters)
python -c "import secrets; print(secrets.token_urlsafe(32)[:32])" > backend/.env
```

### 3. Start with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Superset**: http://localhost:8088 (admin/admin)

### 5. Create Your First Connection
1. Register a new account at http://localhost:3000/register
2. Login and navigate to "Connections"
3. Click "Add Connection" and fill in your database details
4. Test the connection and start syncing data
5. View your analytics in Superset

## Database Support

| Database | Status | Notes |
|----------|--------|-------|
| PostgreSQL | ✅ | Full support |
| MySQL | ✅ | Full support |
| MongoDB | ✅ | Document collections supported |
| SQLite | ✅ | Local files |
| Oracle | ⚠️ | Basic support |
| SQL Server | ⚠️ | Basic support |

## Configuration

### Backend Configuration
Key environment variables in `backend/.env`:

```env
# Security
SECRET_KEY=your-super-secret-key
ENCRYPTION_KEY=your-32-character-encryption-key

# Databases
DATABASE_URL=postgresql://user:pass@host:port/db
ANALYTICS_DATABASE_URL=postgresql://user:pass@host:port/analytics

# Redis
REDIS_URL=redis://localhost:6379

# Superset
SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin
```

### Frontend Configuration
Key environment variables in `frontend/.env`:

```env
VITE_APP_API_URL=http://localhost:8000
VITE_APP_APP_NAME=Analytics Connector
```

## Development

### Backend Development
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker
celery -A app.celery_app worker --loglevel=info
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

## API Documentation

The API documentation is automatically generated and available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user

#### Connections
- `GET /api/v1/connections/` - List connections
- `POST /api/v1/connections/` - Create connection
- `PUT /api/v1/connections/{id}` - Update connection
- `DELETE /api/v1/connections/{id}` - Delete connection
- `POST /api/v1/connections/{id}/test` - Test connection

#### Jobs
- `GET /api/v1/jobs/` - List ETL jobs
- `POST /api/v1/jobs/` - Create ETL job
- `GET /api/v1/jobs/{id}` - Get job status

## Security

### Data Protection
- All database credentials are encrypted using AES-256
- Passwords are hashed using bcrypt
- JWT tokens for API authentication
- CORS protection for cross-origin requests

### Best Practices
- Use strong, unique encryption keys
- Regularly rotate credentials
- Enable HTTPS in production
- Implement proper firewall rules
- Regular security audits

## Deployment

### Production Deployment
1. Use the production Docker Compose file:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. Configure environment variables for production
3. Set up reverse proxy (Nginx)
4. Enable SSL/TLS certificates
5. Configure monitoring and logging

### Environment-Specific Configurations
- **Development**: Local Docker setup with hot reloading
- **Staging**: Similar to production but with debug enabled
- **Production**: Optimized builds, SSL, monitoring, and backups

## Monitoring and Troubleshooting

### Health Checks
- Backend: `GET /health`
- Database connections: Automatic testing
- Celery workers: Built-in monitoring

### Logging
- Application logs: Structured JSON logging
- Database queries: Optional query logging
- Access logs: Nginx/reverse proxy logs

### Common Issues
1. **Connection failures**: Check credentials and network connectivity
2. **ETL job failures**: Review job logs and data quality
3. **Performance issues**: Monitor database connection pools
4. **Authentication errors**: Verify JWT token configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For support, please:
1. Check the documentation
2. Review common issues
3. Create an issue on GitHub
4. Contact the development team

---

Built with ❤️ using FastAPI, React, and Apache Superset