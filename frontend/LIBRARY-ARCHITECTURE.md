# Shared Library Architecture

## Overview

This document describes the proper setup for shared libraries (`ui-kit` and `shared-ui`) in the Democritus frontend monorepo.

## Directory Structure

```
frontend/
├── libs/                          # Shared Libraries (Source)
│   ├── ui-kit/                   # SCSS styles, themes, variables
│   │   ├── src/lib/styles/
│   │   ├── ng-package.json       # Builds to: ../../dist/ui-kit
│   │   └── tsconfig.lib.json     # Extends: ../../tsconfig.json
│   │
│   └── shared-ui/                # Angular components (header, sidebar, etc.)
│       ├── src/lib/components/
│       ├── ng-package.json       # Builds to: ../../dist/shared-ui
│       └── tsconfig.lib.json     # Extends: ../../tsconfig.json
│
├── dist/                          # Build Outputs (Compiled Libraries)
│   ├── ui-kit/                   # Compiled SCSS library
│   └── shared-ui/                # Compiled Angular components
│
├── projects/                      # MFE Applications
│   ├── tsconfig.json             # MUST include paths to dist/ libraries
│   ├── host-shell/               # Host MFE
│   ├── ingestion-app/            # Ingestion MFE
│   └── ai-canvas/                # Canvas MFE
│
└── tsconfig.json                  # Root config with path mappings
```

## Key Configuration Files

### 1. Root `tsconfig.json`
Path mappings for IDE and root-level tooling:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "shared-ui": ["./dist/shared-ui"],
      "ui-kit": ["./dist/ui-kit"]
    }
  }
}
```

### 2. `projects/tsconfig.json`
Path mappings for all MFE applications:
```json
{
  "compilerOptions": {
    "baseUrl": "..",
    "paths": {
      "shared-ui": ["dist/shared-ui"],    // Relative to baseUrl
      "ui-kit": ["dist/ui-kit"]
    }
  }
}
```

### 3. Library `ng-package.json`
Both libraries must output to root `dist/`:

**libs/ui-kit/ng-package.json:**
```json
{
  "dest": "../../dist/ui-kit"
}
```

**libs/shared-ui/ng-package.json:**
```json
{
  "dest": "../../dist/shared-ui",
  "lib": {
    "styleIncludePaths": ["../"]  // For importing ui-kit styles
  }
}
```

## Build Order

**CRITICAL:** Libraries must be built **before** applications that depend on them.

### Development Build Order:
```bash
# 1. Build libraries
npm run ng -- build ui-kit
npm run ng -- build shared-ui

# 2. Build applications (any order)
npm run ng -- build host-shell
npm run ng -- build ingestion-app
npm run ng -- build ai-canvas
```

### Docker Build Order:
Each Dockerfile MUST build libraries first:
```dockerfile
# Build shared libraries first (required dependencies)
RUN npm run ng -- build ui-kit
RUN npm run ng -- build shared-ui

# Then build the application
RUN npm run ng -- build <app-name>
```

## Import Usage

### In Application Code:
```typescript
// Import components from shared-ui
import { AppHeaderComponent, AppSidebarComponent } from 'shared-ui';

// Import from ui-kit (if needed for services)
import { SomeService } from 'ui-kit';
```

### In Application SCSS:
```scss
// Import ui-kit styles
@import 'ui-kit/src/lib/styles/global-imports';
```

## Troubleshooting

### Error: "Cannot find module 'shared-ui'"

**Cause:** Libraries not built, or path mappings missing.

**Fix:**
1. Ensure `dist/shared-ui` exists: `npm run ng -- build shared-ui`
2. Check `projects/tsconfig.json` has correct path mappings
3. Clean cache: `rm -rf .angular dist` and rebuild

### Error: "Can't find stylesheet to import"

**Cause:** `styleIncludePaths` not configured in `ng-package.json`

**Fix:**
Add to `libs/shared-ui/ng-package.json`:
```json
{
  "lib": {
    "styleIncludePaths": ["../"]
  }
}
```

### Docker Build Fails

**Cause:** Libraries not built before application

**Fix:**
Add library builds to Dockerfile before app build:
```dockerfile
RUN npm run ng -- build ui-kit
RUN npm run ng -- build shared-ui
RUN npm run ng -- build <app-name>
```

## Best Practices

1. ✅ **Always build libraries before applications**
2. ✅ **Keep libraries in `libs/`** (not `projects/`)
3. ✅ **Output all builds to `dist/`** (not `libs/dist/`)
4. ✅ **Use relative paths in tsconfig** based on `baseUrl`
5. ✅ **Include library builds in Docker** before app builds
6. ✅ **Clean rebuild** when moving/renaming libraries

## Verification

To verify the setup is correct:

```bash
# 1. Check build outputs exist
ls dist/ui-kit/package.json
ls dist/shared-ui/package.json

# 2. Test clean build
rm -rf .angular dist
npm run ng -- build ui-kit
npm run ng -- build shared-ui
npm run ng -- build host-shell

# 3. Verify no errors
```

All three builds should complete successfully without "Cannot find module" errors.

