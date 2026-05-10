import { Inbox, AlertTriangle } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/Stat";
import { RestaurantBadge } from "@/components/RestaurantBadge";
import { formatInt, formatNumber } from "@/lib/utils";
import type { FoodSearchResult } from "@/api/client";

interface ResultsTableProps {
  rows: FoodSearchResult[] | undefined;
  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
}

export function ResultsTable({
  rows,
  isLoading,
  isFetching,
  error,
}: ResultsTableProps) {
  if (error) {
    return (
      <EmptyState
        icon={<AlertTriangle className="h-5 w-5 text-destructive" />}
        title="Couldn't load results"
        description={error.message}
      />
    );
  }

  if (isLoading || !rows) {
    return <SkeletonRows />;
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<Inbox className="h-5 w-5 text-muted-foreground" />}
        title="No items match"
        description="Try loosening your filters — drag a slider to 0 to turn it off, or include add-ons."
      />
    );
  }

  return (
    <div className="relative">
      {isFetching ? (
        <div className="pointer-events-none absolute inset-x-0 -top-px h-1 overflow-hidden bg-primary/30">
          <div className="h-full w-1/3 animate-[shimmer_1.6s_linear_infinite] bg-gradient-to-r from-transparent via-primary to-transparent" />
        </div>
      ) : null}

      <ul className="space-y-2 md:space-y-2.5">
        {rows.map((row, idx) => (
          <li
            key={`${row.restaurant_name}-${row.food_name}-${row.size ?? ""}-${idx}`}
            className="brutal-border brutal-shadow-hover bg-card"
          >
            {/* Mobile: stacked. Desktop: single row */}
            <div className="flex flex-col md:flex-row md:items-stretch">
              {/* Rank */}
              <div className="hidden w-12 shrink-0 items-center justify-center border-r border-border bg-foreground font-mono text-lg font-bold text-primary dark:bg-primary/15 dark:text-primary md:flex">
                {String(idx + 1).padStart(2, "0")}
              </div>

              {/* Food info */}
              <div className="flex min-w-0 flex-1 items-center gap-3 border-b border-border p-3 md:border-b-0 md:border-r md:px-4 md:py-3">
                <RestaurantBadge
                  name={row.restaurant_name}
                  size="md"
                  showName={false}
                />
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold md:text-base">
                    {row.food_name}
                  </div>
                  <div className="truncate text-[11px] text-muted-foreground md:text-xs">
                    {row.restaurant_name}
                    {row.size ? <> &middot; {row.size}</> : null}
                  </div>
                </div>
              </div>

              {/* Macro blocks */}
              <div className="flex items-stretch">
                <Stat
                  label="Kcal"
                  value={formatInt(row.kcal)}
                  tone="neutral"
                  title={`${row.kcal} kcal`}
                />
                <Stat
                  label="Protein"
                  value={formatNumber(row.protein)}
                  unit="g"
                  tone="protein"
                  title={`${row.protein.toFixed(1)} g protein`}
                />
                <Stat
                  label="Fats"
                  value={formatNumber(row.fats)}
                  unit="g"
                  tone="fats"
                  title={`${row.fats.toFixed(1)} g fats`}
                />
                <Stat
                  label="Carbs"
                  value={formatNumber(row.carbs)}
                  unit="g"
                  tone="carbs"
                  title={`${row.carbs.toFixed(1)} g carbs`}
                />
                <Stat
                  label="P/100"
                  value={formatNumber(row.protein_per_100_kcal)}
                  tone="primary"
                  size="lg"
                  title={`${row.protein_per_100_kcal.toFixed(2)} g protein per 100 kcal`}
                />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SkeletonRows() {
  return (
    <ul className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <li
          key={i}
          className="brutal-border bg-card"
          aria-hidden
        >
          <div className="flex items-center gap-3 p-3">
            <Skeleton className="h-9 w-9 rounded-none" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-4 w-2/5 rounded-none" />
              <Skeleton className="h-3 w-24 rounded-none" />
            </div>
            <div className="hidden gap-0 md:flex">
              {Array.from({ length: 5 }).map((__, j) => (
                <Skeleton key={j} className="h-12 w-14 rounded-none" />
              ))}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="brutal-border brutal-shadow flex flex-col items-center justify-center gap-3 bg-card px-6 py-16 text-center">
      <div className="brutal-border flex h-10 w-10 items-center justify-center bg-muted">
        {icon}
      </div>
      <div className="space-y-1">
        <p className="font-bold text-foreground">{title}</p>
        <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
