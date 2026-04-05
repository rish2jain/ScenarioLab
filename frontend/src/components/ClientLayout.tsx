"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { initSentryClient } from "@/lib/error-reporting";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { ToastProvider } from "@/components/ui/Toast";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { isSimulationDetailLayoutPath } from "@/lib/simulationRoutes";
import { useSeedGraphPoll } from "@/lib/hooks/useSeedGraphPoll";

initSentryClient();

function ClientLayoutInner({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const pathname = usePathname();
  useSeedGraphPoll();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header onMenuClick={() => setIsSidebarOpen(true)} />
        <main
          className={clsx(
            'flex-1 overflow-auto flex justify-center',
            pathname && !isSimulationDetailLayoutPath(pathname) && 'p-4 md:p-6'
          )}
        >
          <div className="w-full max-w-7xl">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}

export function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <ClientLayoutInner>{children}</ClientLayoutInner>
    </ToastProvider>
  );
}
