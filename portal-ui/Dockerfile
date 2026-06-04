# Dev image. Build context is the monorepo root (npm workspaces: admin-ui + portal-ui).
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY admin-ui/package.json ./admin-ui/
COPY portal-ui/package.json ./portal-ui/
COPY packages/i18n/package.json ./packages/i18n/

RUN npm install --include=dev

COPY packages/i18n ./packages/i18n
COPY portal-ui ./portal-ui

WORKDIR /app/portal-ui

EXPOSE 3001
CMD ["npm", "run", "dev"]
