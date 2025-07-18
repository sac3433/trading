# --- 1. Build Stage ---
FROM node:20-slim AS builder
ARG VITE_CONVEX_URL
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ENV VITE_CONVEX_URL=$VITE_CONVEX_URL
RUN npm run build

# --- 2. Production Stage ---
FROM node:20-slim
# Install nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built React app
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy API server and startup script (note the .cjs extension)
COPY api-server.cjs /app/
COPY start.sh /app/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Install only production dependencies for the API server
COPY package*.json /app/
RUN npm install --only=production

# Make startup script executable
RUN chmod +x /app/start.sh

EXPOSE 8080

# Use the startup script
CMD ["/app/start.sh"]