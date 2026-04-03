"use client";

import { usePathname } from "next/navigation";
import { ChevronRight, Bell, User, Menu } from "lucide-react";

const breadcrumbMap: Record<string, string> = {
  "/": "Dashboard",
  "/upload": "Upload",
  "/simulations": "Simulations",
  "/simulations/new": "New Simulation",
  "/playbooks": "Playbooks",
  "/reports": "Reports",
};

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname();
  const pageTitle = breadcrumbMap[pathname] || "Page";

  return (
    <header className="h-16 bg-background-secondary border-b border-border flex items-center justify-between px-4 md:px-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        {/* Hamburger menu button for mobile */}
        <button
          onClick={onMenuClick}
          className="p-2 -ml-2 rounded-lg text-foreground-muted hover:text-foreground hover:bg-background-tertiary md:hidden"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <span className="text-foreground-muted hidden sm:inline">MiroFish</span>
        <ChevronRight className="w-4 h-4 text-foreground-subtle hidden sm:block" />
        <span className="text-foreground font-medium">{pageTitle}</span>
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="relative p-2 text-foreground-muted hover:text-foreground transition-colors rounded-lg hover:bg-background-tertiary">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent rounded-full" />
        </button>

        {/* User menu */}
        <button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-background-tertiary transition-colors">
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
