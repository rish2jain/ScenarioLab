"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Play,
  BookOpen,
  FileText,
  Fish,
  Network,
  BarChart3,
  MessageSquare,
  Clock,
  X,
  History,
  PieChart,
  Scale,
  Brain,
  Key,
  TrendingUp,
  Mic,
  Target,
  Users,
  Settings,
  ChevronDown,
  UserCircle2,
} from "lucide-react";
import { clsx } from "clsx";
import { getSimulationIdFromPath } from "@/lib/simulationRoutes";
import { useSimulationStore } from "@/lib/store";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Upload", href: "/upload", icon: Upload },
  { name: "Simulations", href: "/simulations", icon: Play },
  { name: "Compare", href: "/simulations/compare", icon: Scale },
  { name: "Playbooks", href: "/playbooks", icon: BookOpen },
  { name: "Reports", href: "/reports", icon: FileText },
];

const analyticsNav = [
  { name: "Cross-Simulation", href: "/analytics/cross-simulation", icon: Brain },
];

const toolsNav = [
  { name: "Fine-Tuning", href: "/fine-tuning", icon: Settings },
  { name: "Personas", href: "/personas/designer", icon: UserCircle2 },
  ...(process.env.NODE_ENV === "development" ||
  process.env.NEXT_PUBLIC_ENABLE_API_KEYS_UI === "true"
    ? [{ name: "API Keys", href: "/api-keys", icon: Key }]
    : []),
];

const SIDEBAR_COLLAPSE_KEY = "scenariolab-sidebar-sim-sections";

type SimSectionKey = "visualizations" | "advanced";

function loadCollapsedSections(): Record<SimSectionKey, boolean> {
  if (typeof window === "undefined") {
    return { visualizations: false, advanced: true };
  }
  try {
    const raw = localStorage.getItem(SIDEBAR_COLLAPSE_KEY);
    if (!raw) return { visualizations: false, advanced: true };
    const parsed = JSON.parse(raw) as Partial<Record<SimSectionKey, boolean>>;
    return {
      visualizations: Boolean(parsed.visualizations),
      advanced: parsed.advanced !== false,
    };
  } catch {
    return { visualizations: false, advanced: true };
  }
}

/** Pick the longest matching href so e.g. /simulations/compare wins over /simulations. */
function isNavItemActive(
  pathname: string,
  href: string,
  sectionHrefs: string[],
): boolean {
  const candidates = sectionHrefs.filter((h) =>
    h === "/"
      ? pathname === "/"
      : pathname === h || pathname.startsWith(`${h}/`),
  );
  if (candidates.length === 0) return false;
  const best = candidates.reduce((a, b) => (a.length >= b.length ? a : b));
  return href === best;
}

