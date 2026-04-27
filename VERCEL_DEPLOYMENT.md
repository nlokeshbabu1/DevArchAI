# Vercel Deployment Guide for DevArchAI

## Issue
Vercel was trying to build from the root directory, but the frontend code is in the `frontend/` subdirectory.

## Solution
Created `vercel.json` in the root directory with proper configuration:

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "devCommand": "cd frontend && npm run dev",
  "installCommand": "cd frontend && npm install"
}
```

## What This Does
- **buildCommand**: Changes to frontend directory, installs dependencies, and runs build
- **outputDirectory**: Tells Vercel to serve files from `frontend/dist`
- **installCommand**: Ensures dependencies are installed in the frontend directory

## Deployment Steps

### Option 1: Vercel Dashboard
1. Connect your GitHub repository to Vercel
2. Vercel will automatically detect the `vercel.json` configuration
3. Deploy!

### Option 2: Vercel CLI
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

## Build Output
After successful deployment, Vercel will show:
```
✓ Build completed successfully
✓ Output directory: frontend/dist
✓ Deployment ready
```

## Troubleshooting

### Build Fails with "npm run build" exited with 1
Check the build logs for specific TypeScript errors. Common issues:
- Missing dependencies
- TypeScript type errors
- Missing files

### Solution
1. Run `npm run build` locally first to catch errors
2. Fix any TypeScript errors
3. Push to GitHub
4. Vercel will automatically redeploy

### Frontend Not Loading After Deploy
Check that:
1. `outputDirectory` is set to `frontend/dist`
2. Build completes successfully
3. No 404 errors in browser console

## Environment Variables
If your app needs environment variables:
1. Go to Vercel Dashboard → Project → Settings → Environment Variables
2. Add variables:
   - `VITE_API_URL` - Backend API URL
   - `VITE_GITHUB_CLIENT_ID` - GitHub OAuth client ID (optional)

## Automatic Deployments
Vercel automatically deploys when you push to:
- `main` branch → Production deployment
- Other branches → Preview deployment

## Custom Domain
To add a custom domain:
1. Go to Vercel Dashboard → Project → Settings → Domains
2. Add your domain
3. Update DNS records as instructed
