FROM node:22.23.2-alpine AS build

WORKDIR /app

COPY frontend/uni-app/package.json frontend/uni-app/package-lock.json ./
RUN npm ci --ignore-scripts

COPY frontend/uni-app/ ./

# The H5 client and API share an origin behind the host Nginx proxy. Keeping
# this relative makes the published image portable between IPs and domains.
ARG VITE_API_BASE_URL=/django/api/v1
ARG VITE_CHAT_ENABLE_WS=0
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_CHAT_ENABLE_WS=${VITE_CHAT_ENABLE_WS}
RUN npm run build:h5

FROM nginx:1.27-alpine

COPY frontend/uni-app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/build/h5 /usr/share/nginx/html

EXPOSE 80
