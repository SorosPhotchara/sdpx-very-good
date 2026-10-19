import { spawn, spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const backend = resolve(frontend, '..', 'backend')
const windows = process.platform === 'win32'
const python = process.env.E2E_PYTHON || resolve(backend, '.venv', windows ? 'Scripts/python.exe' : 'bin/python')
const children = []

function start(command, args, cwd, env = process.env) {
  const child = spawn(command, args, { cwd, env, stdio: 'inherit' })
  children.push(child)
  return child
}

async function waitFor(url, child) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (child.exitCode != null) throw new Error(`Server exited before ${url} was ready.`)
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch { /* Server is still starting. */ }
    await new Promise((resolveWait) => setTimeout(resolveWait, 500))
  }
  throw new Error(`Timed out waiting for ${url}.`)
}

function stop(child) {
  if (!child.pid || child.exitCode != null) return
  if (windows) spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore' })
  else child.kill('SIGTERM')
}

let exitCode = 1
try {
  const api = start(python, ['run_e2e.py'], backend)
  const vite = resolve(frontend, 'node_modules', 'vite', 'bin', 'vite.js')
  const web = start(process.execPath, [vite, '--host', '127.0.0.1', '--port', '5173', '--strictPort'], frontend,
    { ...process.env, VITE_AUTH_MODE: 'mock', VITE_GOOGLE_CLIENT_ID: 'browser-test.apps.googleusercontent.com', VITE_API_BASE_URL: 'http://127.0.0.1:8000', VITE_DEMO_INSTRUCTOR_EMAIL: 'teacher@example.edu', VITE_DEMO_STUDENT_EMAIL: 'student1@example.edu' })
  await Promise.all([waitFor('http://127.0.0.1:8000/health', api), waitFor('http://127.0.0.1:5173', web)])

  const cli = resolve(frontend, 'node_modules', '@playwright', 'test', 'cli.js')
  const result = spawnSync(process.execPath, [cli, 'test', ...process.argv.slice(2)], { cwd: frontend, stdio: 'inherit' })
  exitCode = result.status ?? 1
} catch (error) {
  console.error(error instanceof Error ? error.message : error)
} finally {
  for (const child of children.reverse()) stop(child)
}

process.exit(exitCode)
