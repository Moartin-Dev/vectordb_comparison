# Multi-Stage Build für Angular Frontend
# Stage 1: Build

FROM node:22-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build Angular app for production
RUN npm run build -- --configuration production

# Stage 2: Serve with nginx

FROM nginx:alpine

# Copy built app from build stage
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
