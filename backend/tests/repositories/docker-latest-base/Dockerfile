FROM node:latest


WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000

RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001
USER nodejs

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -q --spider http://localhost:3000/health || exit 1
