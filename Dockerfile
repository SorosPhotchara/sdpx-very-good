# ---------- deps: install every dependency once, cached by lockfile ----------
# Pin an exact major + distro tag (never `latest`) so every machine builds the same image; alpine keeps it small.
FROM node:24-alpine AS deps

# Keep all container work in a predictable application directory.
WORKDIR /app

# Copy only the dependency manifests first so a source edit does not invalidate the install layer.
COPY package.json package-lock.json ./

# Install exactly what the lockfile records (fails if package.json and the lockfile disagree).
RUN npm ci

# ---------- build: compile the app with devDependencies available ----------
# Reuse the cached dependency layer; compose.yaml also runs the dev server from this stage.
FROM deps AS build

# Copy application source only after dependencies have been cached (see .dockerignore for what is excluded).
COPY . .

# Type-check, then produce optimized static assets in dist/.
RUN npm run build

# ---------- test: run the unit suite; the container's exit code is the test result ----------
# Start from the built stage so tests see the same source and dependencies that were compiled.
FROM build AS test

# Install the Bun test runner at the same version the team uses locally.
RUN npm install --global bun@1.4.2

# Run tests when the container starts (not at build time) so `--exit-code-from unit` reports pass/fail.
CMD ["npm", "test"]

# ---------- e2e: browsers need glibc and system libraries that alpine lacks ----------
# Microsoft's image ships Chromium/Firefox/WebKit matching this exact @playwright/test version.
FROM mcr.microsoft.com/playwright:v1.63.0-noble AS e2e

# Keep all container work in a predictable application directory.
WORKDIR /app

# Copy dependency manifests first for layer caching, same as the deps stage.
COPY package.json package-lock.json ./

# Install the pinned @playwright/test from the lockfile.
RUN npm ci

# Copy the Playwright config and specs.
COPY . .

# Run the E2E suite against BASE_URL; the container's exit code is the test result.
CMD ["npx", "playwright", "test"]

# ---------- runtime: the image that ships ----------
# Start from a clean pinned base so no compiler, test runner, or source code is carried forward.
FROM node:24-alpine AS runtime

# Tell Node libraries to use their production code paths.
ENV NODE_ENV=production

# Keep runtime files in a dedicated application directory.
WORKDIR /app

# Copy dependency manifests separately to preserve production-install caching.
COPY package.json package-lock.json ./

# Install production dependencies only (no TypeScript, Vite, Playwright) and drop npm's download cache.
RUN npm ci --omit=dev && npm cache clean --force

# Copy only the compiled static assets from the build stage.
COPY --from=build /app/dist ./dist

# Copy the dependency-free static server that also answers /api/health.
COPY server.mjs ./

# Document the port the server listens on; it does not publish it (that is `-p` / `ports:`).
EXPOSE 3000

# Drop root: the node image ships an unprivileged `node` user, limiting damage if the process is compromised.
USER node

# Probe the health endpoint so Docker marks the container unhealthy when it stops serving, not only when it exits.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:3000/api/health || exit 1

# Run the server as PID 1 in exec form so it receives SIGTERM from `docker stop`.
CMD ["node", "server.mjs"]
