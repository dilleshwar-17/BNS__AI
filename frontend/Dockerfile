FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine-slim

RUN adduser -D -g '' -h /usr/share/nginx/html -s /sbin/nologin bnsai

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN chown -R bnsai:bnsai /usr/share/nginx/html /etc/nginx/conf.d && \
    chmod -R 755 /usr/share/nginx/html

USER bnsai

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
