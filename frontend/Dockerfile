FROM node:22-slim AS builder

WORKDIR /build

# Install pnpm (project uses pnpm exclusively).
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install dependencies from lockfile.
COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

# Vite inlines env vars at build time — pass them as build args.
ARG VITE_API_BASE_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

COPY . .
RUN pnpm build


# ---------------------------------------------------------------------------
FROM nginx:alpine AS runtime

# Remove default nginx config.
RUN rm /etc/nginx/conf.d/default.conf

# SPA-aware nginx config.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static files.
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80
