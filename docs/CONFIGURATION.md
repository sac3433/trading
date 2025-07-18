# 🔧 Configuration Reference

This document provides a comprehensive reference for all configuration options for the NSE realtime data.

## 📁 Configuration Files

### Primary Configuration
- **`.env`**: Main environment variables file
- **`docker-compose.yml`**: Development environment setup
- **`docker-compose.prod.yml`**: Production environment setup
- **`/app/config/session_token.txt`**: Hot-reload ICICI Breeze session token (runtime). Please note ICICI Breeze token expires daily.

### Secondary Configuration
- **`convex/schema.ts`**: Database schema definition
- **`nginx.conf`**: Web server configuration
- **`requirements.txt`**: Python dependencies for data ingestor
- **`package.json`**: Node.js dependencies for frontend

## 🔑 Environment Variables

### Breeze API Configuration

```bash
# Required: Breeze API Credentials
BREEZE_API_KEY=your_api_key_here
# Description: API key from ICICI Direct Breeze portal
# Example: BREEZE_API_KEY=1234567890abcdef
# Required: Yes

BREEZE_SECRET_KEY=your_secret_key_here  
# Description: Secret key from ICICI Direct Breeze portal
# Example: BREEZE_SECRET_KEY=abcdef1234567890
# Required: Yes

BREEZE_SESSION_TOKEN=your_session_token_here
# Description: Session token obtained after login (fallback if file doesn't exist)
# Example: BREEZE_SESSION_TOKEN=52209906
# Required: Yes (unless using web token manager)
```

### Convex Database Configuration

```bash
# Required: Convex Backend URL
CONVEX_URL=https://your-deployment.convex.site
# Description: Convex backend URL for data ingestion service
# Example: CONVEX_URL=https://happy-animal-123.convex.site
# Required: Yes

VITE_CONVEX_URL_PROD=https://your-deployment.convex.cloud
# Description: Convex URL for frontend production build
# Example: VITE_CONVEX_URL_PROD=https://happy-animal-123.convex.cloud
# Required: Yes
```

### Market Data Configuration

```bash
# Data Update Frequency
BREEZE_INTERVAL=1second
# Description: OHLCV data interval frequency
# Options: 1second, 1minute, 5minute, 30minute

# Subscription Management  
BATCH_SIZE=20
# Description: Number of stocks to subscribe to in each batch
# Note: Higher values may cause API timeouts

SUBSCRIPTION_DELAY=0.1
# Description: Delay between individual stock subscriptions (seconds)
# Range: 0.01-1.0
# Default: 0.1
# Note: Prevents API rate limiting
```

### Market Hours & Holidays

```bash
# Market Holidays (YYYY-MM-DD format, comma-separated)
MARKET_HOLIDAYS=
# Description: Days when Indian stock market is closed
# Format: YYYY-MM-DD,YYYY-MM-DD,...
# Update: Add/remove holidays as per NSE exchange calendar - https://www.nseindia.com/resources/exchange-communication-holidays

# Market Hours (automatically handled, configurable in code)
# MARKET_SESSION_START=09:00 IST (15 min before market open)
# MARKET_OPEN=09:15 IST
# MARKET_CLOSE=15:30 IST  
# MARKET_SESSION_END=15:40 IST (capture final bars)
```

### Data Source Configuration

```bash
# NSE Master File URL
BREEZE_MASTER_URL=https://directlink.icicidirect.com/NewSecurityMaster/SecurityMaster.zip
# Description: URL for NSE stock symbols master file
# You can download the Security Master file for token mapping at your end. It is generated/updated daily at 8:00 AM.
# Source: https://api.icicidirect.com/breezeapi/documents/index.html#introduction

# Cache Configuration
CACHE_LIFETIME_HOURS=23
# Description: Hours to cache master file before re-downloading
# Range: 1-48
# Default: 23 (refresh daily)
# Note: Reduces API calls and improves startup time
```

## 🐳 Docker Configuration

### Development Environment (`docker-compose.yml`)

```yaml
# Service Ports
services:
  convex:
    ports:
      - "3210:3210"    # Convex backend
      - "6790:6790"    # Convex dashboard
  
  frontend:
    ports:
      - "5173:5173"    # Vite dev server
    
  ingestor:
    # No exposed ports (internal only)

# Environment Overrides
environment:
  - CONVEX_URL=http://convex:3210              # Internal service URL
  - VITE_CONVEX_URL=http://convex:3210         # Frontend to backend
```

### Production Environment (`docker-compose.prod.yml`)

```yaml
# Service Ports
services:
  frontend:
    ports:
      - "8002:8080"    # Nginx + Express API
    
  ingestor:
    # No exposed ports (internal only)

# Volume Configuration
volumes:
  token_config:        # Shared token storage
    driver: local
  ingestor_cache:      # NSE master file cache
    driver: local
```

## 🌐 Network Configuration

### Frontend Service (Nginx + Express)

