# RAG Admin Dashboard

A comprehensive admin dashboard for monitoring and analyzing the RAG (Retrieval-Augmented Generation) portfolio chatbot system.

## ✨ Features

- **📊 Real-time Query Monitoring**: Track all user queries, responses, and performance metrics
- **⚡ Performance Analytics**: Response times, cache hit rates, error tracking with interactive charts
- **🎯 Content Insights**: Popular topics, content gaps, search effectiveness analysis
- **👥 Session Management**: User session tracking and behavior analysis
- **📤 Data Export**: CSV export for further analysis and reporting
- **🔐 Security**: Token-based authentication with route protection
- **📱 Modern UI**: Vue 3 + Vuetify 3 responsive interface
- **🔄 Real-time Updates**: Live dashboard with auto-refresh capabilities

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Install dependencies
cd admin/backend
pip install -r requirements.txt

# Start backend server
python3 ../start-admin.py
```

### 2. Frontend Setup

```bash
# Install and build frontend
cd admin/frontend
npm install
npm run build

# Or run in development mode
npm run dev
```

### 3. Access Dashboard

- **Production**: http://localhost:8001/admin
- **Development**: http://localhost:3000
- **API Docs**: http://localhost:8001/docs

## 📖 Full Documentation

See **[SETUP.md](SETUP.md)** for complete installation, configuration, and deployment instructions.

## API Endpoints

Base URL: `http://localhost:8001/admin/api`

### Authentication
All endpoints require session-based authentication via secure cookies.

### Available Endpoints

- `GET /stats/overview?days=7` - Overall statistics
- `GET /queries?limit=50&offset=0&search=&errors_only=false` - Query logs with pagination
- `GET /queries/{id}` - Specific query details
- `POST /queries/{id}/feedback` - Update query feedback
- `GET /performance/metrics?time_range=24h` - Performance metrics
- `GET /performance/timeline?days=7&interval=hour` - Time series data
- `GET /content/gaps` - Queries with low relevance scores
- `GET /content/popular-topics` - Most queried topics
- `GET /sessions?active_only=false&limit=50` - User sessions
- `GET /export/csv?type=queries&start_date=&end_date=` - CSV export
- `GET /health` - Health check (no auth required)

### Example Usage

```bash
# Get overview stats
curl "http://localhost:8001/admin/api/stats/overview?days=7&token=your-admin-token"

# Get recent queries
curl "http://localhost:8001/admin/api/queries?limit=10&token=your-admin-token"

# Get performance metrics
curl "http://localhost:8001/admin/api/performance/metrics?time_range=24h&token=your-admin-token"
```

## Database Schema

The system uses SQLite with the following tables:
- `query_logs` - All query logs with performance metrics
- `user_sessions` - User session tracking
- `hourly_metrics` - Aggregated hourly statistics
- `content_gaps` - Tracking of poorly answered queries

## Integration with Existing RAG System

The admin system integrates with your existing RAG system by:

1. **Automatic Query Logging**: Patches the existing query logger to also log to the admin database
2. **Session Tracking**: Tracks user sessions across queries
3. **Performance Monitoring**: Captures response times, error rates, and other metrics
4. **Content Analysis**: Analyzes which content is most/least effective

## Security

- Token-based authentication for all admin endpoints
- No sensitive user data stored (queries can be anonymized)
- Configurable data retention periods
- Rate limiting on expensive operations

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest admin/backend/tests/
```

### Database Management
```bash
# The database is automatically created at admin/rag_monitoring.db
# To reset the database, simply delete the file:
rm admin/rag_monitoring.db
```

## Configuration

Environment variables:
- `ADMIN_PORT` - Optional. Port for admin server (default: 8001)
- `ADMIN_DB_PATH` - Optional. Path to SQLite database (default: admin/rag_monitoring.db)

## Deployment

1. **Development**: Run directly with Python
2. **Production**: Use a process manager like systemd, supervisor, or Docker
3. **Reverse Proxy**: Configure nginx/Apache to route `/admin/*` to the admin service

Example nginx configuration:
```nginx
location /admin/ {
    proxy_pass http://localhost:8001/admin/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## Next Steps

1. Implement Vue.js frontend with Vuetify components
2. Add real-time WebSocket updates
3. Create automated reporting and alerts
4. Add more advanced analytics and visualizations
