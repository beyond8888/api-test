# ─── Stage 1: Build Vue app ───────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Install deps first (cached layer — only rebuilds when package.json changes)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ─── Stage 2: Serve with nginx ────────────────────────────────
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O - http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
