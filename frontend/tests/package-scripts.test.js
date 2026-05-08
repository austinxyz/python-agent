import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const pkgPath = join(__dirname, '..', 'package.json')

function pkg() {
  return JSON.parse(readFileSync(pkgPath, 'utf-8'))
}

describe('package.json dev/prod isolation scripts', () => {
  it('defines dev:up, dev:down, dev:reset, e2e:dev', () => {
    const scripts = pkg().scripts
    expect(scripts['dev:up']).toBeDefined()
    expect(scripts['dev:down']).toBeDefined()
    expect(scripts['dev:reset']).toBeDefined()
    expect(scripts['e2e:dev']).toBeDefined()
  })

  it('all four use cross-env COMPOSE_PROJECT_NAME=python-agent-dev', () => {
    const scripts = pkg().scripts
    for (const name of ['dev:up', 'dev:down', 'dev:reset', 'e2e:dev']) {
      expect(
        scripts[name],
        `${name} must set COMPOSE_PROJECT_NAME via cross-env so it works on Windows`,
      ).toMatch(/cross-env\s+COMPOSE_PROJECT_NAME=python-agent-dev/)
    }
  })

  it('dev:reset uses down -v to remove volumes', () => {
    const s = pkg().scripts['dev:reset']
    expect(s).toMatch(/down\s+-v/)
  })

  it('dev:up runs docker compose with up -d', () => {
    const s = pkg().scripts['dev:up']
    expect(s).toMatch(/docker\s+compose/)
    expect(s).toMatch(/\bup\b/)
    expect(s).toMatch(/-d\b/)
  })

  it('e2e:dev gates Playwright on the dev stack being up', () => {
    const s = pkg().scripts['e2e:dev']
    // Either chains dev:up before playwright, or invokes the dev:up script first.
    expect(s).toMatch(/dev:up|docker\s+compose\s+up/)
    expect(s).toMatch(/playwright|e2e/)
  })

  it('cross-env is a devDependency', () => {
    expect(pkg().devDependencies['cross-env']).toBeDefined()
  })
})
