import { clsx } from 'clsx';
import type { Agent } from '@/lib/types';
import { User, Brain, Target, Shield, Scale, MessageCircle } from 'lucide-react';

interface AgentCardProps {
  agent: Agent;
  showDetails?: boolean;
  className?: string;
  onClick?: () => void;
  isSelected?: boolean;
}

const archetypeIcons: Record<string, React.ReactNode> = {
  aggressor: <Target className="w-4 h-4" />,
  defender: <Shield className="w-4 h-4" />,
  mediator: <Scale className="w-4 h-4" />,
  analyst: <Brain className="w-4 h-4" />,
  influencer: <MessageCircle className="w-4 h-4" />,
  skeptic: <User className="w-4 h-4" />,
};

const archetypeLabels: Record<string, string> = {
  aggressor: 'Aggressor',
  defender: 'Defender',
  mediator: 'Mediator',
  analyst: 'Analyst',
  influencer: 'Influencer',
  skeptic: 'Skeptic',
};

export function AgentCard({
  agent,
  showDetails = false,
  className,
  onClick,
  isSelected = false,
}: AgentCardProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'p-4 rounded-lg border transition-all duration-200',
        isSelected
          ? 'bg-slate-700 border-accent'
          : 'bg-slate-800/50 border-slate-700 hover:border-slate-600',
        onClick && 'cursor-pointer',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${agent.color}20` }}
        >
          <span
            className="text-lg font-bold"
            style={{ color: agent.color }}
          >
            {agent.name.charAt(0)}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-slate-200 truncate">{agent.name}</h4>
          <p className="text-sm text-slate-400 truncate">{agent.role}</p>
          
          {/* Archetype Badge */}
          <div
            className="inline-flex items-center gap-1.5 mt-2 px-2 py-0.5 rounded-full text-xs font-medium"
            style={{ backgroundColor: `${agent.color}15`, color: agent.color }}
          >
            {archetypeIcons[agent.archetype]}
            {archetypeLabels[agent.archetype]}
          </div>
        </div>

        {/* Status Indicator */}
        <div
          className={clsx(
            'w-2.5 h-2.5 rounded-full',
            agent.isActive ? 'bg-green-400' : 'bg-slate-600'
          )}
        />
      </div>

      {showDetails && (
        <div className="mt-4 space-y-3 pt-4 border-t border-slate-700">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Description
            </p>
            <p className="text-sm text-slate-300">{agent.description}</p>
          </div>

          {agent.traits.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                Traits
              </p>
              <div className="flex flex-wrap gap-2">
                {agent.traits.map((trait, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300"
                  >
                    {trait}
                  </span>
                ))}
              </div>
            </div>
          )}

          {agent.goals.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                Goals
              </p>
              <ul className="space-y-1">
                {agent.goals.map((goal, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-slate-300 flex items-start gap-2"
                  >
                    <span className="text-accent mt-1">•</span>
                    {goal}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