```nginx
# nginx.conf
server {
    listen 8080;
    server_name localhost;
    
    # Static file serving for React app
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy to Express server for token management
    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Express API Server for hot-reload token management system

**How the Token Bridge Works:**

1.**React UI** → collects the new session token from the user.
2.**Express API** → receives the token via the `/api/update-token` endpoint.
3.**File System** → Express writes the token to a shared volume at `/app/config/session_token.txt`.
4.**Python Ingestor** → reads the updated token from the shared volume file, achieving a "hot-reload" without a restart.


```javascript
// api-server.cjs configuration
const PORT = 3000;                    // Internal API port
const TOKEN_FILE_PATH = '/app/config/session_token.txt';  // Shared volume path

// CORS configuration for token management
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});
```

## 💾 Database Configuration

### Convex Schema (`convex/schema.ts`)

```typescript
// OHLCV Data Table for NSE stocks
ohlcv: defineTable({
  stock_code: v.string(),    // NSE symbol (indexed)
  open: v.number(),          // Opening price
  high: v.number(),          // High price  
  low: v.number(),           // Low price
  close: v.number(),         // Closing/current price
  volume: v.number(),        // Trading volume
  interval: v.string(),      // Time interval
  timestamp: v.number(),     // Unix timestamp (UTC)
}).index("by_stock_code", ["stock_code"])
```

### Database Implementation Notes

- **Index Usage**: Primary index `by_stock_code` for fast lookups
- **Upsert Logic**: Prevents duplicates, maintains latest data  
- **Stock Coverage**: ~2400 NSE stocks supported

## 📊 Performance Configuration

### Resource Limits

```yaml
# Docker resource limits (add to docker-compose.prod.yml if needed)
services:
  frontend:
    deploy:
      resources:
        limits:
          memory: 512M          # React app + Nginx + Express API
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
  
  ingestor:
    deploy:
      resources:
        limits:
          memory: 1G            # Python + data processing
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

### API Rate Limiting

```bash
# Breeze API rate limits (built into ingestor)
SUBSCRIPTION_DELAY=0.1        # Delay between stock subscriptions
BATCH_SIZE=25                 # Stocks per subscription batch
REQUEST_TIMEOUT=3             # HTTP request timeout (seconds)
CONNECTION_POOL_SIZE=20       # HTTP connection pool for Convex
MAX_RETRIES=1                 # Request retry attempts
```

## 🔧 Advanced Configuration

### Custom Market Hours

```python
# breeze_ingestor.py - Modify these functions for custom trading hours
def is_market_session_time():
    session_start = now.replace(hour=9, minute=0)    # 9:00 AM (prep time)
    session_end = now.replace(hour=15, minute=40)    # 3:40 PM (capture final)
    return session_start <= now <= session_end

def is_market_open():
    market_open = now.replace(hour=9, minute=15)     # 9:15 AM NSE open
    market_close = now.replace(hour=15, minute=30)   # 3:30 PM NSE close
    return market_open <= now <= market_close
```

### Custom Stock Filtering

```python
# breeze_ingestor.py - Modify get_nse_cash_stock_tokens()
def get_nse_cash_stock_tokens():
    # Default: All cash equities (Series == 'EQ')
    cash_stocks = df[df['Series'] == 'EQ'].copy()
    
    return tokens
```

### Logging Configuration

```python
# breeze_ingestor.py - Logging levels and output
logging.basicConfig(
    level=logging.INFO,           # Options: DEBUG, INFO, WARNING, ERROR
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("./logs/ingestor.log"),  # File output
        logging.StreamHandler()                       # Console output
    ]
)
```

## 🔐 Security Configuration

### API Security

```bash
# Environment variable security
# Never commit .env files to version control
# Use secrets management in production

# Example: Docker secrets (production)
echo "your_api_key" | docker secret create breeze_api_key -
echo "your_secret" | docker secret create breeze_secret -
```

### File Permissions

```bash
# Token file permissions
chmod 600 /app/config/session_token.txt    # Read/write for owner only
chown app:app /app/config/session_token.txt # Correct ownership
```

### Network Security

```nginx
# nginx.conf - Security headers
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000";
```

## 🎯 Environment-Specific Configurations

### Development
- **Data Frequency**: 5minute (reduce API calls)
- **Stock Limit**: 100 (faster testing)
- **Logging**: DEBUG level
- **Hot Reload**: Enabled for frontend and ingestor

### Production
- **Data Frequency**: 1second (full real-time)
- **Stock Limit**: 0 (all ~2400 NSE stocks)
- **Logging**: INFO level with rotation
- **Monitoring**: Health checks and error alerting

## 📖 Configuration Examples

### Minimal Development Setup
```bash
# .env for development
BREEZE_API_KEY=your_key
BREEZE_SECRET_KEY=your_secret  
BREEZE_SESSION_TOKEN=your_token
CONVEX_URL=http://localhost:3210
BREEZE_INTERVAL=5minute
```

### Production Setup
```bash
# .env for production
BREEZE_API_KEY=your_key
BREEZE_SECRET_KEY=your_secret
BREEZE_SESSION_TOKEN=your_token
CONVEX_URL=https://your-prod.convex.site
VITE_CONVEX_URL_PROD=https://your-prod.convex.cloud
BREEZE_INTERVAL=1second
BATCH_SIZE=25
MARKET_HOLIDAYS=2025-08-15,2025-08-27
```

---

For additional configuration help, see [INSTALLATION.md](INSTALLATION.md) or create an issue on GitHub. 