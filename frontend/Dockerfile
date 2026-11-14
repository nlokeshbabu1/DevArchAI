# Frontend Dockerfile

#-----------Base-image-------------------------------
FROM node:24-alpine AS base

WORKDIR /app

#----------Install dependencies -----------------------
FROM base AS deps

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci 

#---------Build stage-------------------------------
FROM base AS builder

#copy the file from base image
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build application
RUN npm run build

#########################################
## production stage   ###################
########################################
# Production stage
FROM nginx:alpine

#create the use appuser
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

#create the templates directory for nginx
RUN mkdir -p /etc/nginx/templates

# #create the directory for nginx pid file
# RUN mkdir -p /run/nginx

# Fix permissions
RUN chown -R appuser:appgroup /usr/share/nginx/html \
    /var/cache/nginx \
    /var/log/nginx \
    /etc/nginx/conf.d \
    /etc/nginx/templates \
    /run

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
#COPY nginx.conf /etc/nginx/conf.d/default.conf
#COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy template instead of final config
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

#user appuser
USER appuser

#Expose port 80
EXPOSE 80

# Generate config at runtime using env var
CMD ["/bin/sh", "-c", "envsubst '$BACKEND_HOST' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
