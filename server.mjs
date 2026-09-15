// Dependency-free static server for the production image: serves the Vite
// build from dist/, exposes /api/health for the Docker HEALTHCHECK, and
// proxies every other /api/* request to the FastAPI backend container (Vite
// does the same thing in dev via its own proxy config).
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer, request as httpRequest } from "node:http";
import { extname, join, normalize, sep } from "node:path";

const PORT = Number(process.env.PORT ?? 3000);
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const ROOT = join(import.meta.dirname, "dist");

function proxyToBackend(req, res) {
  const target = new URL(req.url, BACKEND_URL);
  const { host: _ignoredHost, ...forwardHeaders } = req.headers;
  const proxyReq = httpRequest(
    {
      hostname: target.hostname,
      port: target.port,
      path: target.pathname + target.search,
      method: req.method,
      headers: forwardHeaders,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );
  proxyReq.on("error", () => {
    res.writeHead(502, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "backend unreachable" }));
  });
  req.pipe(proxyReq);
}

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

async function resolveFile(urlPath) {
  const candidate = normalize(join(ROOT, decodeURIComponent(urlPath)));
  // Reject path traversal such as /../../etc/passwd.
  if (candidate !== ROOT && !candidate.startsWith(ROOT + sep)) return null;
  try {
    const info = await stat(candidate);
    if (info.isFile()) return candidate;
  } catch {
    // Fall through to the SPA fallback below.
  }
  // Client-side routes have no file on disk, so they get the app shell.
  return join(ROOT, "index.html");
}

const server = createServer(async (req, res) => {
  const { pathname } = new URL(req.url ?? "/", "http://localhost");

  if (pathname === "/api/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }

  if (pathname.startsWith("/api/")) {
    proxyToBackend(req, res);
    return;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { Allow: "GET, HEAD" });
    res.end();
    return;
  }

  const file = await resolveFile(pathname).catch(() => null);
  if (!file) {
    res.writeHead(404);
    res.end();
    return;
  }

  res.writeHead(200, {
    "Content-Type": MIME_TYPES[extname(file)] ?? "application/octet-stream",
  });
  if (req.method === "HEAD") {
    res.end();
    return;
  }
  createReadStream(file)
    .on("error", () => res.destroy())
    .pipe(res);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Pairwise listening on http://0.0.0.0:${PORT}`);
});

// Exit promptly on `docker stop` instead of waiting for the SIGKILL timeout.
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
