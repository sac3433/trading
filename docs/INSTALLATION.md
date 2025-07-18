# ⚙️ Installation Guide

This guide provides step-by-step instructions for setting up the platform in both development and production environments.

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- **CPU**: 2 cores (ARM64 or x86_64)
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Network**: Stable internet connection

**Recommended Requirements:**
- **CPU**: 4 cores (ARM64 preferred for cost efficiency)
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 100 Mbps+ for real-time data

### Account Requirements
- **ICICI Direct Account**: Active account with ICICI Direct

### Software Dependencies

**Required:**
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+

**For Development:**
- Node.js 20+ with npm
- Python 3.9+ with pip

**For Production:**
- k3s or Docker Swarm (optional)
- Domain name and SSL certificate (recommended)

## 🔑 ICICI Breeze API Setup

### Step-by-Step Setup

**1. Access Breeze Connect Portal**
- Visit: [https://api.icicidirect.com/](https://api.icicidirect.com/)
- Login with your ICICI Direct credentials

**2. Create New Application**
- Navigate to "Create App" section
- Fill in application details:
  - **App Name**: Your application name (e.g., "Trading Data Platform")
  - **Description**: Brief description of usage
  - **Redirect URL**: Use `http://localhost` for local development

**3. Generate API Credentials**
- After app creation, note down:
  - **API Key**: Your unique API key (16-character alphanumeric)
  - **Secret Key**: Your secret key (16-character alphanumeric)
- These credentials are permanent and should be kept secure

**4. Generate Session Token**
- Use your ICICI Direct login credentials to generate session token
- Session tokens expire daily at midnight IST
- Example token format: 8-digit number (e.g., 52209906)
- Source: https://www.icicidirect.com/futures-and-options/api/breeze/article/what-is-a-session-key-and-how-to-generate-it-for-using-breezeapi#:~:text=2.,URL%20in%20the%20address%20bar

## 🚀 Quick Installation (Docker)

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/IndianRobinHood/trading-platform.git
cd trading

# Verify files
ls -la
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```bash
# ICICI Breeze API Configuration
BREEZE_API_KEY=your_16_char_api_key
# Description: API key from ICICI Direct Breeze portal
# Example: BREEZE_API_KEY=1234567890abcdef

BREEZE_SECRET_KEY=your_16_char_secret_key
# Description: Secret key from ICICI Direct Breeze portal  
# Example: BREEZE_SECRET_KEY=abcdef1234567890

BREEZE_SESSION_TOKEN=your_8_digit_token
# Description: Daily session token (fallback if web manager unavailable). This is used for the initial startup and as a fallback if the token manager file is not found. It will be overwritten by the web-based token manager during operation.
# Example: BREEZE_SESSION_TOKEN=52209906

# Convex Database Configuration
CONVEX_URL=https://your-deployment.convex.site
# Description: Convex backend URL for data ingestion
# Example: CONVEX_URL=https://happy-animal-123.convex.site

VITE_CONVEX_URL_PROD=https://your-deployment.convex.cloud
# Description: Convex URL for frontend production build
# Example: VITE_CONVEX_URL_PROD=https://happy-animal-123.convex.cloud

# Market Data Configuration
BREEZE_INTERVAL=1minute
# Options: 1second, 1minute, 5minute, 30minute
# Recommended: 1minute (balances real-time with API limits)

BATCH_SIZE=25
# Number of stocks to subscribe in each batch (1-100)
# Recommended: 25 (prevents API timeouts)

SUBSCRIPTION_DELAY=0.1
# Delay between stock subscriptions in seconds (0.01-1.0)
# Recommended: 0.1 (prevents rate limiting)

# Market Holidays (YYYY-MM-DD format, comma-separated)
MARKET_HOLIDAYS=2025-08-15,2025-08-27,2025-10-02,2025-10-21,2025-10-22,2025-11-05,2025-12-25
# Update: Add/remove holidays per NSE calendar
# Source: https://www.nseindia.com/resources/exchange-communication-holidays

# Optional: Advanced Configuration
BREEZE_MASTER_URL=https://directlink.icicidirect.com/NewSecurityMaster/SecurityMaster.zip
CACHE_LIFETIME_HOURS=23
```

### 3. Convex Backend Setup

**Prerequisites:**
```bash
# Ensure you're in the project directory with package.json
cd trading
ls package.json  # Should exist from the cloned repo
```

**Install Convex:**
```bash
# Install Convex as project dependency (to install the CLI)
npm install convex

# Install Convex CLI globally (optional, for easier commands)
npm install -g convex

# Login to your Convex account and follow instructions
npx convex login
```

**Development Setup:**
```bash
# Initialize and start development backend (follow instructions on the CLI)

npx convex dev

# This command links your cloned project to your Convex account.
# Follow the CLI prompts. It will:
# - Create a new project in your Convex dashboard.
# - Generate a .env.local file with your new CONVEX_DEPLOYMENT key.
# - Provide you with the development URLs needed for the next steps.
```

**Production Setup:**
```bash
# Deploy to production
npx convex deploy

# This gives you production URLs:
# Frontend: https://grateful-mink-123.convex.cloud  
# HTTP Actions: https://grateful-mink-123.convex.site
```

### Which Convex Command Should I Use?

Convex provides two main commands for two different purposes. Choose the one that matches your goal:

* **For Development & Testing (`npx convex dev`)**:
    * Use this if you want to run the app on your local machine to test it, explore the code, or contribute changes.
    * It creates a **private development backend** that syncs with your local code in real-time.
    * This is the command you will use most often while coding.

* **For a Live Public Website (`npx convex deploy`)**:
    * Use this only when you are ready to launch your own **live, public version** of this platform for others to use.
    * It creates a **permanent production backend** that is stable and optimized for performance.
    * The `docker-compose.prod.yml` file is configured to work with this production deployment.



**Update Environment Variables:**
```bash
# Add to your .env file
echo "CONVEX_URL=https://grateful-mink-123.convex.site" >> .env
echo "VITE_CONVEX_URL_PROD=https://grateful-mink-123.convex.cloud" >> .env
```

The key point: **Convex needs an existing Node.js project with `package.json`** before you can run any Convex commands. The repo already has this structure.

### 4. Start Services

**Development Environment:**
```bash
# Start all services with hot-reload
docker-compose up

# Or run in background  
docker-compose up -d

# View logs
docker-compose logs -f
```

**Production Environment:**
```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Verify Installation

**Check Service Status:**
```bash
# All containers should be running
docker ps

# Expected output:
# indianrobinhood-frontend   (port 8002)
# indianrobinhood-ingestor   (internal only)

# Check logs for errors or details
docker logs indianrobinhood-frontend
docker logs indianrobinhood-ingestor
```

**Access Application:**
- **Frontend**: http://localhost:8002 (production) or http://localhost:5173 (development)
- **Health Check**: http://localhost:8002/api/health
- **Token Manager**: http://localhost:8002 → Token Manager section

## 🌐 Production Deployment

### Single Server (Recommended)

**Server Setup (Linux):**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin

# Clone and configure
git clone https://github.com/IndianRobinHood/trading-platform.git
cd trading
cp .env.example .env
nano .env  # Configure with production values
```

**Deploy:**
```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Enable auto-restart
docker update --restart unless-stopped indianrobinhood-frontend
docker update --restart unless-stopped indianrobinhood-ingestor

# Check status
docker-compose -f docker-compose.prod.yml ps
```

## 🔍 Troubleshooting

### Common Issues

**1. Container Won't Start**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check port conflicts  
sudo netstat -tulpn | grep :8002

# Check volume permissions
ls -la /var/lib/docker/volumes/
```

**2. Token Management Issues**
```bash
# Check token file exists and is readable
docker exec indianrobinhood-frontend cat /app/config/session_token.txt

# Test token update API
curl -X POST http://localhost:8002/api/update-token \
  -H "Content-Type: application/json" \
  -d '{"token":"12345678"}'
```

**3. Data Ingestion Problems**
```bash
# Check if market is open (9:15 AM - 3:30 PM IST)
date -d "TZ=\"Asia/Kolkata\"" '+%Y-%m-%d %H:%M:%S %Z'

# Check ingestor logs during market hours
docker logs indianrobinhood-ingestor --since 5m

# Verify Convex connectivity
curl -I $CONVEX_URL
```

## 📊 Performance Optimization

### Resource Monitoring
```bash
# Monitor container resources
docker stats

# Check disk usage
docker system df

# Clean up if needed
docker system prune -a
```

### Configuration Tuning
```bash
# For high-performance setup
BREEZE_INTERVAL=1second      # Real-time data
BATCH_SIZE=50               # Larger batches (if stable)
SUBSCRIPTION_DELAY=0.05     # Faster subscriptions

# For resource-constrained setup  
BREEZE_INTERVAL=5minute     # Reduced frequency
BATCH_SIZE=10               # Smaller batches
SUBSCRIPTION_DELAY=0.2      # More conservative timing
```

## 🔐 Security Best Practices

### Environment Security
```bash
# Set proper file permissions
chmod 600 .env
chmod 600 /app/config/session_token.txt

# Use Docker secrets in production
echo "your_api_key" | docker secret create breeze_api_key -
```

### Network Security
```bash
# Add firewall rules (UFW example)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8002/tcp  # Application
sudo ufw enable
```

## ✅ Installation Checklist

- [ ] ICICI Direct account active with API access
- [ ] Breeze Connect app created and credentials obtained
- [ ] Server meets minimum requirements
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned and .env configured
- [ ] Convex project created and URL configured
- [ ] Services started successfully (docker ps shows both containers)
- [ ] Frontend accessible on http://server-ip:8002
- [ ] Token manager accessible and functional
- [ ] Logs show no critical errors during startup
- [ ] Data ingestion working during market hours (check logs)

## 🎯 Next Steps

After successful installation:

1. **Monitor During Market Hours**: Check data ingestion between 9:15 AM - 3:30 PM IST
2. **Set Up Alerts**: Configure monitoring for container health and API errors
3. **SSL Certificate**: Obtain HTTPS certificate for production (Let's Encrypt)
4. **Backup Strategy**: Plan for data and configuration backups
5. **Update Procedure**: Establish process for updating containers and dependencies

## 📚 Additional Resources

- **Configuration Details**: See [CONFIGURATION.md](CONFIGURATION.md)
- **Token Management**: See [TOKEN_MANAGEMENT.md](TOKEN_MANAGEMENT.md)
- **Breeze API Docs**: https://api.icicidirect.com/breezeapi/documents/
- **Convex Documentation**: https://docs.convex.dev/
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/

For issues not covered here, create an issue on GitHub. 