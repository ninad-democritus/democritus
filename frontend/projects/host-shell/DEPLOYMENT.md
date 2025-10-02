# Host Shell - Deployment Guide

This is the **MFE Host Application** that orchestrates and loads the remote micro-frontends.

## Application Info

- **Name**: host-shell
- **Port**: 4200 (development) / 80 (container)
- **Type**: Module Federation Host
- **Dependencies**: None (loads remotes dynamically)

## Local Development

From the `frontend` directory:

```bash
npm run ng -- serve host-shell
```

Access at: http://localhost:4200

## Building

### Development Build

```bash
cd frontend
npm run ng -- build host-shell --configuration=development
```

Output: `frontend/dist/host-shell/`

### Production Build

```bash
cd frontend
npm run ng -- build host-shell --configuration=production
```

Output: `frontend/dist/host-shell/`

## Docker Build

### From Project Root

```bash
# Build from democritus root
docker build -f frontend/projects/host-shell/Dockerfile -t democritus-host:latest ./frontend

# Run
docker run -p 4200:80 democritus-host:latest
```

### From Frontend Directory

```bash
# Build from frontend directory
cd frontend
docker build -f projects/host-shell/Dockerfile -t democritus-host:latest .

# Run
docker run -p 4200:80 democritus-host:latest
```

### With Docker Compose

```bash
# From project root
docker compose build frontend-host
docker compose up frontend-host
```

## Environment Configuration

The host needs to know where the remotes are hosted.

### Development (Local)
Remotes configured in `webpack.config.js`:
```javascript
remotes: {
  "ingestionApp": "http://localhost:4201/remoteEntry.js",
  "aiCanvas": "http://localhost:4202/remoteEntry.js"
}
```

### Production
Update `webpack.prod.config.js` or use environment variables to point to production URLs:
```javascript
remotes: {
  "ingestionApp": "https://ingestion.yourdomain.com/remoteEntry.js",
  "aiCanvas": "https://ai-canvas.yourdomain.com/remoteEntry.js"
}
```

## CI/CD Pipeline Example

### GitHub Actions

```yaml
name: Build and Deploy Host Shell

on:
  push:
    branches: [main]
    paths:
      - 'frontend/projects/host-shell/**'
      - 'frontend/libs/ui-kit/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          docker build \
            -f frontend/projects/host-shell/Dockerfile \
            -t your-registry/democritus-host:${{ github.sha }} \
            ./frontend
      
      - name: Push to Registry
        run: |
          docker push your-registry/democritus-host:${{ github.sha }}
      
      - name: Deploy
        run: |
          # Your deployment commands here
```

### GitLab CI

```yaml
build-host:
  stage: build
  only:
    changes:
      - frontend/projects/host-shell/**
      - frontend/libs/ui-kit/**
  script:
    - docker build -f frontend/projects/host-shell/Dockerfile -t $CI_REGISTRY_IMAGE/host:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/host:$CI_COMMIT_SHA
```

## Deployment Considerations

### 1. Remote URLs
- Ensure webpack config points to correct remote URLs for your environment
- Consider using environment variables for runtime configuration

### 2. CORS
- Host doesn't need CORS headers
- Remotes must have CORS enabled to be loaded by the host

### 3. Caching
- Host application can be cached aggressively
- Updates to host require redeployment
- Changes to remotes don't require host redeployment

### 4. Health Checks
The NGINX config serves a simple static site, health check:
```bash
curl http://localhost:80/
```

### 5. Dependencies
- Host shares Angular, RxJS, and other dependencies with remotes
- Ensure version compatibility across all MFEs

## Standalone Deployment

This app can be deployed completely independently:

```bash
# Build standalone
cd frontend
npm install
npm run ng -- build host-shell --configuration=production

# Deploy dist/host-shell/ to any static hosting:
# - AWS S3 + CloudFront
# - Azure Blob Storage + CDN
# - Netlify
# - Vercel
# - GitHub Pages
# - Your own NGINX server
```

## Monitoring

Add monitoring to track:
- Failed remote loads
- Module Federation errors
- Route navigation performance
- Remote loading times

## Rollback

To rollback to a previous version:
```bash
# Redeploy previous Docker image
docker run -p 4200:80 your-registry/democritus-host:previous-sha

# Or with Kubernetes
kubectl rollout undo deployment/democritus-host
```

## Files in This Directory

- `Dockerfile` - Multi-stage Docker build
- `nginx.conf` - NGINX configuration
- `webpack.config.js` - Module Federation config (dev)
- `webpack.prod.config.js` - Module Federation config (prod)
- `src/` - Application source code

