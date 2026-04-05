'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Search, Clock, Users, Play, CheckCircle, BookOpen } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';
import { usePlaybookStore } from '@/lib/store';
import { api } from '@/lib/api';
import { Spinner } from '@/components/ui/Spinner';
import type { Playbook } from '@/lib/types';

const iconMap: Record<string, React.ReactNode> = {
  Building2: <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center"><span className="text-2xl">🏢</span></div>,
  ShieldAlert: <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center"><span className="text-2xl">🛡️</span></div>,
  Swords: <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center"><span className="text-2xl">⚔️</span></div>,
  Users: <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center"><span className="text-2xl">👥</span></div>,
};

export default function PlaybooksPage() {
  const { playbooks, setPlaybooks } = usePlaybookStore();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [selectedPlaybookPreview, setSelectedPlaybookPreview] = useState<Playbook | null>(null);
  const clickRequestId = useRef<number>(0);
  const displayPlaybook = selectedPlaybook ?? selectedPlaybookPreview;
  const { addToast } = useToast();

  /** Invalidate in-flight detail fetches so closing the modal cannot reopen when a request completes. */
  const handleClosePlaybook = () => {
    clickRequestId.current += 1;
    setSelectedPlaybook(null);
    setSelectedPlaybookPreview(null);
    setIsLoadingDetails(false);
  };

  useEffect(() => {
    let mounted = true;
    const loadPlaybooks = async () => {
      setIsLoading(true);
      try {
        const data = await api.getPlaybooks();
        if (mounted) setPlaybooks(data);
      } catch (err) {
        if (mounted) {
          addToast(
            err instanceof Error ? err.message : 'Failed to load playbooks.',
            'error'
          );
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    loadPlaybooks();
    return () => { mounted = false; };
  }, [setPlaybooks, addToast]);

  const filteredPlaybooks = playbooks.filter(
    (playbook) =>
      playbook.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      playbook.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      playbook.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading playbooks...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Playbook Library</h1>
        <p className="text-slate-400 mt-1 text-sm sm:text-base">
          Browse and select from our collection of war-gaming templates
        </p>
      </div>

      {/* Search */}
      <div className="max-w-md w-full">
        <Input
          placeholder="Search playbooks..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          leftIcon={<Search className="w-4 h-4" />}
          className="w-full"
        />
      </div>

      {/* Playbook Grid */}
      {filteredPlaybooks.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {filteredPlaybooks.map((playbook) => (
            <Card
              key={playbook.id}
              hover
              className="h-full cursor-pointer"
              onClick={async () => {
                const currentId = ++clickRequestId.current;
                setSelectedPlaybookPreview(playbook);
                setSelectedPlaybook(null);
                setIsLoadingDetails(true);
                try {
                  const fullDetails = await api.getPlaybook(playbook.id);
                  if (currentId === clickRequestId.current) {
                    if (fullDetails != null) {
                      setSelectedPlaybook(fullDetails);
                      setSelectedPlaybookPreview(null);
                    } else {
                      console.error(
                        '[PlaybooksPage] api.getPlaybook returned no data for id:',
                        playbook.id,
                      );
                      addToast('Playbook details could not be loaded.', 'error');
                      setSelectedPlaybook(null);
                      setSelectedPlaybookPreview(null);
                    }
                  }
                } catch (err) {
                  if (currentId === clickRequestId.current) {
                    addToast(
                      err instanceof Error
                        ? err.message
                        : 'Failed to load playbook details.',
                      'error'
                    );
                  }
                } finally {
                  if (currentId === clickRequestId.current) {
                    setIsLoadingDetails(false);
                  }
                }
              }}
            >
              <div className="p-4 md:p-6">
                <div className="flex items-start gap-4">
                  {iconMap[playbook.icon] || (
                    <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center">
                      <BookOpen className="w-6 h-6 text-slate-400" />
                    </div>
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-slate-100">{playbook.name}</h3>
                    </div>
                    <Badge variant="info" size="sm" className="mt-2">
                      {playbook.category}
                    </Badge>
                  </div>
                </div>

                <p className="text-slate-400 text-sm mt-4 line-clamp-2">
                  {playbook.description}
                </p>

                <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{playbook.typicalDuration}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5" />
                    <span>{playbook.agentCount} agents</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Play className="w-3.5 h-3.5" />
                    <span>{playbook.rounds} rounds</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          {searchQuery.trim().length > 0 ? (
            <EmptyState
              title="No playbooks found"
              description={`No playbooks match your search for "${searchQuery}".`}
              icon={<Search className="w-8 h-8" />}
              action={{
                label: 'Clear Search',
                onClick: () => setSearchQuery(''),
              }}
            />
          ) : (
            <EmptyState
              title="No playbooks yet"
              description="Your library does not have any playbooks yet. Start a new simulation to configure a run, or check back after templates are added."
              icon={<BookOpen className="w-8 h-8" />}
              action={{
                label: 'New simulation',
                onClick: () => router.push('/simulations/new'),
              }}
            />
          )}
        </Card>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={!!selectedPlaybook || isLoadingDetails || !!selectedPlaybookPreview}
        onClose={handleClosePlaybook}
        title={displayPlaybook?.name ?? 'Playbook'}
        description={displayPlaybook?.description}
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={handleClosePlaybook}>
              Close
            </Button>
            {isLoadingDetails ? (
              <Button leftIcon={<Play className="w-4 h-4" />} disabled>
                Use Template
              </Button>
            ) : (
              <Link
                href={
                  displayPlaybook
                    ? `/simulations/new?playbook=${encodeURIComponent(displayPlaybook.id)}`
                    : '/simulations/new'
                }
              >
                <Button leftIcon={<Play className="w-4 h-4" />}>
                  Use Template
                </Button>
              </Link>
            )}
          </>
        }
      >
        {selectedPlaybook ? (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-3 bg-slate-700/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-accent">
                  {selectedPlaybook.agentCount}
                </p>
                <p className="text-xs text-slate-400">Agents</p>
              </div>
              <div className="p-3 bg-slate-700/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-accent">
                  {selectedPlaybook.rounds}
                </p>
                <p className="text-xs text-slate-400">Rounds</p>
              </div>
              <div className="p-3 bg-slate-700/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-accent">
                  {selectedPlaybook.typicalDuration}
                </p>
                <p className="text-xs text-slate-400">Duration</p>
              </div>
            </div>

            {/* Description */}
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">
                About this Playbook
              </h4>
              <p className="text-slate-400 text-sm">
                {selectedPlaybook.longDescription}
              </p>
            </div>

            {/* Objectives */}
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">
                Objectives
              </h4>
              <ul className="space-y-2">
                {(selectedPlaybook?.objectives ?? []).map((objective, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-400">
                    <CheckCircle className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                    {objective}
                  </li>
                ))}
              </ul>
            </div>

            {/* Roster */}
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">
                Agent Roster
              </h4>
              <div className="space-y-2">
                {(selectedPlaybook?.roster ?? []).map((role, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-200">
                        {role.role}
                      </p>
                      <p className="text-xs text-slate-500">
                        {role.description}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="default" size="sm">
                        {role.archetype}
                      </Badge>
                      {role.required && (
                        <Badge variant="info" size="sm">
                          Required
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Required Seeds */}
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">
                Required Seed Materials
              </h4>
              <div className="flex flex-wrap gap-2">
                {(selectedPlaybook?.requiredSeeds ?? []).map((seed, idx) => (
                  <Badge key={idx} variant="default" size="sm">
                    {seed}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        ) : displayPlaybook ? (
          <div className="space-y-6">
            <div className="rounded-xl border border-slate-600/60 bg-slate-800/40 p-4 md:p-5">
              <div className="flex items-start gap-4">
                {iconMap[displayPlaybook.icon] || (
                  <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center">
                    <BookOpen className="w-6 h-6 text-slate-400" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-slate-100">{displayPlaybook.name}</h3>
                  <Badge variant="info" size="sm" className="mt-2">
                    {displayPlaybook.category}
                  </Badge>
                </div>
              </div>
              <p className="text-slate-400 text-sm mt-4 line-clamp-3">
                {displayPlaybook.description}
              </p>
              <div className="flex flex-wrap items-center gap-4 mt-4 text-xs text-slate-500">
                <div className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{displayPlaybook.typicalDuration}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  <span>{displayPlaybook.agentCount} agents</span>
                </div>
                <div className="flex items-center gap-1">
                  <Play className="w-3.5 h-3.5" />
                  <span>{displayPlaybook.rounds} rounds</span>
                </div>
              </div>
            </div>
            {isLoadingDetails && (
              <div className="flex flex-col items-center justify-center gap-2 py-6">
                <Spinner size="lg" />
                <p className="text-slate-500 text-sm">Loading full details…</p>
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