function SimNavLink({
  href,
  label,
  icon: Icon,
  active,
  onClick,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={clsx(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        active
          ? "bg-accent/10 text-accent border border-accent/20"
          : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
      )}
    >
      <Icon
        className={clsx(
          "w-4 h-4",
          active ? "text-accent" : "text-foreground-subtle"
        )}
      />
      {label}
    </Link>
  );
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = true, onClose }: SidebarProps) {
  const pathname = usePathname();
  const simulationId = getSimulationIdFromPath(pathname);
  const isInSimulation = simulationId !== null;
  const currentSimulation = useSimulationStore((s) => s.currentSimulation);
  const [collapsed, setCollapsed] = useState<Record<SimSectionKey, boolean>>(
    loadCollapsedSections
  );

  useEffect(() => {
    if (!isOpen || !onClose) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const toggleSection = (key: SimSectionKey) => {
    setCollapsed((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        localStorage.setItem(SIDEBAR_COLLAPSE_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const handleLinkClick = () => {
    if (onClose) {
      onClose();
    }
  };

  const primaryHrefs = navigation.map((n) => n.href);
  const analyticsHrefs = analyticsNav.map((n) => n.href);
  const toolsHrefs = toolsNav.map((n) => n.href);
  const showReport =
    currentSimulation?.id === simulationId &&
    currentSimulation?.status === "completed";

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        role={isOpen ? 'dialog' : undefined}
        aria-modal={isOpen ? true : undefined}
        aria-label="Main navigation"
        className={clsx(
          "fixed md:static inset-y-0 left-0 z-50 w-[80vw] sm:w-64 max-w-sm bg-background-secondary border-r border-border flex flex-col transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-border">
          <Link
            href="/"
            className="flex items-center gap-2 group"
            onClick={handleLinkClick}
          >
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
              <Fish className="w-5 h-5 text-accent" />
            </div>
            <span className="text-lg font-bold text-foreground tracking-tight">
              ScenarioLab
            </span>
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="md:hidden p-2 text-foreground-muted hover:text-foreground rounded-lg hover:bg-background-tertiary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="space-y-1">
            {navigation.map((item) => {
              const isActive =
                isNavItemActive(pathname, item.href, primaryHrefs) &&
                !isInSimulation;
              const Icon = item.icon;

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={handleLinkClick}
                  aria-current={isActive ? "page" : undefined}
                  className={clsx(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                    isActive
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                  )}
                >
                  <Icon
                    className={clsx(
                      "w-4 h-4",
                      isActive ? "text-accent" : "text-foreground-subtle"
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>

          <div className="pt-4 mt-4 border-t border-border">
            <h3 className="px-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
              Analytics
            </h3>
            {analyticsNav.map((item) => {
              const isActive = isNavItemActive(
                pathname,
                item.href,
                analyticsHrefs
              );
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={handleLinkClick}
                  aria-current={isActive ? "page" : undefined}
                  className={clsx(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                    isActive
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                  )}
                >
                  <Icon
                    className={clsx(
                      "w-4 h-4",
                      isActive ? "text-accent" : "text-foreground-subtle"
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>

          <div className="pt-4 mt-4 border-t border-border">
            <h3 className="px-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
              Tools
            </h3>
            {toolsNav.map((item) => {
              const isActive = isNavItemActive(pathname, item.href, toolsHrefs);
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={handleLinkClick}
                  aria-current={isActive ? "page" : undefined}
                  className={clsx(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                    isActive
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                  )}
                >
                  <Icon
                    className={clsx(
                      "w-4 h-4",
                      isActive ? "text-accent" : "text-foreground-subtle"
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>

          {isInSimulation && simulationId && (
            <div className="pt-4 mt-4 border-t border-border space-y-1">
              <h3 className="px-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                Current Simulation
              </h3>

              <SimNavLink
                href={`/simulations/${simulationId}`}
                label="Overview"
                icon={Play}
                active={pathname === `/simulations/${simulationId}`}
                onClick={handleLinkClick}
              />
              <SimNavLink
                href={`/simulations/${simulationId}/chat`}
                label="Chat"
                icon={MessageSquare}
                active={pathname.includes("/chat")}
                onClick={handleLinkClick}
              />
              {showReport && (
                <SimNavLink
                  href={`/simulations/${simulationId}/report`}
                  label="Report"
                  icon={FileText}
                  active={pathname.includes("/report")}
                  onClick={handleLinkClick}
                />
              )}

              <button
                type="button"
                onClick={() => toggleSection("visualizations")}
                className="w-full flex items-center justify-between px-3 mt-3 mb-1 text-xs font-medium text-foreground-subtle uppercase tracking-wider hover:text-foreground"
                aria-expanded={!collapsed.visualizations}
              >
                Visualizations
                <ChevronDown
                  className={clsx(
                    "w-4 h-4 transition-transform",
                    collapsed.visualizations && "-rotate-90"
                  )}
                />
              </button>
              {!collapsed.visualizations && (
                <>
                  <SimNavLink
                    href={`/simulations/${simulationId}/network`}
                    label="Network Graph"
                    icon={Network}
                    active={pathname.includes("/network")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/timeline`}
                    label="Timeline"
                    icon={Clock}
                    active={pathname.includes("/timeline")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/sensitivity`}
                    label="Sensitivity"
                    icon={BarChart3}
                    active={pathname.includes("/sensitivity")}
                    onClick={handleLinkClick}
                  />
                </>
              )}

              <button
                type="button"
                onClick={() => toggleSection("advanced")}
                className="w-full flex items-center justify-between px-3 mt-3 mb-1 text-xs font-medium text-foreground-subtle uppercase tracking-wider hover:text-foreground"
                aria-expanded={!collapsed.advanced}
              >
                Advanced
                <ChevronDown
                  className={clsx(
                    "w-4 h-4 transition-transform",
                    collapsed.advanced && "-rotate-90"
                  )}
                />
              </button>
              {!collapsed.advanced && (
                <>
                  <SimNavLink
                    href={`/simulations/${simulationId}/voice`}
                    label="Voice Chat"
                    icon={Mic}
                    active={pathname.includes("/voice")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/zopa`}
                    label="ZOPA Mapping"
                    icon={Target}
                    active={pathname.includes("/zopa")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/rehearsal`}
                    label="Rehearsal"
                    icon={Users}
                    active={pathname.includes("/rehearsal")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/audit-trail`}
                    label="Audit Trail"
                    icon={History}
                    active={pathname.includes("/audit-trail")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/attribution`}
                    label="Attribution"
                    icon={PieChart}
                    active={pathname.includes("/attribution")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/fairness`}
                    label="Fairness Audit"
                    icon={Scale}
                    active={pathname.includes("/fairness")}
                    onClick={handleLinkClick}
                  />
                  <SimNavLink
                    href={`/simulations/${simulationId}/market-intel`}
                    label="Market Intel"
                    icon={TrendingUp}
                    active={pathname.includes("/market-intel")}
                    onClick={handleLinkClick}
                  />
                </>
              )}
            </div>
          )}
        </nav>

        <div className="p-4 border-t border-border">
          <div className="text-xs text-foreground-subtle">
            <p>ScenarioLab v0.1.0</p>
            <p className="mt-1">AI War-Gaming Platform</p>
          </div>
        </div>
      </aside>
    </>
  );
}
