import { Skeleton } from "@/components/ui/skeleton";

export function BrandedSkeleton() {
  return (
    <div className="container py-6 md:py-8">
      {/* Header skeleton */}
      <div className="brutal-border brutal-shadow mb-4 bg-primary px-5 py-5 md:mb-6 md:px-7 md:py-6">
        <Skeleton className="h-7 w-56 rounded-none bg-foreground/10 md:h-8" />
        <Skeleton className="mt-2 h-4 w-40 rounded-none bg-foreground/10" />
      </div>

      {/* Filter boxes skeleton */}
      <div className="mb-4 md:mb-6">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 md:gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="brutal-border brutal-shadow space-y-2 bg-card p-3"
              >
                <Skeleton className="h-2.5 w-16 rounded-none" />
                <Skeleton className="h-7 w-full rounded-none" />
              </div>
            ))}
          </div>

          {/* Sort bar skeleton */}
          <div className="flex flex-wrap items-center gap-3">
            <Skeleton className="h-9 w-64 rounded-none" />
            <Skeleton className="h-5 w-24 rounded-none" />
            <Skeleton className="h-8 w-16 rounded-none" />
          </div>
        </div>
      </div>

      {/* Results count skeleton */}
      <div className="mb-3 flex items-center gap-2">
        <Skeleton className="brutal-border h-9 w-14 rounded-none" />
        <Skeleton className="h-4 w-24 rounded-none" />
      </div>

      {/* Result rows skeleton */}
      <ul className="space-y-2 md:space-y-2.5">
        {Array.from({ length: 6 }).map((_, i) => (
          <li key={i} className="brutal-border bg-card" aria-hidden>
            <div className="flex flex-col md:flex-row md:items-stretch">
              {/* Rank column — hidden on mobile */}
              <div className="hidden w-12 shrink-0 items-center justify-center border-r border-border bg-foreground md:flex">
                <Skeleton className="h-5 w-6 rounded-none bg-primary/20" />
              </div>

              {/* Food info */}
              <div className="flex min-w-0 flex-1 items-center gap-3 border-b border-border p-3 md:border-b-0 md:border-r md:px-4 md:py-3">
                <Skeleton className="h-9 w-9 shrink-0 rounded-none" />
                <div className="min-w-0 flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/5 rounded-none" />
                  <Skeleton className="h-3 w-24 rounded-none" />
                </div>
              </div>

              {/* Stat tiles */}
              <div className="flex items-stretch">
                {Array.from({ length: 5 }).map((__, j) => (
                  <div
                    key={j}
                    className="flex min-w-0 flex-1 flex-col items-center justify-center border-l border-border py-1.5 first:border-l-0 md:w-[68px] md:flex-none md:py-2"
                  >
                    <Skeleton className="h-4 w-8 rounded-none" />
                    <Skeleton className="mt-1 h-2 w-6 rounded-none" />
                  </div>
                ))}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
