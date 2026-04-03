'use client';

import { useState } from 'react';
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

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    onChange?.(tabId);
  };

  const activeContent = tabs.find((t) => t.id === activeTab)?.content;

  return (
    <div className={clsx('w-full', className)}>
      {/* Tab List */}
      <div className="flex border-b border-slate-700 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={clsx(
              'px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors relative',
              activeTab === tab.id
                ? 'text-accent'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.label}
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="py-4">{activeContent}</div>
    </div>
  );
}
