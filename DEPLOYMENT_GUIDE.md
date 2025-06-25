# 🚀 AI Chatbot Webhook Deployment Guide

## 📋 Overview
This guide provides step-by-step instructions for deploying the AI Chatbot Webhook application using Docker in production.

## 🛠️ Prerequisites

### Required Software
- **Docker Desktop** (Windows)
- **Git** (for version control)
- **Text Editor** (VS Code recommended)

### Required Files
Ensure these files exist in your project directory:
- `webhook.py` - Main application file
- `Dockerfile` - Docker configuration
- `requirements.txt` - Python dependencies
- `.env` - Environment variables
- `data/import/sample.csv` - Sample data file

## 📁 Project Structure
```
aichatbot/
├── webhook.py
├── Dockerfile
├── requirements.txt
├── .env
├── data/
│   └── import/
│       └── sample.csv
└── DEPLOYMENT_GUIDE.md
```

## 🔧 Setup Instructions

### Step 1: Environment Configuration
Create or update your `.env` file:

```bash
# Google Chat Webhook Configuration
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/YOUR_SPACE/messages?key=YOUR_KEY&token=YOUR_TOKEN

# Flask Environment
FLASK_ENV=production
```

> ⚠️ **Security Note**: Never commit the `.env` file to version control. Add it to `.gitignore`.

### Step 2: Verify Dockerfile
Ensure your `Dockerfile` contains:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5001

# Run with Gunicorn (Production WSGI Server)
CMD ["gunicorn", "-b", "0.0.0.0:5001", "--timeout=300", "--workers=4", "--threads=5", "--worker-class=gthread", "webhook:app"]
```

### Step 3: Verify Dependencies
Check your `requirements.txt` includes:

```txt
Flask==2.3.3
python-dotenv==1.0.0
requests==2.31.0
pandas==2.0.3
gunicorn==21.2.0
```

## 🐳 Docker Deployment

### Option 1: Using Environment File (Recommended)

```bash
# Navigate to project directory
cd c:\Users\sluon\Downloads\projects\kv_hackathon\aichatbot

# Build Docker image
docker build -t webhook-app .

# Run container with environment file
docker run -d -p 8080:5001 --env-file .env --name ai-chatbot-webhook webhook-app
```

### Option 2: Direct Environment Variables

```bash
# Build Docker image
docker build -t webhook-app .

# Run with direct environment variables
docker run -d -p 8080:5001 \
  -e GOOGLE_CHAT_WEBHOOK_URL="your_webhook_url_here" \
  -e FLASK_ENV="production" \
  --name ai-chatbot-webhook \
  webhook-app
```

### Option 3: Development Mode

```bash
# For development with live code changes
docker run -p 8080:5001 \
  --env-file .env \
  -v ${PWD}:/app \
  --name ai-chatbot-webhook-dev \
  webhook-app
```

## 🧪 Testing Your Deployment

### Health Check Endpoints

```bash
# Test home endpoint
curl http://localhost:8080/

# Test webhook endpoint (triggers report)
curl -X POST http://localhost:8080/webhook

# Test message sending
curl http://localhost:8080/test-send
```

### Expected Responses

**Home Endpoint (`/`)**:
```json
{"message": "AI Chatbot Webhook is running!", "status": "OK"}
```

**Webhook Endpoint (`/webhook`)**:
```json
{"status": "Report sent successfully."}
```

**Test Send (`/test-send`)**:
```
Test message sent.
```

## 📊 Application Features

### Daily Report Includes:
- 📍 **Total Active Merchants**: Current count with formatting
- 🆕 **New Merchants Today**: Daily additions
- 📊 **Comparison Analytics**: 
  - Percentage change vs. yesterday
  - Trend indicators (📈 increase, 📉 decrease, ➡️ stable)
  - Absolute change numbers
- 📈 **Forecast Chart**: Interactive prediction visualization
- 🚨 **Anomaly Detection**: Automatic unusual pattern detection

### Sample Report Output:
```
📊 Daily Retail Active Report - 30/06/2025

🏪 Active Merchants Overview
📍 Total active merchants: 207,798
🆕 New merchants today: 122

📊 Comparison with Yesterday
🔄 Active merchants: 📉 decreased 0.16% (-331 merchants)
🆕 New merchants: 📈 increased 65.27% (+48 merchants)

📈 Forecast & Analysis
[Chart Button] View Forecast Chart

🚨 Anomaly Detection (if applicable)
[Chart Button] View Anomaly Details
```

## 🔍 Docker Management Commands

### Container Operations
```bash
# List running containers
docker ps

# View container logs
docker logs ai-chatbot-webhook

# Stop container
docker stop ai-chatbot-webhook

# Start stopped container
docker start ai-chatbot-webhook

# Remove container
docker rm ai-chatbot-webhook

# Remove image
docker rmi webhook-app
```

### Troubleshooting Commands
```bash
# Execute shell in running container
docker exec -it ai-chatbot-webhook /bin/bash

# View container resource usage
docker stats ai-chatbot-webhook

# Inspect container configuration
docker inspect ai-chatbot-webhook
```

## 🛠️ Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Find process using port 8080
netstat -ano | findstr :8080

# Kill process (replace PID)
taskkill /PID [PID_NUMBER] /F
```

**2. Environment Variables Not Loading**
- Verify `.env` file format (no quotes around values)
- Check file encoding (UTF-8)
- Ensure no trailing spaces

**3. Data File Not Found**
- Verify `data/import/sample.csv` exists
- Check file permissions
- Ensure proper CSV format

**4. Google Chat Webhook Issues**
- Verify webhook URL format
- Test webhook URL directly
- Check Google Chat space permissions

### Log Analysis
```bash
# View real-time logs
docker logs -f ai-chatbot-webhook

# View last 100 log lines
docker logs --tail 100 ai-chatbot-webhook
```

## 📈 Performance Optimization

### Production Configuration
The Docker setup includes optimized Gunicorn settings:
- **Workers**: 4 (adjust based on CPU cores)
- **Threads**: 5 per worker
- **Timeout**: 300 seconds
- **Worker Class**: gthread (hybrid threading)

### Resource Monitoring
```bash
# Monitor container resources
docker stats ai-chatbot-webhook

# Set memory limits (optional)
docker run -d -p 8080:5001 --memory="512m" --env-file .env webhook-app
```

## 🔒 Security Considerations

1. **Environment Variables**: Never hardcode sensitive data
2. **Network Security**: Use reverse proxy (nginx) in production
3. **Container Security**: Run as non-root user
4. **SSL/TLS**: Implement HTTPS in production
5. **Access Control**: Limit webhook access to authorized sources

## 📝 Maintenance

### Regular Tasks
- Monitor application logs daily
- Update dependencies monthly
- Backup data files regularly
- Review and rotate webhook URLs quarterly

### Updates
```bash
# Rebuild with updates
docker build -t webhook-app:v2 .

# Deploy new version
docker stop ai-chatbot-webhook
docker rm ai-chatbot-webhook
docker run -d -p 8080:5001 --env-file .env --name ai-chatbot-webhook webhook-app:v2
```

## 📞 Support

For issues or questions:
1. Check container logs first
2. Verify environment configuration
3. Test individual endpoints
4. Review this deployment guide

---

**Last Updated**: June 25, 2025  
**Version**: 1.0  
**Maintainer**: AI Chatbot Webhook Team