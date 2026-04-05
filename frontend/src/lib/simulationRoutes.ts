/**
 * Top-level segments under /simulations/ that are not simulation UUIDs.
 * These must not be treated as simulation detail routes for layout or sidebar.
 */
const RESERVED_SIMULATION_PATH_SEGMENTS = new Set(["new", "compare"]);

/**
 * Returns the simulation id from /simulations/{id}/... or null if not a simulation route
 * (list, wizard, compare, etc.).
 */
export function getSimulationIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/simulations\/([^/]+)/);
  if (!match) return null;
  if (RESERVED_SIMULATION_PATH_SEGMENTS.has(match[1])) return null;
  return match[1];
}

/**
 * True when pathname should use the full-bleed simulation detail layout (no main padding).
 */
export function isSimulationDetailLayoutPath(pathname: string): boolean {
  const match = pathname.match(/^\/simulations\/([^/]+)(?:\/|$)/);
  if (!match) return false;
  return !RESERVED_SIMULATION_PATH_SEGMENTS.has(match[1]);
}
