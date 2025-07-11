# --- 1. Build Stage ---
# This stage installs all dependencies (including devDependencies)
# and builds the React frontend for production.
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# --- 2. Production Stage ---
# This stage uses a lightweight Nginx server to serve the built static files.
FROM nginx:1.25-alpine

# Copy the built assets from the 'builder' stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration to handle SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for the web server
EXPOSE 8080

# The default Nginx CMD will run, starting the server.