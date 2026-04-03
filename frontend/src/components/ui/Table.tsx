import { clsx } from 'clsx';

interface TableProps {
  children: React.ReactNode;
  className?: string;
}

export function Table({ children, className }: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table className={clsx('w-full text-left border-collapse', className)}>
        {children}
      </table>
    </div>
  );
}

interface TableHeadProps {
  children: React.ReactNode;
  className?: string;
}

export function TableHead({ children, className }: TableHeadProps) {
  return (
    <thead className={clsx('bg-slate-800/80', className)}>
      {children}
    </thead>
  );
}

interface TableBodyProps {
  children: React.ReactNode;
  className?: string;
}

export function TableBody({ children, className }: TableBodyProps) {
  return <tbody className={className}>{children}</tbody>;
}

interface TableRowProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export function TableRow({ children, className, onClick, hover = false }: TableRowProps) {
  return (
    <tr
      className={clsx(
        'border-b border-slate-700 last:border-b-0',
        hover && 'hover:bg-slate-800/50 cursor-pointer transition-colors',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

interface TableCellProps {
  children: React.ReactNode;
  className?: string;
  isHeader?: boolean;
}

export function TableCell({ children, className, isHeader = false }: TableCellProps) {
  const Component = isHeader ? 'th' : 'td';
  return (
    <Component
      className={clsx(
        'px-4 py-3 text-sm',
        isHeader
          ? 'font-medium text-slate-300 uppercase tracking-wider'
          : 'text-slate-300',
        className
      )}
    >
      {children}
    </Component>
  );
}
