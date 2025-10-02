# Module Federation (MFE) Architecture

## Overview

This Angular workspace has been restructured to support Module Federation, allowing multiple independently deployable Angular applications to work together as micro-frontends.

## Project Structure

```
/frontend
├── angular.json              # Workspace configuration
├── package.json              # Dependencies
├── tailwind.config.js        # Shared Tailwind configuration
├── tsconfig.json             # Root TypeScript configuration
│
├── /projects                 # MFE Applications
│   ├── /host-shell          # Host application (port 4200)
│   │   ├── nginx.conf       # Production NGINX config
│   │   ├── webpack.config.js # Module Federation config
│   │   └── src/
│   │
│   ├── /ingestion-app       # Remote: Data ingestion (port 4201)
│   │   ├── nginx.conf
│   │   ├── webpack.config.js
│   │   └── src/
│   │
│   └── /ai-canvas           # Remote: AI workspace (port 4202)
│       ├── nginx.conf
│       ├── webpack.config.js
│       └── src/
│
├── /libs                     # Shared Libraries
│   └── /ui-kit              # Shared components, services, and SCSS
│       └── src/lib/styles/  # Centralized theme system
│           ├── abstractions/
│           ├── components/
│           ├── themes/
│           ├── main.scss
│           └── global-imports.scss
│
├── Dockerfile.host          # Host application Docker build
├── Dockerfile.ingestion     # Ingestion remote Docker build
└── Dockerfile.ai-canvas     # AI Canvas remote Docker build
```

## Applications

### Host Shell (Port 4200)
The main container application that loads and orchestrates the remote applications. It provides:
- Main routing and navigation
- Layout structure
- Module Federation host configuration

**Routes:**
- `/ingestion` → Loads ingestion-app remote
- `/ai-canvas` → Loads ai-canvas remote

### Ingestion App (Port 4201)
Remote application for data ingestion workflows. Exposes its AppModule via Module Federation.

### AI Canvas (Port 4202)
Remote application for AI-powered data analysis and visualization. Exposes its AppModule via Module Federation.

## Development

### Running Locally

Start all applications simultaneously:

```bash
# Terminal 1: Host Shell
cd frontend
npm run ng -- serve host-shell --port 4200

# Terminal 2: Ingestion App
npm run ng -- serve ingestion-app --port 4201

# Terminal 3: AI Canvas
npm run ng -- serve ai-canvas --port 4202
```

Access the host at http://localhost:4200

### Building for Production

Build individual applications:

```bash
npm run ng -- build host-shell --configuration=production
npm run ng -- build ingestion-app --configuration=production
npm run ng -- build ai-canvas --configuration=production
```

### Docker Development

Build and run with Docker Compose:

```bash
docker compose build frontend-host frontend-ingestion frontend-ai-canvas
docker compose up frontend-host frontend-ingestion frontend-ai-canvas
```

## Styling

All applications share a centralized SCSS system through the `ui-kit` library.

### Importing Shared Styles

Each application's `styles.scss`:

```scss
/* Tailwind directives */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Import shared UI Kit styles */
@import 'ui-kit/src/lib/styles/global-imports';
```

This provides:
- Theme variables (colors, spacing, shadows, etc.)
- Reusable mixins
- Global component classes
- Tailwind custom utilities

### Changing Themes

Edit `libs/ui-kit/src/lib/styles/global-imports.scss`:

```scss
// Change this line to switch themes
@forward 'themes/ocean-breeze';  // or 'themes/purple-haze'
```

## Module Federation Configuration

### Host Configuration (host-shell/webpack.config.js)

```javascript
remotes: {
  "ingestionApp": "http://localhost:4201/remoteEntry.js",
  "aiCanvas": "http://localhost:4202/remoteEntry.js",
}
```

### Remote Configuration (ingestion-app/webpack.config.js)

```javascript
name: 'ingestion-app',
exposes: {
  './Module': './projects/ingestion-app/src/app/app.module.ts',
}
```

### Loading Remotes in Host

The host application uses dynamic loading in its routing:

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

## Docker Deployment

### Services Configuration (docker-compose.yml)

Three separate frontend services:

```yaml
frontend-host:
  build:
    dockerfile: Dockerfile.host
  ports:
    - "4200:80"

frontend-ingestion:
  build:
    dockerfile: Dockerfile.ingestion
  ports:
    - "4201:80"

frontend-ai-canvas:
  build:
    dockerfile: Dockerfile.ai-canvas
  ports:
    - "4202:80"
```

### NGINX Configuration

Each application has its own NGINX config with:
- Proper routing for SPA
- CORS headers (for remotes)
- Cache control for `remoteEntry.js`
- Static asset caching

## Adding New Remote Applications

1. Generate a new application:
```bash
npm run ng -- generate application my-new-app --routing=true --style=scss --standalone=false --skip-tests
```

2. Move to projects directory:
```bash
Move-Item -Path "my-new-app" -Destination "projects/my-new-app"
```

3. Add Module Federation:
```bash
npm run ng -- generate @angular-architects/module-federation:ng-add --project my-new-app --port 4203 --type remote
```

4. Update angular.json paths to `projects/my-new-app`

5. Create Dockerfile.my-new-app

6. Create nginx.conf in the project

7. Add to docker-compose.yml

8. Update host-shell routing and webpack config

## Troubleshooting

### Module not found errors
- Ensure all paths in angular.json point to `projects/` or `libs/`
- Check TypeScript path mappings in tsconfig.json

### SCSS import errors
- Verify the import path: `@import 'ui-kit/src/lib/styles/global-imports'`
- Ensure ui-kit library is built: `npm run ng -- build ui-kit`

### Module Federation errors
- Check that all remotes are running on their designated ports
- Verify webpack.config.js exposes the correct module
- Ensure CORS is properly configured for remotes

### Docker build failures
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Rebuild Docker images: `docker compose build --no-cache`

## Best Practices

1. **Shared Dependencies**: Use `shareAll` in webpack.config.js to avoid duplicate dependencies
2. **Styling**: Always use the centralized ui-kit styles, avoid duplicating SCSS
3. **Versioning**: Keep Angular and dependency versions consistent across all apps
4. **Testing**: Test each remote independently before integration
5. **Deployment**: Deploy remotes before the host to ensure availability

## Resources

- [Module Federation Documentation](https://webpack.js.org/concepts/module-federation/)
- [@angular-architects/module-federation](https://www.npmjs.com/package/@angular-architects/module-federation)
- [Angular Micro Frontends Guide](https://www.angulararchitects.io/en/blog/micro-frontends-with-modern-angular/)


