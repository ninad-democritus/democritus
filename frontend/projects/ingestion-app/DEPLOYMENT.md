# Ingestion App - Deployment Guide

This is the **Data Ingestion Remote MFE** that handles file uploads and data ingestion workflows.

## Application Info

- **Name**: ingestion-app
- **Port**: 4201 (development) / 80 (container)
- **Type**: Module Federation Remote
- **Exposes**: `./Module` (AppModule)

## Local Development

From the `frontend` directory:

```bash
npm run ng -- serve ingestion-app
```

Access at: http://localhost:4201

## Building

### Development Build

```bash
cd frontend
npm run ng -- build ingestion-app --configuration=development
```

Output: `frontend/dist/ingestion-app/`
Generates: `remoteEntry.js` ✓

### Production Build

```bash
cd frontend
npm run ng -- build ingestion-app --configuration=production
```

Output: `frontend/dist/ingestion-app/`
Generates: `remoteEntry.js` ✓

## Docker Build

### From Project Root

```bash
# Build from democritus root
docker build -f frontend/projects/ingestion-app/Dockerfile -t democritus-ingestion:latest ./frontend

# Run
docker run -p 4201:80 democritus-ingestion:latest
```

### From Frontend Directory

```bash
# Build from frontend directory
cd frontend
docker build -f projects/ingestion-app/Dockerfile -t democritus-ingestion:latest .

# Run
docker run -p 4201:80 democritus-ingestion:latest
```

### With Docker Compose

```bash
# From project root
docker compose build frontend-ingestion
docker compose up frontend-ingestion
```

## Remote Entry Verification

After building, verify `remoteEntry.js` exists:

```bash
ls -la frontend/dist/ingestion-app/remoteEntry.js
```

Access it via HTTP:
```bash
curl http://localhost:4201/remoteEntry.js
```

## Module Federation Config

This app exposes its AppModule:

```javascript
// webpack.config.js
module.exports = withModuleFederationPlugin({
  name: 'ingestion-app',
  exposes: {
    './Module': './projects/ingestion-app/src/app/app.module.ts',
  },
  shared: {
    ...shareAll({ singleton: true, strictVersion: true, requiredVersion: 'auto' }),
  },
});
```

## CORS Configuration

**Critical**: This remote MUST have CORS enabled to be loaded by the host.

NGINX config includes:
```nginx
add_header 'Access-Control-Allow-Origin' '*' always;
add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
```

For production, restrict CORS to your host domain:
```nginx
add_header 'Access-Control-Allow-Origin' 'https://your-host-domain.com' always;
```

## CI/CD Pipeline Example

### GitHub Actions

```yaml
name: Build and Deploy Ingestion App

on:
  push:
    branches: [main]
    paths:
      - 'frontend/projects/ingestion-app/**'
      - 'frontend/libs/ui-kit/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          docker build \
            -f frontend/projects/ingestion-app/Dockerfile \
            -t your-registry/democritus-ingestion:${{ github.sha }} \
            ./frontend
      
      - name: Verify remoteEntry.js
        run: |
          docker run --rm your-registry/democritus-ingestion:${{ github.sha }} \
            ls /usr/share/nginx/html/remoteEntry.js
      
      - name: Push to Registry
        run: |
          docker push your-registry/democritus-ingestion:${{ github.sha }}
      
      - name: Deploy
        run: |
          # Your deployment commands here
```

### GitLab CI

```yaml
build-ingestion:
  stage: build
  only:
    changes:
      - frontend/projects/ingestion-app/**
      - frontend/libs/ui-kit/**
  script:
    - docker build -f frontend/projects/ingestion-app/Dockerfile -t $CI_REGISTRY_IMAGE/ingestion:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/ingestion:$CI_COMMIT_SHA
```

## Deployment Considerations

### 1. Independent Deployment
- Can be deployed without redeploying the host
- Host will fetch the latest version on next load
- No need to rebuild host when updating this remote

### 2. CORS Requirements
- **Must** allow cross-origin requests from host domain
- Update CORS headers in production nginx.conf

### 3. CDN Deployment
Consider deploying to CDN for better performance:
- AWS CloudFront
- Azure CDN
- Cloudflare
- Fastly

### 4. remoteEntry.js Caching
**Critical**: Never cache `remoteEntry.js`

NGINX config ensures this:
```nginx
location ~* remoteEntry\.js$ {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

### 5. Static Assets Caching
Other assets (JS, CSS) can be cached aggressively:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Backend Integration

This app communicates with backend services:
- `/v1/files/*` - File upload service
- `/v1/workflows/*` - Workflow orchestration
- `/v1/pipelines/*` - Data pipeline service

Ensure these are properly proxied through your infrastructure.

## Testing Remote Loading

Test that the remote can be loaded by the host:

```bash
# Start this remote
docker run -p 4201:80 democritus-ingestion:latest

# Verify remoteEntry.js is accessible
curl http://localhost:4201/remoteEntry.js

# Start host (which will load this remote)
# Navigate to http://localhost:4200/ingestion
```

## Standalone Deployment

```bash
# Build
cd frontend
npm install
npm run ng -- build ingestion-app --configuration=production

# Deploy dist/ingestion-app/ including remoteEntry.js to:
# - AWS S3 + CloudFront
# - Azure Blob Storage + CDN  
# - Your own NGINX server
# - Any static file hosting

# Verify remoteEntry.js is publicly accessible
curl https://your-cdn.com/remoteEntry.js
```

## Update Process

1. Make changes to ingestion-app
2. Build new version
3. Deploy new version to your hosting
4. Host automatically loads new version on next navigation
5. **No host redeployment needed** ✨

## Monitoring

Monitor:
- Module Federation errors
- Failed resource loads
- CORS errors in browser console
- Remote loading performance

## Rollback

```bash
# Redeploy previous version
docker run -p 4201:80 your-registry/democritus-ingestion:previous-sha

# Or with Kubernetes
kubectl rollout undo deployment/democritus-ingestion
```

## Files in This Directory

- `Dockerfile` - Multi-stage Docker build
- `nginx.conf` - NGINX config with CORS
- `webpack.config.js` - Module Federation config (exposes Module)
- `webpack.prod.config.js` - Production config
- `src/` - Application source code

