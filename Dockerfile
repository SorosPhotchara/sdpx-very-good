# Use the requested pinned Node release for reproducible dependency installation.
FROM node:24-alpine AS deps

# Keep all container work in a predictable application directory.
WORKDIR /app

# Copy dependency manifests first so source changes do not invalidate the install layer.
COPY package.json package-lock.json ./

# Install the exact dependency graph recorded in the npm lockfile.
RUN npm ci

# Reuse the installed dependency layer to compile the Vite application.
FROM deps AS build

# Copy application source only after dependencies have been cached.
COPY . .

# Type-check the application and produce optimized static assets.
RUN npm run build

# Isolate verification tooling and test execution from the production image.
FROM build AS test

# Install the repository's test runner at its pinned local version.
RUN npm install --global bun@1.2.17

# Run the existing Bun test suite before artifacts can enter the runtime stage.
RUN npm test

# Start the deployable image from a clean pinned Node base.
FROM node:24-alpine AS runtime

# Mark the process environment as production for runtime dependency selection.
ENV NODE_ENV=production

# Keep runtime files in a dedicated application directory.
WORKDIR /app

# Copy dependency manifests separately to preserve production-install caching.
COPY package.json package-lock.json ./

# Install production dependencies only and discard npm's download cache.
RUN npm ci --omit=dev && npm cache clean --force

# Copy tested build output without carrying compiler or test dependencies forward.
COPY --from=test /app/dist ./dist

# Copy the dependency-free static server that exposes the health endpoint.
COPY server.mjs ./

# Document the unprivileged HTTP port served by the application.
EXPOSE 3000

# Run the application as the non-root user supplied by the Node image.
USER node

# Verify that the application server and health route remain responsive.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget --quiet --tries=1 --spider http://127.0.0.1:3000/api/health || exit 1

# Launch the static application server as the container's foreground process.
CMD ["node", "server.mjs"]
