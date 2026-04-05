"use client";

import { usePathname } from "next/navigation";
import { ChevronRight, Bell, User, Menu } from "lucide-react";
import { getSimulationIdFromPath } from "@/lib/simulationRoutes";

const breadcrumbMap: Record<string, string> = {
  "/": "Dashboard",
  "/upload": "Upload",
  "/simulations": "Simulations",
  "/simulations/new": "New Simulation",
  "/simulations/compare": "Compare",
  "/playbooks": "Playbooks",
  "/reports": "Reports",
  "/api-keys": "API Keys",
  "/fine-tuning": "Fine-Tuning",
  "/analytics/cross-simulation": "Cross-Simulation Analytics",
  "/personas/designer": "Persona Designer",
  "/personas/axioms": "Persona Axioms",
};

// Sub-page labels for simulation routes: /simulations/{id}/{sub}
const simulationSubPageLabels: Record<string, string> = {
  "": "Overview",
  "chat": "Chat",
  "report": "Report",
  "network": "Network Graph",
  "timeline": "Timeline",
  "sensitivity": "Sensitivity Analysis",
  "voice": "Voice Chat",
  "zopa": "ZOPA Analysis",
  "rehearsal": "Rehearsal",
  "audit-trail": "Audit Trail",
  "attribution": "Attribution",
  "fairness": "Fairness Audit",
  "market-intel": "Market Intelligence",
};

/** Pathname only: strip query string and trailing slash so map lookups stay exact. */
function normalizePathname(pathname: string): string {
  const path = pathname.split("?")[0];
  if (path === "/" || path === "") return "/";
  return path.replace(/\/+$/, "") || "/";
}

function getPageTitle(pathname: string): string {
  const path = normalizePathname(pathname);

  // Check static map first (exact match)
  if (breadcrumbMap[path]) return breadcrumbMap[path];

  // Simulation detail routes only (excludes /simulations/new, /simulations/compare, etc.)
  const simId = getSimulationIdFromPath(path);
  if (simId) {
    const subMatch = path.match(/^\/simulations\/[^/]+\/(.+)$/);
    const sub = subMatch ? subMatch[1] : "";
    return simulationSubPageLabels[sub] ?? "Simulation";
  }

  return "Page";
}

interface HeaderProps {
  onMenuClick?: () => void;
  /** Unread count for assistive tech; optional until notifications are wired. */
  unreadNotificationCount?: number;
}

export function Header({
  onMenuClick,
  unreadNotificationCount = 0,
}: HeaderProps) {
  const pathname = usePathname();
  const pageTitle = getPageTitle(pathname);

  return (
    <header className="sticky top-0 z-40 h-16 bg-background-secondary border-b border-border flex items-center justify-between px-4 md:px-6">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm max-w-[60%] sm:max-w-none">
        {/* Hamburger menu button for mobile */}
        <button
          onClick={onMenuClick}
          className="flex-shrink-0 p-2 -ml-2 rounded-lg text-foreground-muted hover:text-foreground hover:bg-background-tertiary md:hidden"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <span className="text-foreground-muted hidden sm:inline flex-shrink-0">MiroFish</span>
        <ChevronRight className="w-4 h-4 text-foreground-subtle hidden sm:block flex-shrink-0" />
        <span aria-current="page" className="text-foreground font-medium truncate" title={pageTitle}>
          {pageTitle}
        </span>
      </nav>

      {/* Right side actions */}
      <div className="flex items-center gap-4 flex-shrink-0">
        {/* Notifications */}
        <button
          type="button"
          aria-label={
            unreadNotificationCount > 0
              ? `View notifications, ${unreadNotificationCount} unread`
              : "View notifications"
          }
          className="relative p-2 text-foreground-muted hover:text-foreground transition-colors rounded-lg hover:bg-background-tertiary"
        >
          <Bell className="w-5 h-5" aria-hidden />
          {unreadNotificationCount > 0 && (
            <span
              className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent rounded-full"
              aria-hidden
            />
          )}
        </button>

        {/* User menu */}
        <button 
          aria-label="User profile"
          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-background-tertiary transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-background-tertiary border border-border flex items-center justify-center">
            <User className="w-4 h-4 text-foreground-muted" />
          </div>
          <span className="text-sm text-foreground-muted hidden sm:block">
            User
          </span>
        </button>
      </div>
    </header>
  );
}
