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

ENV PORT=8080 \
    EXTRACTOR_VERTEX_URL=http://localhost:8080

CMD ["sh", "docker-entrypoint.sh"]
