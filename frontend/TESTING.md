# Frontend testing guide

## Prerequisites

- Node.js 24 (matches CI)
- `npm ci` from `frontend/`

## Commands

| Command | Purpose |
|---------|---------|
| `npm run lint` | ESLint (TypeScript + React) |
| `npm test` | Unit/component tests (Vitest, `src/**/*.test.{ts,tsx}`) |
| `npm run test:unit` | Alias for `npm test` |
| `npm run test:watch` | Vitest watch mode |
| `npm run test:integration` | Integration specs (`src/integration/**/*.integration.spec.tsx`) |
| `npm run test:coverage` | Unit tests with coverage |
| `npm run test:e2e` | Playwright browser tests (`tests/e2e/`, requires dev server) |
| `npm run build` | `tsc` + production Vite build |

## Directory layout

- **Unit / component:** co-located `*.test.ts(x)` under `src/`
- **Integration:** `src/integration/*.integration.spec.tsx` + `src/integration/fixtures/`
- **E2E:** `tests/e2e/*.spec.ts` (Playwright, real browser; not run as integration)

## Integration vs unit

Integration tests render multiple real components with **React Query**, **React Router**, and **Zustand**, and mock HTTP at the **API module boundary** (`api`, `scansApi`, etc.). They validate loading, success, and navigation wiring—not isolated pure functions.

Unit tests mock hooks/stores more aggressively and focus on a single component or module.

## API mocking

Integration tests use `vi.mock('../api/...')` or `vi.mock('../lib/api')` with fixtures in `src/integration/fixtures/` shaped to match `src/api/endpoints/*` and shared `src/types`.

No production credentials or `.env` files are required.

## CI

`.github/workflows/CI-Frontend.yml` runs `npm ci`, `npm run lint`, `npm test`, `npm run test:integration`, and `npm run build`.
