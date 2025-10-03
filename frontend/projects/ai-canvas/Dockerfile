# Stage 1: Build the Angular Remote Application
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build shared libraries first (required dependencies)
RUN npm run ng -- build ui-kit
RUN npm run ng -- build shared-ui

# Build the ai-canvas application
RUN npm run ng -- build ai-canvas

# Stage 2: Serve with NGINX
FROM nginx:alpine

# Copy custom nginx config
COPY projects/ai-canvas/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application
COPY --from=build /app/dist/ai-canvas /usr/share/nginx/html

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]


