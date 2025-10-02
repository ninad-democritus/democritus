# Deployment Architecture - Independent MFE Deployment

## Overview

Each MFE application now has its **own Dockerfile in its directory**, enabling completely independent deployment pipelines while maintaining the shared workspace for development.

## Directory Structure

```
frontend/
├── projects/
│   ├── host-shell/
│   │   ├── Dockerfile          ← Build from here
│   │   ├── DEPLOYMENT.md       ← Deployment guide
│   │   ├── nginx.conf
│   │   └── src/
│   │
│   ├── ingestion-app/
│   │   ├── Dockerfile          ← Build from here
│   │   ├── DEPLOYMENT.md       ← Deployment guide
│   │   ├── nginx.conf
│   │   └── src/
│   │
│   └── ai-canvas/
│       ├── Dockerfile          ← Build from here
│       ├── DEPLOYMENT.md       ← Deployment guide
│       ├── nginx.conf
│       └── src/
│
├── libs/ui-kit/                ← Shared by all apps
└── package.json                ← Shared dependencies
```

## Build Commands

### Host Shell

```bash
# From project root
docker build -f frontend/projects/host-shell/Dockerfile -t democritus-host:latest ./frontend

# From frontend directory
cd frontend
docker build -f projects/host-shell/Dockerfile -t democritus-host:latest .
```

### Ingestion App

```bash
# From project root
docker build -f frontend/projects/ingestion-app/Dockerfile -t democritus-ingestion:latest ./frontend

# From frontend directory
cd frontend
docker build -f projects/ingestion-app/Dockerfile -t democritus-ingestion:latest .
```

### AI Canvas

```bash
# From project root
docker build -f frontend/projects/ai-canvas/Dockerfile -t democritus-ai-canvas:latest ./frontend

# From frontend directory
cd frontend
docker build -f projects/ai-canvas/Dockerfile -t democritus-ai-canvas:latest .
```

## Why This Architecture?

### ✅ Benefits

1. **Independent CI/CD Pipelines**
   - Each app can have its own GitHub Actions / GitLab CI pipeline
   - Trigger builds only when specific app changes
   - Deploy apps independently

2. **Clear Ownership**
   - Each team owns their app's deployment
   - Dockerfile lives with the app code
   - Deployment docs are app-specific

3. **Separate Release Cycles**
   - Update ingestion-app without touching host or ai-canvas
   - Different versions in different environments
   - Canary deployments per app

4. **Monorepo to Polyrepo Migration Path**
   - Easy to split apps into separate repos later
   - Each app is already self-contained
   - Clear boundaries between apps

### 🔧 How It Works

**Build Context**: Always `./frontend` (workspace root)
- Ensures access to `package.json` and `node_modules`
- Angular CLI needs the workspace root
- Shared `libs/ui-kit` accessible to all apps

**Dockerfile Location**: In each app's directory
- Clear ownership and organization
- Easy to find app-specific build config
- CI/CD can watch specific paths

## CI/CD Examples

### GitHub Actions - Separate Workflows

**`.github/workflows/deploy-host.yml`**
```yaml
name: Deploy Host Shell

on:
  push:
    branches: [main]
    paths:
      - 'frontend/projects/host-shell/**'
      - 'frontend/libs/ui-kit/**'
      - 'frontend/package.json'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          docker build \
            -f frontend/projects/host-shell/Dockerfile \
            -t ${{ secrets.REGISTRY }}/democritus-host:${{ github.sha }} \
            -t ${{ secrets.REGISTRY }}/democritus-host:latest \
            ./frontend
      
      - name: Push to Registry
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login -u "${{ secrets.REGISTRY_USER }}" --password-stdin
          docker push ${{ secrets.REGISTRY }}/democritus-host:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/democritus-host:latest
      
      - name: Deploy to Production
        run: |
          # Your deployment commands
          kubectl set image deployment/democritus-host \
            host=${{ secrets.REGISTRY }}/democritus-host:${{ github.sha }}
```

**`.github/workflows/deploy-ingestion.yml`**
```yaml
name: Deploy Ingestion App

on:
  push:
    branches: [main]
    paths:
      - 'frontend/projects/ingestion-app/**'
      - 'frontend/libs/ui-kit/**'
      - 'frontend/package.json'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          docker build \
            -f frontend/projects/ingestion-app/Dockerfile \
            -t ${{ secrets.REGISTRY }}/democritus-ingestion:${{ github.sha }} \
            -t ${{ secrets.REGISTRY }}/democritus-ingestion:latest \
            ./frontend
      
      - name: Verify remoteEntry.js
        run: |
          docker run --rm \
            ${{ secrets.REGISTRY }}/democritus-ingestion:${{ github.sha }} \
            ls -la /usr/share/nginx/html/remoteEntry.js
      
      - name: Push to Registry
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login -u "${{ secrets.REGISTRY_USER }}" --password-stdin
          docker push ${{ secrets.REGISTRY }}/democritus-ingestion:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/democritus-ingestion:latest
      
      - name: Deploy to Production
        run: |
          # Your deployment commands
          kubectl set image deployment/democritus-ingestion \
            ingestion=${{ secrets.REGISTRY }}/democritus-ingestion:${{ github.sha }}
```

