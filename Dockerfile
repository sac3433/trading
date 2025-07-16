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
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080