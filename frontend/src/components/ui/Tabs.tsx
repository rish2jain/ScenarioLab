'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { clsx } from 'clsx';

interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  className?: string;
}

export function Tabs({ tabs, defaultTab, onChange, className }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    onChange?.(tabId);
  };

  const focusTab = (tabId: string) => {
    tabRefs.current.get(tabId)?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>, currentId: string) => {
    const idx = tabs.findIndex((t) => t.id === currentId);
    if (idx === -1) return;

    let nextIdx = idx;
    switch (e.key) {
      case 'ArrowRight':
        nextIdx = (idx + 1) % tabs.length;
        e.preventDefault();
        break;
      case 'ArrowLeft':
        nextIdx = (idx - 1 + tabs.length) % tabs.length;
        e.preventDefault();
        break;
      case 'Home':
        nextIdx = 0;
        e.preventDefault();
        break;
      case 'End':
        nextIdx = tabs.length - 1;
        e.preventDefault();
        break;
      default:
        return;
    }

    const nextTab = tabs[nextIdx];
    handleTabChange(nextTab.id);
    focusTab(nextTab.id);
  };

  return (
    <div className={clsx('w-full', className)}>
      <div
        role="tablist"
        aria-orientation="horizontal"
        className="flex border-b border-border overflow-x-auto"
      >
        {tabs.map((tab) => {
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              ref={(el) => {
                if (el) tabRefs.current.set(tab.id, el);
                else tabRefs.current.delete(tab.id);
              }}
              type="button"
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={isSelected}
              aria-controls={`tabpanel-${tab.id}`}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => handleTabChange(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, tab.id)}
              className={clsx(
                'px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors relative',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                isSelected
                  ? 'text-accent'
                  : 'text-foreground-muted hover:text-foreground'
              )}
            >
              {tab.label}
              {isSelected && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" aria-hidden="true" />
              )}
            </button>
          );
        })}
      </div>

      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`tabpanel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={activeTab !== tab.id}
          tabIndex={activeTab === tab.id ? 0 : undefined}
          className="py-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg"
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
