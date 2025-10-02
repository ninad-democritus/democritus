# Quick Start Guide - Module Federation Setup

## ✅ What Was Done

Your Angular application has been successfully restructured into a Module Federation (MFE) architecture with:

1. **Three Applications:**
   - `host-shell` (port 4200) - Main container app
   - `ingestion-app` (port 4201) - Data ingestion remote
   - `ai-canvas` (port 4202) - AI workspace remote

2. **Shared UI Library:**
   - `ui-kit` - Centralized SCSS themes, mixins, and components

3. **Docker Configuration:**
   - Separate Dockerfiles for each app
   - Updated docker-compose.yml with three frontend services

## 🚀 Getting Started

### Development Mode

Run all three applications locally:

```bash
cd frontend

# Terminal 1 - Host Shell
npm run ng -- serve host-shell --port 4200

# Terminal 2 - Ingestion App
npm run ng -- serve ingestion-app --port 4201

# Terminal 3 - AI Canvas
npm run ng -- serve ai-canvas --port 4202
```

Then open http://localhost:4200 in your browser.

### Build for Production

```bash
cd frontend

# Build all applications
npm run ng -- build host-shell --configuration=production
npm run ng -- build ingestion-app --configuration=production
npm run ng -- build ai-canvas --configuration=production
```

### Docker Development

Build and run with Docker:

```bash
# Build all frontend services
docker compose build frontend-host frontend-ingestion frontend-ai-canvas

# Start all services
docker compose up frontend-host frontend-ingestion frontend-ai-canvas

# Or start the entire stack
docker compose up
```

Access the application at:
- Host Shell: http://localhost:4200
- Ingestion App: http://localhost:4201  
- AI Canvas: http://localhost:4202

## 📁 New Project Structure

```
frontend/
├── projects/
│   ├── host-shell/       # MFE Host (orchestrator)
│   ├── ingestion-app/    # Remote: Data Ingestion
│   └── ai-canvas/        # Remote: AI Workspace
├── libs/
│   └── ui-kit/           # Shared library
│       └── src/lib/styles/  # Centralized SCSS
├── Dockerfile.host
├── Dockerfile.ingestion
├── Dockerfile.ai-canvas
└── angular.json
```

## 🔧 Key Configuration Files

### Module Federation Configs

Each application has a `webpack.config.js`:

**Host (host-shell/webpack.config.js):**
```javascript
remotes: {
  "ingestionApp": "http://localhost:4201/remoteEntry.js",
  "aiCanvas": "http://localhost:4202/remoteEntry.js"
}
```

**Remotes (ingestion-app & ai-canvas):**
```javascript
exposes: {
  './Module': './projects/{app-name}/src/app/app.module.ts'
}
```

### Routing (host-shell/app-routing.module.ts)

```typescript
{
  path: 'ingestion',
  loadChildren: () =>
    loadRemoteModule({
      type: 'module',
      remoteEntry: 'http://localhost:4201/remoteEntry.js',
      exposedModule: './Module'
    }).then(m => m.AppModule)
}
```

## 🎨 Styling

All apps share centralized styles from `ui-kit`:

```scss
// In each app's styles.scss
@tailwind base;
@tailwind components;
@tailwind utilities;

@import '../../../libs/ui-kit/src/lib/styles/global-imports';
```

Change themes in `libs/ui-kit/src/lib/styles/global-imports.scss`.

## 🐳 Docker Services

**docker-compose.yml** now has three frontend services:

```yaml
frontend-host:
  build:
    context: ./frontend
    dockerfile: projects/host-shell/Dockerfile
  ports:
    - "4200:80"

frontend-ingestion:
  build:
    context: ./frontend
    dockerfile: projects/ingestion-app/Dockerfile
  ports:
    - "4201:80"

frontend-ai-canvas:
  build:
    context: ./frontend
    dockerfile: projects/ai-canvas/Dockerfile
  ports:
    - "4202:80"
```

Each Dockerfile is in its app's directory for independent deployment.

## ⚠️ Important Notes

1. **All apps must run simultaneously** for Module Federation to work
2. **Ports must match** the webpack.config.js remote entries
3. **CORS is configured** in remote app nginx configs
4. **remoteEntry.js is never cached** (check nginx.conf)

## 🔍 Troubleshooting

### "Cannot find module" errors
- Ensure all apps are running on their designated ports
- Check webpack.config.js remote URLs
- Verify CORS headers in remote nginx configs

### SCSS import errors
- Build the ui-kit library first: `npm run ng -- build ui-kit`
- Check import path: `@import '../../../libs/ui-kit/src/lib/styles/global-imports'`

### Docker build failures
- Clear caches: `docker compose build --no-cache`
- Remove old containers: `docker compose down -v`

## 📚 Next Steps

1. **Customize Navigation** - Edit `projects/host-shell/src/app/app.component.html`
2. **Add Features to AI Canvas** - Build out the ai-canvas application
3. **Add More Remotes** - Follow the guide in `MFE-ARCHITECTURE.md`
4. **Configure Production URLs** - Update webpack configs for production environment

## 📖 Documentation

- Full architecture guide: `MFE-ARCHITECTURE.md`
- Module Federation docs: https://webpack.js.org/concepts/module-federation/

## ✨ What's New

- ✅ Three independently deployable frontend apps
- ✅ Shared UI library with centralized theming
- ✅ Module Federation setup with dynamic loading
- ✅ Docker multi-service configuration
- ✅ NGINX configs with CORS for remotes
- ✅ Tailwind configured for all projects


