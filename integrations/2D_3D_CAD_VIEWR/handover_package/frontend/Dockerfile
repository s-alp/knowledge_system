FROM node:20-alpine AS base

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM base AS build

COPY frontend/ /app/frontend/

ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_LOCAL_FILE_ENABLED=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_LOCAL_FILE_ENABLED=$VITE_LOCAL_FILE_ENABLED

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
