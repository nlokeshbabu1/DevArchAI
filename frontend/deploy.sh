#!/bin/bash
# Deploy frontend to nginx

echo "🚀 Deploying DevArchAI Frontend to nginx..."

# Copy build artifacts
echo "📦 Copying build files..."
sudo cp -r dist/* /usr/share/nginx/html/

# Copy nginx config
echo "📝 Copying nginx configuration..."
sudo cp nginx.conf /etc/nginx/nginx.conf

# Test nginx configuration
echo "✅ Testing nginx configuration..."
sudo nginx -t

# Reload nginx
echo "🔄 Reloading nginx..."
sudo nginx -s reload

echo "✨ Deployment complete!"
echo "🌐 Frontend: http://localhost"
echo "🔧 Backend:  http://localhost:8000"
