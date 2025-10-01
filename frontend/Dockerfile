FROM node:20-alpine as build
WORKDIR /app
RUN npm i -g @angular/cli@17.3.8
COPY package.json package-lock.json* ./
RUN npm ci || npm i
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/ingestion-ui/ /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


