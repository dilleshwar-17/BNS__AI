FROM nginx:alpine-slim

RUN adduser -D -g '' -h /etc/nginx -s /sbin/nologin bnsai

COPY default.conf /etc/nginx/conf.d/default.conf

RUN chown -R bnsai:bnsai /etc/nginx /var/cache/nginx /var/run && \
    chmod -R 755 /etc/nginx

USER bnsai

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
