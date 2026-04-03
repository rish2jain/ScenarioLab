import { clsx } from 'clsx';

interface RoundIndicatorProps {
  currentRound: number;
  totalRounds: number;
  className?: string;
}

export function RoundIndicator({
  currentRound,
  totalRounds,
  className,
}: RoundIndicatorProps) {
  const progress = (currentRound / totalRounds) * 100;

  return (
    <div className={clsx('flex items-center gap-4', className)}>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-300">Progress</span>
          <span className="text-sm font-semibold text-accent">
            Round {currentRound} / {totalRounds}
          </span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent to-cyan-400 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
