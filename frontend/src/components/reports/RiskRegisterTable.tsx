'use client';

import { Table, TableHead, TableBody, TableRow, TableCell } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import type { Risk } from '@/lib/types';

interface RiskRegisterTableProps {
  risks: Risk[];
}

export function RiskRegisterTable({ risks }: RiskRegisterTableProps) {
  const getProbabilityColor = (probability: string) => {
    switch (probability) {
      case 'low':
        return 'default';
      case 'medium':
        return 'info';
      case 'high':
        return 'warning';
      case 'critical':
        return 'danger';
      default:
        return 'default';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'low':
        return 'default';
      case 'medium':
        return 'info';
      case 'high':
        return 'warning';
      case 'critical':
        return 'danger';
      default:
        return 'default';
    }
  };

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell isHeader>ID</TableCell>
            <TableCell isHeader>Description</TableCell>
            <TableCell isHeader>Category</TableCell>
            <TableCell isHeader>Probability</TableCell>
            <TableCell isHeader>Impact</TableCell>
            <TableCell isHeader>Owner</TableCell>
            <TableCell isHeader>Mitigation</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {risks.map((risk) => (
            <TableRow key={risk.id}>
              <TableCell>
                <span className="font-mono text-slate-400">{risk.id}</span>
              </TableCell>
              <TableCell>
                <p className="text-slate-200 max-w-md">{risk.description}</p>
              </TableCell>
              <TableCell>
                <Badge variant="default" size="sm">
                  {risk.category}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={getProbabilityColor(risk.probability)} size="sm">
                  {risk.probability}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={getImpactColor(risk.impact)} size="sm">
                  {risk.impact}
                </Badge>
              </TableCell>
              <TableCell>
                <span className="text-slate-300">{risk.owner}</span>
              </TableCell>
              <TableCell>
                <p className="text-slate-400 text-sm max-w-xs">{risk.mitigation}</p>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
