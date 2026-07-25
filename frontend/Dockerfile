# Stage 1: Build stage
FROM node:24-alpine AS build

WORKDIR /app

# Enable corepack for pnpm management
RUN corepack enable

# Install dependencies using frozen lockfile
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy frontend source code and build production assets
COPY . .
RUN pnpm run build

# Stage 2: Production serving stage
FROM nginx:alpine AS final

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
