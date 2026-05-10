import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { searchFoods, countAllFoods } from "@/api/client";
import {
  DEFAULT_FILTERS,
  Filters,
  type FilterValues,
} from "@/components/Filters";
import { ResultsTable } from "@/components/ResultsTable";
import { BrandedSkeleton } from "@/components/BrandedSkeleton";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { formatInt } from "@/lib/utils";

export default function App() {
  const [filters, setFilters] = useState<FilterValues>(DEFAULT_FILTERS);

  const debouncedKcal = useDebouncedValue(filters.maxKcal, 250);
  const debouncedProtein = useDebouncedValue(filters.minProtein, 250);

  const effectiveFilters = useMemo(
    () => ({
      ...filters,
      maxKcal: debouncedKcal,
      minProtein: debouncedProtein,
    }),
    [filters, debouncedKcal, debouncedProtein],
  );

  const search = useQuery({
    queryKey: ["search", effectiveFilters],
    queryFn: ({ signal }) =>
      searchFoods(
        {
          max_kcal: effectiveFilters.maxKcal,
          min_protein: effectiveFilters.minProtein,
          restaurant_id: effectiveFilters.restaurantId,
          low_kcal_included: effectiveFilters.lowKcalIncluded,
          sort_by: effectiveFilters.sortBy,
        },
        signal,
      ),
    placeholderData: (prev) => prev,
  });

  const totalCountQuery = useQuery({
    queryKey: ["totalCount"],
    queryFn: ({ signal }) => countAllFoods(signal),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (search.error) {
      toast.error("Search failed", {
        description: (search.error as Error).message,
      });
    }
  }, [search.error]);

  const totalShown = search.data?.length ?? 0;
  const totalAll = totalCountQuery.data ?? 0;

  // First load with no cached data → show branded skeleton
  if (search.isLoading && !search.data) {
    return (
      <div className="relative min-h-screen bg-background text-foreground">
        <BrandedSkeleton />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <div className="container pb-[calc(env(safe-area-inset-bottom)+5rem)] pt-4 md:py-8 md:pb-8">
        {/* ── Header ── */}
        <header className="brutal-border brutal-shadow mb-4 bg-primary px-4 py-3 text-primary-foreground md:mb-6 md:px-7 md:py-6">
          <div className="flex items-baseline justify-between gap-3">
            <div className="min-w-0">
              <h1 className="truncate text-xl font-bold uppercase tracking-tight md:text-[32px]">
                Wroclaw Macro Finder
              </h1>
              <p className="mt-0.5 hidden text-sm font-medium opacity-80 md:block md:text-base">
                High-protein menu items, fast.
              </p>
            </div>
            {/* Mobile: count moves into the header so the body starts with results. */}
            <div className="flex items-baseline gap-1.5 md:hidden">
              <span className="brutal-border bg-accent px-2 py-0.5 font-mono text-base font-bold text-accent-foreground">
                {search.isLoading ? "…" : formatInt(totalShown)}
              </span>
              <span className="text-[11px] font-semibold opacity-80">
                /{formatInt(totalAll)}
              </span>
            </div>
          </div>
        </header>

        {/* ── Filters (desktop inline + mobile pill/sheet handled inside) ── */}
        <section aria-label="Filters" className="md:mb-6">
          <Filters
            values={filters}
            onChange={setFilters}
            totalShown={totalShown}
            totalAll={totalAll}
            isLoading={search.isLoading}
          />
        </section>

        {/* ── Results count (desktop only — mobile shows it in header + pill) ── */}
        <div className="mb-3 hidden items-center gap-2 md:flex">
          <span className="brutal-border bg-accent px-3 py-1 font-mono text-2xl font-bold text-accent-foreground">
            {search.isLoading ? "…" : formatInt(totalShown)}
          </span>
          <span className="text-sm font-semibold">
            of {formatInt(totalAll)} results
          </span>
        </div>

        {/* ── Results ── */}
        <section className="min-w-0">
          <ResultsTable
            rows={search.data}
            isLoading={search.isLoading}
            isFetching={search.isFetching}
            error={search.error as Error | null}
          />
        </section>

        <footer className="mt-8 text-center text-[11px] uppercase tracking-widest text-muted-foreground">
          Wroclaw Macro Finder &middot; Seasonal menus may not be included
        </footer>
      </div>
    </div>
  );
}
