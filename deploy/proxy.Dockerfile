FROM node:22-alpine AS publisher
WORKDIR /build
COPY publisher/package.json publisher/package-lock.json ./
COPY publisher/apps/publisher-ui/package.json apps/publisher-ui/package.json
RUN npm ci
COPY publisher/ .
ARG VITE_CENTRAL_CATALOG_URL
ARG VITE_DEFAULT_IDP
ENV VITE_CENTRAL_CATALOG_URL=$VITE_CENTRAL_CATALOG_URL
ENV VITE_DEFAULT_IDP=$VITE_DEFAULT_IDP
RUN npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=publisher /build/apps/publisher-ui/dist /srv/publisher
