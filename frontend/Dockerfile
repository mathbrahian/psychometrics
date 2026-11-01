FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY --from=build /app/dist ./dist
COPY docker-entrypoint.sh ./

ENV PORT=3000 \
    BACKEND_URL=http://localhost:9090

EXPOSE 3000

CMD ["sh", "docker-entrypoint.sh"]
