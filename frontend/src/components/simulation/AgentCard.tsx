import { clsx } from 'clsx';
import { archetypeColors } from '@/lib/archetypeColors';
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

/** Matches `displayColor` fallback when `agent.color` and archetype map omit a color. */
const FALLBACK_DISPLAY_COLOR = '#6b7280';

function parseHexRgb(color: string): { r: number; g: number; b: number } | null {
  if (!color || typeof color !== 'string') return null;
  let hex = color.trim().replace(/^#/, '');
  if (hex.length === 3) {
    if (!/^[0-9a-fA-F]{3}$/.test(hex)) return null;
    hex = hex
      .split('')
      .map((c) => c + c)
      .join('');
  }
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
  return {
    r: parseInt(hex.slice(0, 2), 16),
    g: parseInt(hex.slice(2, 4), 16),
    b: parseInt(hex.slice(4, 6), 16),
  };
}

const isLightColor = (color: string) => {
  const rgb = parseHexRgb(color);
  const { r, g, b } = rgb ?? parseHexRgb(FALLBACK_DISPLAY_COLOR)!;
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128;
};

export function AgentCard({
  agent,
  showDetails = false,
  className,
  onClick,
  isSelected = false,
}: AgentCardProps) {
  const Component = onClick ? 'button' : 'div';
  const buttonProps = onClick ? { type: 'button' as const } : {};
  const displayColor =
    agent.color || archetypeColors[agent.archetype] || FALLBACK_DISPLAY_COLOR;

  return (
    <Component
      onClick={onClick}
      {...buttonProps}
      className={clsx(
        'w-full text-left p-4 rounded-lg border transition-all duration-200',
        isSelected
          ? 'bg-background-tertiary border-accent'
          : 'bg-background-secondary border-border hover:border-border-hover',
        onClick && 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: displayColor }}
        >
          <span className={clsx(
            "text-lg font-bold shadow-sm",
            isLightColor(displayColor) ? "text-gray-900" : "text-white"
          )}>
            {agent.name.charAt(0)}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-foreground truncate" title={agent.name}>{agent.name}</h4>
          <p className="text-sm text-foreground-muted truncate" title={agent.role}>{agent.role}</p>
          
          {/* Archetype Badge */}
          <div
            className="inline-flex items-center gap-1.5 mt-2 px-2 py-0.5 rounded-full text-xs font-medium border"
            style={{ borderColor: displayColor, color: displayColor }}
          >
            {archetypeIcons[agent.archetype]}
            {archetypeLabels[agent.archetype]}
          </div>
        </div>

        {/* Status Indicator */}
        <div
          className={clsx(
            'w-2.5 h-2.5 rounded-full flex-shrink-0',
            agent.isActive ? 'bg-success' : 'bg-foreground-subtle'
          )}
          aria-label={agent.isActive ? 'Active agent' : 'Inactive agent'}
          role="status"
        />
      </div>

      {showDetails && (
        <div className="mt-4 space-y-3 pt-4 border-t border-border">
          <div>
            <p className="text-xs text-foreground-subtle uppercase tracking-wider mb-1">
              Description
            </p>
            <p className="text-sm text-foreground-muted">{agent.description}</p>
          </div>

          {agent.traits.length > 0 && (
            <div>
              <p className="text-xs text-foreground-subtle uppercase tracking-wider mb-2">
                Traits
              </p>
              <div className="flex flex-wrap gap-2">
                {agent.traits.map((trait, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-background-tertiary border border-border rounded text-xs text-foreground-muted"
                  >
                    {trait}
                  </span>
                ))}
              </div>
            </div>
          )}

          {agent.goals.length > 0 && (
            <div>
              <p className="text-xs text-foreground-subtle uppercase tracking-wider mb-2">
                Goals
              </p>
              <ul className="space-y-1">
                {agent.goals.map((goal, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-foreground-muted flex items-start gap-2"
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
    </Component>
  );
}
