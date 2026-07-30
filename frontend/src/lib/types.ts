// ScenarioLab TypeScript Types
// This file re-exports all types from domain-specific modules.
// Import from here for backwards compatibility, or import directly
// from the domain modules under ./types/ for better tree-shaking.
//
// OpenAPI-generated API shapes live in ./generated-types.ts
// (regenerate via `./scripts/generate-types.sh`). Prefer hand-written
// domain types below for UI models; use generated types for raw API
// contracts when migrating clients:
//   import type { components, paths } from './generated-types';

export * from './types/index';

/** Namespace re-export for OpenAPI-generated schemas (additive; optional). */
export type * as OpenAPI from './generated-types';
