# Elimu Pro - Frontend (Vercel) Deployment Guide

## Quick Setup

1. Go to Vercel Dashboard → **Add New...** → **Project**
2. Import GitHub repo: `derosavage/elimu-pro-kenya-hub`
3. **Root Directory**: `frontend`
4. Framework Preset: **Create React App** (auto-detected)
5. Build Command: `npm run build` (auto-detected)
6. Output Directory: `build` (auto-detected)
7. Install Command: `npm install` (auto-detected)

## Environment Variables (in Vercel Dashboard)

| Key | Value |
|-----|-------|
| `REACT_APP_API_URL` | `https://your-backend.onrender.com/api/v1` |

## Post-Deploy Configuration

1. After first deploy, copy the Vercel URL (e.g., `https://elimu-pro-kenya-hub.vercel.app`)
2. Update Render backend `FRONTEND_URL` environment variable to this URL
3. Redeploy backend to pick up the new CORS origin

## SPA Routing

Handled by `vercel.json` rewrites (already configured):
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

## Build Optimization

- React Scripts 5 uses Webpack 5 with caching
- Static assets in `build/static/` get long-term caching via `vercel.json` headers
- Consider enabling Vercel Analytics for performance monitoring

## Troubleshooting

- **Build fails**: Check Node version (Vercel uses 18.x by default, compatible with react-scripts 5)
- **API calls fail**: Verify `REACT_APP_API_URL` is set correctly in Vercel dashboard
- **CORS errors**: Ensure backend `FRONTEND_URL` matches Vercel URL exactly (including https://)
- **Blank page**: Check browser console for JS errors; ensure `vercel.json` rewrites are working

## Custom Domain (Optional)

1. Vercel Dashboard → Project → Settings → Domains
2. Add custom domain (e.g., `app.elimupro.co.ke`)
3. Update DNS records as instructed
4. Update Render `FRONTEND_URL` to custom domain