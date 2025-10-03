# RAG Admin Dashboard - Setup Guide

A comprehensive admin dashboard for monitoring and analyzing your RAG (Retrieval-Augmented Generation) portfolio chatbot system.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### 1. Backend Setup

```bash
# Install Python dependencies
cd admin/backend
pip install -r requirements.txt

# Or install individually:
pip install fastapi uvicorn python-multipart pydantic python-dateutil
```

### 2. Set Environment Variables

```bash
# Optional: Set custom port (default is 8001)
export ADMIN_PORT="8001"
```

Or create a `.env` file in the admin directory:
```bash
ADMIN_PORT=8001
```

### 3. Start Backend Server

```bash
# From project root
python3 admin/start-admin.py

# Or run directly
cd admin/backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Frontend Setup

```bash
# Install dependencies
cd admin/frontend
npm install

# Build for production
npm run build

# Or run in development mode
npm run dev
```

### 5. Access Dashboard

- **Production**: http://localhost:8001/admin (after building frontend)
- **Development**: http://localhost:3000 (if running `npm run dev`)
- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/admin/api/health

## 🔐 Authentication

The dashboard uses session-based authentication with secure login credentials.

## 📊 Features

### Dashboard Overview
- Real-time system metrics
- Query statistics
- Performance indicators
- Recent activity feed
- System health status

### Query Explorer
- Searchable query history
- Advanced filtering (errors, date ranges)
- Detailed query analysis
- User feedback management
- Response time tracking

### Performance Analytics
- Response time trends
- Query volume analysis
- Error rate monitoring
- Cache performance
- Model comparison metrics

### Content Insights
- Popular topics analysis
- Content gap identification
- Query effectiveness scoring
- Improvement suggestions
- Search relevance metrics

### User Sessions
- Active session monitoring
- User behavior analysis
- Session duration tracking
- Platform usage statistics

## 🔧 Integration with Existing RAG System

The admin dashboard automatically integrates with your existing RAG system by:

1. **Automatic Query Logging**: Patches existing query loggers
2. **Database Integration**: Uses SQLite for performance and simplicity
3. **No Code Changes Required**: Works with your existing endpoints

To enable logging in your existing RAG system, add this to your application startup:

```python
# In your main application startup
from admin.backend.integration import patch_existing_query_logger

# Enable admin dashboard logging
patch_existing_query_logger()
```

## 📁 Project Structure

```
admin/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main application
│   ├── routes.py           # API endpoints
│   ├── database.py         # Database operations
│   ├── models.py           # Data models
│   ├── integration.py      # RAG system integration
│   └── requirements.txt    # Python dependencies
├── frontend/               # Vue.js frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── views/          # Page views
│   │   ├── stores/         # Pinia state management
│   │   ├── services/       # API services
│   │   └── router/         # Vue Router config
│   ├── package.json        # Frontend dependencies
│   └── vite.config.js      # Build configuration
├── rag_monitoring.db       # SQLite database (auto-created)
├── start-admin.py          # Backend startup script
├── test-setup.py           # Setup validation script
└── README.md               # Documentation
```

## 🗃️ Database Schema

The system uses SQLite with these main tables:

- **query_logs**: All query records with performance metrics
- **user_sessions**: User session tracking
- **hourly_metrics**: Aggregated performance data
- **content_gaps**: Content improvement opportunities

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PORT` | `8001` | Port for the admin backend server |
| `ADMIN_DB_PATH` | `admin/rag_monitoring.db` | Path to SQLite database |

### Frontend Configuration

The frontend automatically proxies API requests to the backend. For production deployment, configure your web server to route `/admin/api/*` requests to the admin backend.

## 🚀 Deployment

### Development
```bash
# Backend
python3 admin/start-admin.py

# Frontend (separate terminal)
cd admin/frontend && npm run dev
```

### Production
```bash
# Build frontend
cd admin/frontend && npm run build

# Start backend (serves both API and frontend)
python3 admin/start-admin.py
```

### Docker Deployment (Optional)
```dockerfile
# admin/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY admin/backend/requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8001

CMD ["python", "admin/start-admin.py"]
```

**Security Note**: Session-based authentication provides secure access without environment tokens.

## 🔍 Troubleshooting

### Common Issues

1. **"No module named 'fastapi'"**
   ```bash
   pip install fastapi uvicorn
   ```

2. **Authentication issues**
   - Ensure admin users are properly configured in the database
   - Check session management and cookie settings

3. **Frontend not loading**
   - Build the frontend: `cd admin/frontend && npm run build`
   - Check backend logs for errors

4. **Database issues**
   - Delete `admin/rag_monitoring.db` to reset
   - Check file permissions

### Testing Setup
```bash
# Run setup validation
python3 admin/test-setup.py

# Test API endpoints (requires valid session)
curl -c cookies.txt -b cookies.txt http://localhost:8001/admin/api/health
```

## 📈 Performance Considerations

- SQLite handles thousands of queries efficiently
- Frontend is optimized for large datasets with pagination
- Charts are rendered client-side for responsiveness
- API responses are cached where appropriate

## 🔒 Security

- Token-based authentication for all admin endpoints
- No sensitive data stored in frontend
- Configurable data retention policies
- Rate limiting on expensive operations

## 🤝 Contributing

The admin dashboard is designed to be extensible:

1. Add new API endpoints in `admin/backend/routes.py`
2. Create new Vue components in `admin/frontend/src/components/`
3. Add new views in `admin/frontend/src/views/`
4. Update the database schema in `admin/backend/database.py`

## 📚 API Documentation

Once the backend is running, full API documentation is available at:
- http://localhost:8001/docs (Swagger UI)
- http://localhost:8001/redoc (ReDoc)

## ⚠️ Important Notes

- Always set a strong admin token in production
- The database file contains query logs - secure it appropriately
- Consider log rotation for long-running deployments
- Monitor disk space usage as query logs accumulate

## 🎯 Next Steps

After setup:
1. Configure your RAG system integration
2. Set up automated backups for the database
3. Configure monitoring alerts
4. Customize the dashboard for your specific needs
