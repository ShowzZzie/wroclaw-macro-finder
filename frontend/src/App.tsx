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
      <div className="container py-6 md:py-8">
        {/* ── Header ── */}
        <header className="brutal-border brutal-shadow mb-4 bg-primary px-5 py-5 md:mb-6 md:px-7 md:py-6">
          <h1 className="text-2xl font-bold uppercase tracking-tight md:text-[32px]">
            Wroclaw Macro Finder
          </h1>
          <p className="mt-0.5 text-sm font-medium md:text-base">
            High-protein menu items, fast.
          </p>
        </header>

        {/* ── Filters ── */}
        <section
          aria-label="Filters"
          className="sticky top-0 z-40 -mx-4 border-b-2 border-border bg-background px-4 pb-2 pt-2 md:static md:mx-0 md:border-b-0 md:p-0 md:mb-6"
        >
          <Filters values={filters} onChange={setFilters} />
        </section>

        {/* ── Sort bar ── */}
        {/* (Sort is inside Filters) */}

        {/* ── Results count ── */}
        <div className="mb-3 flex items-center gap-2">
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
