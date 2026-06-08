import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
}

export function Skeleton({ className, width, height, borderRadius }: SkeletonProps) {
  return (
    <div
      className={cn('skeleton-shimmer rounded-lg', className)}
      style={{
        width: width ?? undefined,
        height: height ?? undefined,
        borderRadius: borderRadius ?? undefined,
      }}
    />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <Skeleton className="mb-3 h-3 w-24" />
      <Skeleton className="mb-4 h-8 w-16" />
      <Skeleton className="h-12 w-full" />
    </div>
  );
}

export function TaskRowSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border p-4">
      <Skeleton className="h-5 w-5 rounded" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/3" />
      </div>
    </div>
  );
}

export function ResourceCardSkeleton() {
  return <Skeleton className="h-48 w-full" />;
}

export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return <Skeleton height={height} className="w-full" />;
}
