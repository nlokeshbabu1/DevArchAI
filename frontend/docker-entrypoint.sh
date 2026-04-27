#!/bin/sh
set -e

# Default backend URL if not set
export BACKEND_URL="${BACKEND_URL:-http://backend:8000}"

# Process nginx template with environment variables
envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

echo "✅ Backend URL configured: ${BACKEND_URL}"

# Execute the CMD
exec "$@"
