FROM node:18.17.0-alpine


WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000

RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001
USER nodejs
