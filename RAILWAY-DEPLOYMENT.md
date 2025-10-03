# Railway Deployment Guide

This guide explains how to deploy your application with the integrated admin dashboard to Railway.

## Overview

The application is configured to deploy as a single service that includes:
- FastAPI backend (your main application)
- Admin dashboard backend (integrated into main backend)
- Admin dashboard frontend (built and served as static files)

## URLs After Deployment

- **Main Application**: `https://your-app.railway.app/`
- **Admin Dashboard**: `https://your-app.railway.app/admin/dashboard/`
- **Admin API**: `https://your-app.railway.app/admin/api/`
- **API Documentation**: `https://your-app.railway.app/docs`

## Deployment Steps

### 1. Connect Repository to Railway
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

### 2. Configure Environment Variables (Minimal)

This project uses a database-first configuration with code defaults. Only secrets and deployment-specific values must be set in Railway.

Set these in Railway → Variables:

```
# Required secrets
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key
API_KEY_ENCRYPTION_SECRET=<strong-random-secret>   # required in production
IP_HASH_SALT=<strong-random-secret>                # required in production

# Deployment
ENVIRONMENT=production
PUBLIC_API_URL=https://your-app.railway.app

# Optional
PORT=8000
WATCHFILES_FORCE_POLLING=true
```

Generate strong random secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Notes:
- Do not include inline comments in Railway variable values.
- All non-secret settings (LLM models, caching, rate limiting, RAG, search, knowledge) are edited in the Admin UI and stored in the DB.

### 3. Deploy
Railway will automatically:
1. Use the `Dockerfile` to build your application
2. Build the admin frontend during the Docker build process
3. Serve both backend API and frontend static files
4. Deploy to your custom domain

## Local Testing

Test the integrated setup locally:

```bash
# Build admin frontend
npm run admin:build

# Build and run with Docker
npm run backend:build
npm run backend:dev
```

Then visit:
- Backend API: `http://localhost:8000/docs`
- Admin Dashboard: `http://localhost:8000/admin`

## File Structure

```
/
├── Dockerfile                 # Multi-stage build with Node.js and Python
├── railway.toml              # Railway configuration
├── backend/                  # Python FastAPI backend
├── admin/
│   └── frontend/
│       └── dist/            # Built admin frontend (served at /admin/dashboard/)
└── public/                  # Your main application content
```

## Troubleshooting

### Admin Dashboard Not Loading
- Verify admin frontend built correctly (`admin/frontend/dist/` should exist)
- Check Railway logs for any build errors
- Ensure admin database is properly initialized

### API Errors
- Ensure all required environment variables are set (see minimal list above)
- Check Railway application logs for backend errors
- Verify your API keys are valid

### Configuration not applying
- Most settings are DB-backed; make changes in the Admin UI and they take effect without restart.
- Response caching: Admin → Response Settings → enable_caching, enable_response_caching, cache_ttl_seconds.
- Rate limiting: Admin → Security Settings → enable_rate_limiting; Admin → System Config → rate_limit string (e.g., `100/minute`).

### Build Failures
- Ensure Node.js dependencies in `admin/frontend/package.json` are correct
- Check that Python dependencies in `backend/requirements.txt` are up to date
- Review Railway build logs for specific error messages

## Security Notes

- Never commit API keys to your repository
- The admin dashboard is protected by session-based authentication
- All traffic uses HTTPS on Railway by default
- Session cookies use secure attributes and fingerprinting
