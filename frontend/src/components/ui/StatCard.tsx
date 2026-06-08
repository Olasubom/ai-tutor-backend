import type { ReactNode } from 'react';
import { Card } from './Card';

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: ReactNode;
  icon?: ReactNode;
  visual?: ReactNode;
}

export function StatCard({ label, value, trend, icon, visual }: StatCardProps) {
  return (
    <Card className="p-6">
      <div className="mb-4 flex items-start justify-between">
        <span className="label-caps text-text-muted">{label}</span>
        {icon && <div className="rounded-full bg-primary/10 p-2 text-primary">{icon}</div>}
      </div>
      <div className="stat-number text-text-primary">{value}</div>
      {trend && <div className="mt-2 text-[14px]">{trend}</div>}
      {visual && <div className="mt-4">{visual}</div>}
    </Card>
  );
}