**`.github/workflows/deploy-ai-canvas.yml`**
```yaml
name: Deploy AI Canvas

on:
  push:
    branches: [main]
    paths:
      - 'frontend/projects/ai-canvas/**'
      - 'frontend/libs/ui-kit/**'
      - 'frontend/package.json'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Image
        run: |
          docker build \
            -f frontend/projects/ai-canvas/Dockerfile \
            -t ${{ secrets.REGISTRY }}/democritus-ai-canvas:${{ github.sha }} \
            -t ${{ secrets.REGISTRY }}/democritus-ai-canvas:latest \
            ./frontend
      
      - name: Push and Deploy
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login -u "${{ secrets.REGISTRY_USER }}" --password-stdin
          docker push ${{ secrets.REGISTRY }}/democritus-ai-canvas:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/democritus-ai-canvas:latest
          
          # Deploy
          kubectl set image deployment/democritus-ai-canvas \
            ai-canvas=${{ secrets.REGISTRY }}/democritus-ai-canvas:${{ github.sha }}
```

### GitLab CI - Monorepo Pipeline

**`.gitlab-ci.yml`**
```yaml
stages:
  - build
  - deploy

# Host Shell
build-host:
  stage: build
  only:
    changes:
      - frontend/projects/host-shell/**
      - frontend/libs/ui-kit/**
  script:
    - docker build -f frontend/projects/host-shell/Dockerfile -t $CI_REGISTRY_IMAGE/host:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/host:$CI_COMMIT_SHA

deploy-host:
  stage: deploy
  only:
    changes:
      - frontend/projects/host-shell/**
      - frontend/libs/ui-kit/**
  script:
    - kubectl set image deployment/democritus-host host=$CI_REGISTRY_IMAGE/host:$CI_COMMIT_SHA

# Ingestion App
build-ingestion:
  stage: build
  only:
    changes:
      - frontend/projects/ingestion-app/**
      - frontend/libs/ui-kit/**
  script:
    - docker build -f frontend/projects/ingestion-app/Dockerfile -t $CI_REGISTRY_IMAGE/ingestion:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/ingestion:$CI_COMMIT_SHA

deploy-ingestion:
  stage: deploy
  only:
    changes:
      - frontend/projects/ingestion-app/**
      - frontend/libs/ui-kit/**
  script:
    - kubectl set image deployment/democritus-ingestion ingestion=$CI_REGISTRY_IMAGE/ingestion:$CI_COMMIT_SHA

# AI Canvas
build-ai-canvas:
  stage: build
  only:
    changes:
      - frontend/projects/ai-canvas/**
      - frontend/libs/ui-kit/**
  script:
    - docker build -f frontend/projects/ai-canvas/Dockerfile -t $CI_REGISTRY_IMAGE/ai-canvas:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/ai-canvas:$CI_COMMIT_SHA

deploy-ai-canvas:
  stage: deploy
  only:
    changes:
      - frontend/projects/ai-canvas/**
      - frontend/libs/ui-kit/**
  script:
    - kubectl set image deployment/democritus-ai-canvas ai-canvas=$CI_REGISTRY_IMAGE/ai-canvas:$CI_COMMIT_SHA
```

## Deployment Scenarios

### Scenario 1: Update Only Ingestion App

```bash
# Developer makes changes to ingestion-app
git commit -m "Add new file upload feature"
git push

# CI/CD Pipeline:
# ✓ Builds ingestion-app only
# ✓ Deploys ingestion-app only
# ✗ Host not rebuilt (no changes)
# ✗ AI Canvas not rebuilt (no changes)

# Result: Fast deployment, no impact on other apps
```

### Scenario 2: Update Shared UI Kit

```bash
# Developer updates theme in ui-kit
git commit -m "Update primary color theme"
git push

# CI/CD Pipeline:
# ✓ Builds host-shell (uses ui-kit)
# ✓ Builds ingestion-app (uses ui-kit)
# ✓ Builds ai-canvas (uses ui-kit)
# ✓ All apps get new theme

# Result: Coordinated update across all apps
```

### Scenario 3: Canary Deployment

```bash
# Deploy new version of ingestion-app to 10% of traffic
kubectl set image deployment/democritus-ingestion \
  ingestion=registry/democritus-ingestion:new-version

kubectl scale deployment/democritus-ingestion-canary --replicas=1
kubectl scale deployment/democritus-ingestion --replicas=9

# Monitor metrics, rollback if needed
kubectl rollout undo deployment/democritus-ingestion-canary
```

## Kubernetes Deployment

### Separate Deployments

**`k8s/host-shell.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: democritus-host
spec:
  replicas: 3
  selector:
    matchLabels:
      app: democritus-host
  template:
    metadata:
      labels:
        app: democritus-host
    spec:
      containers:
      - name: host
        image: your-registry/democritus-host:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: democritus-host
spec:
  selector:
    app: democritus-host
  ports:
  - port: 80
    targetPort: 80
```

Similar files for `ingestion-app` and `ai-canvas`.

## Best Practices

### 1. Version Tagging
```bash
# Tag with git SHA for traceability
docker build -t app:$GIT_SHA -t app:latest .

# Semantic versioning for releases
docker build -t app:v1.2.3 -t app:latest .
```

### 2. Cache Optimization
```dockerfile
# Copy package files first for better layer caching
COPY package*.json ./
RUN npm ci
COPY . .
```

### 3. Health Checks
```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 4. Resource Limits
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Documentation per App

Each app has its own `DEPLOYMENT.md`:
- `frontend/projects/host-shell/DEPLOYMENT.md`
- `frontend/projects/ingestion-app/DEPLOYMENT.md`
- `frontend/projects/ai-canvas/DEPLOYMENT.md`

## Summary

✅ **Dockerfiles are now in app directories** for clear ownership
✅ **Build context remains frontend root** for workspace access
✅ **Independent deployment pipelines** possible
✅ **Easy to split into separate repos** if needed later
✅ **Clear documentation** per application

This architecture gives you the flexibility to deploy apps independently while maintaining the benefits of a monorepo during development.

