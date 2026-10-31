# Giai đoạn 1: build ra tệp tĩnh (HTML/CSS/JS) bằng Vite
FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Giai đoạn 2: phục vụ tệp tĩnh bằng Nginx + proxy /api, /health sang service `api`
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
