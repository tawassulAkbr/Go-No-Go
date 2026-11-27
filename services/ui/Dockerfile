FROM node:20.19.0-alpine AS build
WORKDIR /app
COPY services/ui/package*.json ./
RUN npm ci
COPY services/ui/ ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24
COPY services/ui/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY --chmod=755 services/ui/docker-entrypoint.sh /docker-entrypoint.d/40-config.sh
USER 101:101
EXPOSE 8080
