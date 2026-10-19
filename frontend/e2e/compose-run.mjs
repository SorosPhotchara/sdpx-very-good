import { spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const compose = ['compose', '-f', resolve(root, 'compose.test.yml')]
const service = process.argv[2] || 'e2e'

const result = spawnSync('docker', [
  ...compose, 'up', '--build', '--abort-on-container-exit', '--exit-code-from', service, service,
], { cwd: root, stdio: 'inherit' })

spawnSync('docker', [...compose, 'down', '--volumes'], { cwd: root, stdio: 'inherit' })
process.exit(result.status ?? 1)
