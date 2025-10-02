# AI Canvas - Deployment Guide

This is the **AI Canvas Remote MFE** for AI-powered data analysis and visualization.

## Application Info

- **Name**: ai-canvas
- **Port**: 4202 (development) / 80 (container)
- **Type**: Module Federation Remote
- **Exposes**: `./Module` (AppModule)

## Local Development

From the `frontend` directory:

```bash
npm run ng -- serve ai-canvas
```

Access at: http://localhost:4202

## Building

### Development Build

```bash
cd frontend
npm run ng -- build ai-canvas --configuration=development
```

Output: `frontend/dist/ai-canvas/`
Generates: `remoteEntry.js` ✓

### Production Build

```bash
cd frontend
npm run ng -- build ai-canvas --configuration=production
```

Output: `frontend/dist/ai-canvas/`
Generates: `remoteEntry.js` ✓

## Docker Build

### From Project Root

```bash
# Build from democritus root
docker build -f frontend/projects/ai-canvas/Dockerfile -t democritus-ai-canvas:latest ./frontend

# Run
docker run -p 4202:80 democritus-ai-canvas:latest
```

### From Frontend Directory

```bash
# Build from frontend directory
cd frontend
docker build -f projects/ai-canvas/Dockerfile -t democritus-ai-canvas:latest .

# Run
docker run -p 4202:80 democritus-ai-canvas:latest
```

### With Docker Compose

```bash
# From project root
docker compose build frontend-ai-canvas
docker compose up frontend-ai-canvas
```

## Remote Entry Verification

After building, verify `remoteEntry.js` exists:

```bash
ls -la frontend/dist/ai-canvas/remoteEntry.js
```

Access it via HTTP:
```bash
curl http://localhost:4202/remoteEntry.js
```

## Module Federation Config

This app exposes its AppModule:

```javascript
// webpack.config.js
module.exports = withModuleFederationPlugin({
  name: 'ai-canvas',
  exposes: {
    './Module': './projects/ai-canvas/src/app/app.module.ts',
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
name: Build and Deploy AI Canvas

on:
  push:
    branches: [main]
    paths:
      - 'frontend/projects/ai-canvas/**'
      - 'frontend/libs/ui-kit/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          docker build \
            -f frontend/projects/ai-canvas/Dockerfile \
            -t your-registry/democritus-ai-canvas:${{ github.sha }} \
            ./frontend
      
      - name: Verify remoteEntry.js
        run: |
          docker run --rm your-registry/democritus-ai-canvas:${{ github.sha }} \
            ls /usr/share/nginx/html/remoteEntry.js
      
      - name: Push to Registry
        run: |
          docker push your-registry/democritus-ai-canvas:${{ github.sha }}
      
      - name: Deploy
        run: |
          # Your deployment commands here
```

### GitLab CI

```yaml
build-ai-canvas:
  stage: build
  only:
    changes:
      - frontend/projects/ai-canvas/**
      - frontend/libs/ui-kit/**
  script:
    - docker build -f frontend/projects/ai-canvas/Dockerfile -t $CI_REGISTRY_IMAGE/ai-canvas:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/ai-canvas:$CI_COMMIT_SHA
```

## Deployment Considerations

### 1. Independent Deployment
- Can be deployed without redeploying the host
- Host will fetch the latest version on next load
- No need to rebuild host or other remotes when updating

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

## Feature Development

This is a new app ready for AI-powered features:
- Data visualization dashboards
- AI-powered insights
- Machine learning model integration
- Natural language queries
- Predictive analytics

## Testing Remote Loading

Test that the remote can be loaded by the host:

```bash
# Start this remote
docker run -p 4202:80 democritus-ai-canvas:latest

# Verify remoteEntry.js is accessible
curl http://localhost:4202/remoteEntry.js

# Start host (which will load this remote)
# Navigate to http://localhost:4200/ai-canvas
```

## Standalone Deployment

```bash
# Build
cd frontend
npm install
npm run ng -- build ai-canvas --configuration=production

# Deploy dist/ai-canvas/ including remoteEntry.js to:
# - AWS S3 + CloudFront
# - Azure Blob Storage + CDN  
# - Your own NGINX server
# - Any static file hosting

# Verify remoteEntry.js is publicly accessible
curl https://your-cdn.com/remoteEntry.js
```

## Update Process

1. Make changes to ai-canvas
2. Build new version
3. Deploy new version to your hosting
4. Host automatically loads new version on next navigation
5. **No host or other remote redeployment needed** ✨

## Monitoring

Monitor:
- Module Federation errors
- Failed resource loads
- CORS errors in browser console
- Remote loading performance
- AI service integration errors

## Rollback

```bash
# Redeploy previous version
docker run -p 4202:80 your-registry/democritus-ai-canvas:previous-sha

# Or with Kubernetes
kubectl rollout undo deployment/democritus-ai-canvas
```

## Files in This Directory

- `Dockerfile` - Multi-stage Docker build
- `nginx.conf` - NGINX config with CORS
- `webpack.config.js` - Module Federation config (exposes Module)
- `webpack.prod.config.js` - Production config
- `src/` - Application source code

