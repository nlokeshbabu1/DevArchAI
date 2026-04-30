# Frontend Development Mandates

## Core Technologies
- **Framework:** React 18+ with TypeScript and Vite.
- **Styling:** Tailwind CSS. Use `tailwind-merge` and `clsx` for dynamic classes.
- **Components:** Radix UI primitives for accessible UI components.
- **Icons:** Lucide React.

## State & Data
- **Data Fetching:** TanStack Query (React Query) for all server-state management.
- **Global State:** Zustand for lightweight client-side state.
- **Forms:** Use uncontrolled components or `react-hook-form` if complex validation is needed.

## Standards
- **TypeScript:** Strict mode enabled. Define interfaces/types for all API responses and component props.
- **File Structure:** 
  - `components/`: Reusable UI components.
  - `hooks/`: Custom hooks.
  - `services/` or `api/`: API client and endpoints.
  - `types/`: Shared TypeScript definitions.
- **Testing:** Use `vitest` for unit and component testing.
- **Linting:** `eslint` with TypeScript and React plugins.

## Workflow
- Use `npm run lint:fix` to ensure code quality.
- Ensure all components are responsive and follow the design language (dark/light mode support if applicable).
