import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { searchFoods } from "@/api/client";
import {
  DEFAULT_FILTERS,
  Filters,
  type FilterValues,
} from "@/components/Filters";
import { ResultsTable } from "@/components/ResultsTable";
import { ThemeToggle } from "@/components/ThemeToggle";
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
          limit: effectiveFilters.limit,
          sort_by: effectiveFilters.sortBy,
        },
        signal,
      ),
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (search.error) {
      toast.error("Search failed", {
        description: (search.error as Error).message,
      });
    }
  }, [search.error]);

  const totalShown = search.data?.length ?? 0;

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <div className="container py-6 md:py-8">
        {/* ── Header ── */}
        <header className="brutal-border brutal-shadow mb-4 bg-primary px-5 py-5 md:mb-6 md:px-7 md:py-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold uppercase tracking-tight md:text-[32px]">
                Wroclaw Macro Finder
              </h1>
              <p className="mt-0.5 text-sm font-medium md:text-base">
                High-protein menu items, fast.
              </p>
            </div>
            <ThemeToggle />
          </div>
        </header>

        {/* ── Filters ── */}
        <section aria-label="Filters" className="mb-4 md:mb-6">
          <Filters values={filters} onChange={setFilters} />
        </section>

        {/* ── Sort bar ── */}
        {/* (Sort is inside Filters) */}

        {/* ── Results count ── */}
        <div className="mb-3 flex items-center gap-2">
          <span className="brutal-border bg-accent px-3 py-1 font-mono text-2xl font-bold text-accent-foreground">
            {search.isLoading ? "…" : formatInt(totalShown)}
          </span>
          <span className="text-sm font-semibold">items found</span>
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
          Wroclaw Macro Finder &middot; Data may not reflect current menus
        </footer>
      </div>
    </div>
  );
}
