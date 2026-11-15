FROM node:22-alpine

WORKDIR /app

RUN npm install -g pnpm@10

# Install dependencies first so they are cached until the lockfile changes
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173

# Vite dev server (hot reload); /api requests are proxied to the backend service
CMD ["pnpm", "dev"]
