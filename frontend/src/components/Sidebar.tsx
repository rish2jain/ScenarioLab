"use client";

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
  Gavel,
  Lightbulb,
  Settings,
} from "lucide-react";
import { clsx } from "clsx";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Upload", href: "/upload", icon: Upload },
  { name: "Simulations", href: "/simulations", icon: Play },
  { name: "Playbooks", href: "/playbooks", icon: BookOpen },
  { name: "Reports", href: "/reports", icon: FileText },
];

const analyticsNav = [
  { name: "Attribution Analysis", href: "/analytics/attribution", icon: PieChart },
  { name: "Fairness Audit", href: "/analytics/fairness", icon: Scale },
  { name: "Cross-Simulation", href: "/analytics/cross-simulation", icon: Brain },
];

const toolsNav = [
  { name: "Fine-Tuning", href: "/fine-tuning", icon: Settings },
  { name: "API Keys", href: "/api-keys", icon: Key },
  { name: "Market Intelligence", href: "/market-intel", icon: TrendingUp },
];

// Helper to check if a nav item is active
function isNavItemActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}

// Extract simulation ID from pathname if viewing a simulation
function getSimulationIdFromPath(pathname: string): string | null {
  const match = pathname.match(/\/simulations\/([^/]+)/);
  return match ? match[1] : null;
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = true, onClose }: SidebarProps) {
  const pathname = usePathname();
  const simulationId = getSimulationIdFromPath(pathname);
  const isInSimulation = simulationId !== null;
  const isVisualizationPage = pathname.includes('/network') || pathname.includes('/timeline') || pathname.includes('/sensitivity') || pathname.includes('/chat') || pathname.includes('/voice') || pathname.includes('/zopa') || pathname.includes('/rehearsal') || pathname.includes('/audit-trail') || pathname.includes('/attribution') || pathname.includes('/fairness') || pathname.includes('/market-intel');

  const handleLinkClick = () => {
    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside className={clsx(
        "fixed md:static inset-y-0 left-0 z-50 w-64 bg-background-secondary border-r border-border flex flex-col transition-transform duration-300 ease-in-out",
        isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-border">
        <Link href="/" className="flex items-center gap-2 group" onClick={handleLinkClick}>
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <Fish className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-foreground group-hover:text-accent transition-colors">
            MiroFish
          </span>
        </Link>
        {/* Close button for mobile */}
        <button
          onClick={onClose}
          className="p-2 rounded-lg text-foreground-muted hover:text-foreground hover:bg-background-tertiary md:hidden"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = isNavItemActive(pathname, item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={handleLinkClick}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                isActive && !isInSimulation
                  ? "bg-accent/10 text-accent border border-accent/20"
                  : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
              )}
            >
              <Icon
                className={clsx(
                  "w-5 h-5",
                  isActive && !isInSimulation ? "text-accent" : "text-foreground-subtle"
                )}
              />
              {item.name}
            </Link>
          );
        })}

        {/* Analytics Section */}
        <div className="pt-4 mt-4 border-t border-border">
          <div className="px-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
            Analytics
          </div>
          {analyticsNav.map((item) => {
            const isActive = isNavItemActive(pathname, item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
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

        {/* Tools Section */}
        <div className="pt-4 mt-4 border-t border-border">
          <div className="px-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
            Tools
          </div>
          {toolsNav.map((item) => {
            const isActive = isNavItemActive(pathname, item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
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

        {/* Simulation-specific navigation */}
        {isInSimulation && (
          <>
            <div className="pt-4 mt-4 border-t border-border">
              <div className="px-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                Current Simulation
              </div>
              
              <Link
                href={`/simulations/${simulationId}`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname === `/simulations/${simulationId}`
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Play className={clsx(
                  "w-4 h-4",
                  pathname === `/simulations/${simulationId}` ? "text-accent" : "text-foreground-subtle"
                )} />
                Overview
              </Link>

              <Link
                href={`/simulations/${simulationId}/chat`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/chat')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <MessageSquare className={clsx(
                  "w-4 h-4",
                  pathname.includes('/chat') ? "text-accent" : "text-foreground-subtle"
                )} />
                Chat
              </Link>

              <div className="px-3 mt-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                Visualizations
              </div>

              <Link
                href={`/simulations/${simulationId}/network`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/network')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Network className={clsx(
                  "w-4 h-4",
                  pathname.includes('/network') ? "text-accent" : "text-foreground-subtle"
                )} />
                Network Graph
              </Link>

              <Link
                href={`/simulations/${simulationId}/timeline`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/timeline')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Clock className={clsx(
                  "w-4 h-4",
                  pathname.includes('/timeline') ? "text-accent" : "text-foreground-subtle"
                )} />
                Timeline
              </Link>

              <Link
                href={`/simulations/${simulationId}/sensitivity`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/sensitivity')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <BarChart3 className={clsx(
                  "w-4 h-4",
                  pathname.includes('/sensitivity') ? "text-accent" : "text-foreground-subtle"
                )} />
                Sensitivity
              </Link>

              <div className="px-3 mt-3 mb-2 text-xs font-medium text-foreground-subtle uppercase tracking-wider">
                Advanced
              </div>

              <Link
                href={`/simulations/${simulationId}/voice`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/voice')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Mic className={clsx(
                  "w-4 h-4",
                  pathname.includes('/voice') ? "text-accent" : "text-foreground-subtle"
                )} />
                Voice Chat
              </Link>

              <Link
                href={`/simulations/${simulationId}/zopa`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/zopa')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Target className={clsx(
                  "w-4 h-4",
                  pathname.includes('/zopa') ? "text-accent" : "text-foreground-subtle"
                )} />
                ZOPA Mapping
              </Link>

              <Link
                href={`/simulations/${simulationId}/rehearsal`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/rehearsal')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Users className={clsx(
                  "w-4 h-4",
                  pathname.includes('/rehearsal') ? "text-accent" : "text-foreground-subtle"
                )} />
                Rehearsal
              </Link>

              <Link
                href={`/simulations/${simulationId}/audit-trail`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/audit-trail')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <History className={clsx(
                  "w-4 h-4",
                  pathname.includes('/audit-trail') ? "text-accent" : "text-foreground-subtle"
                )} />
                Audit Trail
              </Link>

              <Link
                href={`/simulations/${simulationId}/attribution`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/attribution')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <PieChart className={clsx(
                  "w-4 h-4",
                  pathname.includes('/attribution') ? "text-accent" : "text-foreground-subtle"
                )} />
                Attribution
              </Link>

              <Link
                href={`/simulations/${simulationId}/fairness`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/fairness')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <Scale className={clsx(
                  "w-4 h-4",
                  pathname.includes('/fairness') ? "text-accent" : "text-foreground-subtle"
                )} />
                Fairness Audit
              </Link>

              <Link
                href={`/simulations/${simulationId}/market-intel`}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                  pathname.includes('/market-intel')
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-foreground-muted hover:text-foreground hover:bg-background-tertiary"
                )}
              >
                <TrendingUp className={clsx(
                  "w-4 h-4",
                  pathname.includes('/market-intel') ? "text-accent" : "text-foreground-subtle"
                )} />
                Market Intel
              </Link>
            </div>
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="text-xs text-foreground-subtle">
          <p>MiroFish v0.1.0</p>
          <p className="mt-1">AI War-Gaming Platform</p>
        </div>
      </div>
      </aside>
    </>
  );
}
