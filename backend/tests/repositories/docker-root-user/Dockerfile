FROM node:18.17.0-alpine


WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -q --spider http://localhost:3000/health || exit 1
