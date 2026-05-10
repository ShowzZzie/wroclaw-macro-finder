import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  ChevronsUpDown,
  ChevronUp,
  RotateCcw,
  Store,
  X,
} from "lucide-react";

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { listRestaurants, type SortBy } from "@/api/client";
import { cn, formatInt } from "@/lib/utils";
import { RestaurantBadge } from "@/components/RestaurantBadge";
import { ThemeToggle } from "@/components/ThemeToggle";

export interface FilterValues {
  maxKcal: number;
  minProtein: number;
  restaurantId: number | null;
  lowKcalIncluded: boolean;
  sortBy: SortBy;
}

export const DEFAULT_FILTERS: FilterValues = {
  maxKcal: 800,
  minProtein: 30,
  restaurantId: null,
  lowKcalIncluded: false,
  sortBy: "protein_ratio_desc",
};

interface SortOption {
  value: SortBy;
  short: string;
  label: string;
  description: string;
}

const SORT_OPTIONS: ReadonlyArray<SortOption> = [
  {
    value: "protein_ratio_desc",
    short: "P/100kcal",
    label: "Protein per 100 kcal",
    description: "Most protein-dense first",
  },
  {
    value: "protein_desc",
    short: "Protein",
    label: "Protein in portion",
    description: "Most total protein first",
  },
  {
    value: "kcal_asc",
    short: "Kcal ↑",
    label: "Kcal ascending",
    description: "Lowest calorie first",
  },
  {
    value: "kcal_desc",
    short: "Kcal ↓",
    label: "Kcal descending",
    description: "Highest calorie first",
  },
];

interface FiltersProps {
  values: FilterValues;
  onChange: (next: FilterValues) => void;
  totalShown: number;
  totalAll: number;
  isLoading: boolean;
  className?: string;
}

export function Filters({
  values,
  onChange,
  totalShown,
  totalAll,
  isLoading,
  className,
}: FiltersProps) {
  const restaurantsQuery = useQuery({
    queryKey: ["restaurants"],
    queryFn: ({ signal }) => listRestaurants(signal),
    staleTime: 5 * 60_000,
  });

  const restaurants = restaurantsQuery.data ?? [];
  const selectedRestaurant = useMemo(
    () => restaurants.find((r) => r.id === values.restaurantId) ?? null,
    [restaurants, values.restaurantId],
  );

  const activeSort = SORT_OPTIONS.find((o) => o.value === values.sortBy)!;

  return (
    <>
      {/* ── Desktop / tablet inline ── */}
      <div className={cn("hidden md:block", className)}>
        <FilterControls
          values={values}
          onChange={onChange}
          restaurants={restaurants}
          restaurantsLoading={restaurantsQuery.isLoading}
          selectedRestaurant={selectedRestaurant}
          activeSort={activeSort}
          variant="inline"
        />
      </div>

      {/* ── Mobile bottom-sheet pill ── */}
      <MobileFilterDock
        values={values}
        onChange={onChange}
        restaurants={restaurants}
        restaurantsLoading={restaurantsQuery.isLoading}
        selectedRestaurant={selectedRestaurant}
        activeSort={activeSort}
        totalShown={totalShown}
        totalAll={totalAll}
        isLoading={isLoading}
      />
    </>
  );
}

/* ─────────────────────────────────────────────────────────────
 *  Mobile bottom-sheet dock
 * ───────────────────────────────────────────────────────────── */

interface DockProps {
  values: FilterValues;
  onChange: (next: FilterValues) => void;
  restaurants: { id: number; name: string }[];
  restaurantsLoading: boolean;
  selectedRestaurant: { id: number; name: string } | null;
  activeSort: SortOption;
  totalShown: number;
  totalAll: number;
  isLoading: boolean;
}

function MobileFilterDock({
  values,
  onChange,
  restaurants,
  restaurantsLoading,
  selectedRestaurant,
  activeSort,
  totalShown,
  totalAll,
  isLoading,
}: DockProps) {
  const [open, setOpen] = useState(false);

  const summaryBits = useMemo(() => {
    const bits: string[] = [];
    bits.push(values.maxKcal === 0 ? "no kcal cap" : `≤${values.maxKcal}`);
    bits.push(
      values.minProtein === 0 ? "any protein" : `≥${values.minProtein}g`,
    );
    bits.push(selectedRestaurant?.name ?? "all");
    return bits;
  }, [values.maxKcal, values.minProtein, selectedRestaurant]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          aria-label="Open filters"
          className={cn(
            "md:hidden",
            "fixed inset-x-0 bottom-0 z-40",
            "flex w-full items-center gap-2.5",
            "border-t-[3px] border-border bg-foreground px-4 py-3",
            "pb-[calc(env(safe-area-inset-bottom)+0.75rem)]",
            "text-primary",
            "shadow-[0_-4px_0_0_hsl(var(--accent))]",
          )}
        >
          <ChevronUp className="h-5 w-5 shrink-0" />
          <span className="flex min-w-0 flex-1 items-baseline gap-1.5 truncate text-left">
            <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-primary">
              Filters
            </span>
            <span
              className="truncate font-mono text-xs font-semibold text-primary/70"
              aria-hidden
            >
              {summaryBits.join(" · ")}
            </span>
          </span>
          <span
            className={cn(
              "brutal-border ml-auto bg-accent px-2 py-0.5",
              "font-mono text-sm font-bold tabular-nums text-accent-foreground",
            )}
          >
            {isLoading ? "…" : formatInt(totalShown)}
          </span>
        </button>
      </SheetTrigger>

      <SheetContent
        side="bottom"
        className={cn(
          "border-t-[3px] border-border bg-card p-0",
          "rounded-t-none",
          "shadow-[0_-6px_0_0_hsl(var(--primary)),0_-9px_0_0_hsl(var(--border))]",
          "max-h-[92vh] overflow-y-auto",
          "[&>button]:hidden", // hide default close, we render our own
        )}
      >
        <SheetTitle className="sr-only">Filters and sort</SheetTitle>

        {/* drag handle */}
        <div className="sticky top-0 z-10 flex flex-col bg-card pt-2">
          <div
            aria-hidden
            className="mx-auto h-1 w-12 rounded-full bg-foreground/80"
          />
          <div className="mt-2 flex items-center justify-between border-b-2 border-border px-5 pb-2.5">
            <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Filters
            </span>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close filters"
              className="brutal-border flex h-7 w-7 items-center justify-center bg-card hover:bg-muted"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="px-4 pb-5 pt-4">
          <FilterControls
            values={values}
            onChange={onChange}
            restaurants={restaurants}
            restaurantsLoading={restaurantsLoading}
            selectedRestaurant={selectedRestaurant}
            activeSort={activeSort}
            variant="sheet"
          />
        </div>

        {/* Sticky footer apply */}
        <div
          className={cn(
            "sticky bottom-0 z-10",
            "border-t-[3px] border-border bg-card",
            "px-4 py-3",
            "pb-[calc(env(safe-area-inset-bottom)+0.75rem)]",
          )}
        >
          <button
            onClick={() => setOpen(false)}
            className={cn(
              "brutal-border w-full bg-foreground py-3.5 text-primary",
              "text-sm font-bold uppercase tracking-[0.18em]",
              "shadow-[4px_4px_0_hsl(var(--accent))]",
              "active:translate-x-0.5 active:translate-y-0.5",
              "active:shadow-[2px_2px_0_hsl(var(--accent))]",
              "transition-[transform,box-shadow] duration-100",
            )}
          >
            {isLoading ? (
              <>Loading…</>
            ) : (
              <>
                Show{" "}
                <span className="font-mono">{formatInt(totalShown)}</span>{" "}
                of <span className="font-mono">{formatInt(totalAll)}</span>{" "}
                results
              </>
            )}
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

/* ─────────────────────────────────────────────────────────────
 *  Shared filter controls (used inline + in sheet)
 * ───────────────────────────────────────────────────────────── */

interface FilterControlsProps {
  values: FilterValues;
  onChange: (next: FilterValues) => void;
  restaurants: { id: number; name: string }[];
  restaurantsLoading: boolean;
  selectedRestaurant: { id: number; name: string } | null;
  activeSort: SortOption;
  variant: "inline" | "sheet";
}

function FilterControls({
  values,
  onChange,
  restaurants,
  restaurantsLoading,
  selectedRestaurant,
  activeSort,
  variant,
}: FilterControlsProps) {
  const update = <K extends keyof FilterValues>(
    key: K,
    val: FilterValues[K],
  ) => onChange({ ...values, [key]: val });

  if (variant === "sheet") {
    return (
      <div className="space-y-5">
        {/* Sliders — stacked, full width */}
        <div className="space-y-3">
          <FilterBox label="Max Kcal">
            <NumberWithSlider
              suffix="kcal"
              min={0}
              max={2500}
              step={25}
              value={values.maxKcal}
              onChange={(v) => update("maxKcal", v)}
              size="lg"
            />
          </FilterBox>

          <FilterBox label="Min Protein">
            <NumberWithSlider
              suffix="g"
              min={0}
              max={120}
              step={1}
              value={values.minProtein}
              onChange={(v) => update("minProtein", v)}
              size="lg"
            />
          </FilterBox>

          <FilterBox label="Restaurant">
            <RestaurantPicker
              restaurants={restaurants}
              loading={restaurantsLoading}
              selected={selectedRestaurant}
              onSelect={(id) => update("restaurantId", id)}
            />
          </FilterBox>
        </div>

        {/* Sort — vertical list with descriptions */}
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Sort by
            </span>
            <span className="text-[10px] font-medium text-muted-foreground">
              tap to switch
            </span>
          </div>
          <SortPickerList
            value={values.sortBy}
            onChange={(v) => update("sortBy", v)}
          />
        </div>

        {/* Add-ons + Reset + Theme */}
        <div className="space-y-2">
          <label className="brutal-border flex cursor-pointer items-center justify-between gap-3 bg-card px-3 py-3 select-none">
            <span className="flex flex-col">
              <span className="text-xs font-bold uppercase tracking-wide">
                Include add-ons
              </span>
              <span className="text-[11px] text-muted-foreground">
                items &le; 150 kcal
              </span>
            </span>
            <Switch
              checked={values.lowKcalIncluded}
              onCheckedChange={(v) => update("lowKcalIncluded", v)}
              aria-label="Include low-kcal add-ons"
            />
          </label>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onChange(DEFAULT_FILTERS)}
              className={cn(
                "brutal-border flex flex-1 items-center justify-center gap-2",
                "bg-card px-3 py-2.5 text-xs font-bold uppercase tracking-wide",
                "hover:bg-muted",
              )}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset filters
            </button>
            <ThemeToggle />
          </div>
        </div>
      </div>
    );
  }

  /* ── Inline (desktop) variant ── */
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 md:gap-3">
        <FilterBox label="Max Kcal">
          <NumberWithSlider
            suffix="kcal"
            min={0}
            max={2500}
            step={25}
            value={values.maxKcal}
            onChange={(v) => update("maxKcal", v)}
          />
        </FilterBox>

        <FilterBox label="Min Protein">
          <NumberWithSlider
            suffix="g"
            min={0}
            max={120}
            step={1}
            value={values.minProtein}
            onChange={(v) => update("minProtein", v)}
          />
        </FilterBox>

        <FilterBox label="Restaurant">
          <RestaurantPicker
            restaurants={restaurants}
            loading={restaurantsLoading}
            selected={selectedRestaurant}
            onSelect={(id) => update("restaurantId", id)}
          />
        </FilterBox>
      </div>

      {/* Sort + controls */}
      <div className="flex flex-wrap items-center gap-3">
        <SortPickerSegmented
          value={values.sortBy}
          onChange={(v) => update("sortBy", v)}
        />

        <label className="flex cursor-pointer items-center gap-2 select-none">
          <Switch
            checked={values.lowKcalIncluded}
            onCheckedChange={(v) => update("lowKcalIncluded", v)}
            aria-label="Include low-kcal add-ons"
          />
          <span className="text-xs font-semibold">
            Add-ons{" "}
            <span className="text-muted-foreground">&le;150 kcal</span>
          </span>
        </label>

        <Button
          variant="ghost"
          size="sm"
          className="ml-1 text-muted-foreground hover:text-foreground"
          onClick={() => onChange(DEFAULT_FILTERS)}
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Reset
        </Button>

        <ThemeToggle />
      </div>

      {/* Active-sort explainer — keeps the segmented bar unambiguous */}
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
        <span className="font-bold uppercase tracking-wider">Sorted by</span>
        <span className="font-bold text-foreground">{activeSort.label}</span>
        <span aria-hidden>&middot;</span>
        <span>{activeSort.description}</span>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
 *  Sort pickers — two layouts, same data
 * ───────────────────────────────────────────────────────────── */

function SortPickerSegmented({
  value,
  onChange,
}: {
  value: SortBy;
  onChange: (v: SortBy) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Sort by"
      className="brutal-border brutal-shadow flex flex-wrap overflow-hidden"
    >
      {SORT_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          role="radio"
          aria-checked={value === opt.value}
          onClick={() => onChange(opt.value)}
          title={`${opt.label} — ${opt.description}`}
          className={cn(
            "border-r border-border px-3 py-2 text-[11px] font-bold uppercase tracking-wide transition-colors last:border-r-0 md:px-4 md:text-xs",
            value === opt.value
              ? "bg-foreground text-primary"
              : "bg-card text-muted-foreground hover:bg-muted",
          )}
        >
          {opt.short}
        </button>
      ))}
    </div>
  );
}

function SortPickerList({
  value,
  onChange,
}: {
  value: SortBy;
  onChange: (v: SortBy) => void;
}) {
  return (
    <div role="radiogroup" aria-label="Sort by" className="space-y-1.5">
      {SORT_OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "brutal-border flex w-full items-center gap-3 px-3.5 py-3 text-left transition-colors",
              active
                ? "bg-foreground text-primary brutal-shadow"
                : "bg-card text-foreground hover:bg-muted",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center border-[2.5px] border-primary",
                active ? "bg-primary" : "bg-transparent",
              )}
            >
              {active ? (
                <Check className="h-3 w-3 text-foreground" strokeWidth={3.5} />
              ) : null}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-bold uppercase tracking-wide">
                {opt.label}
              </span>
              <span
                className={cn(
                  "block text-[11px] font-medium",
                  active ? "text-primary/75" : "text-muted-foreground",
                )}
              >
                {opt.description}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
 *  Sub-components (preserved from earlier)
 * ───────────────────────────────────────────────────────────── */

function FilterBox({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="brutal-border brutal-shadow space-y-1.5 bg-card p-3">
      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}

function NumberWithSlider({
  suffix,
  min,
  max,
  step,
  value,
  onChange,
  size = "md",
}: {
  suffix: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (next: number) => void;
  size?: "md" | "lg";
}) {
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const commit = (raw: string) => {
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
      setDraft(String(value));
      return;
    }
    const clamped = Math.max(min, Math.min(max, Math.round(parsed)));
    onChange(clamped);
    setDraft(String(clamped));
  };

  return (
    <div
      className={cn(
        "flex items-center gap-2",
        size === "lg" && "gap-3",
      )}
    >
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={([v]) => v !== undefined && onChange(v)}
        className={cn("min-w-0 flex-1", size === "lg" && "py-1")}
      />
      <div className="flex items-baseline gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={(e) => commit(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              (e.target as HTMLInputElement).blur();
            }
          }}
          inputMode="numeric"
          className={cn(
            "brutal-border bg-background text-right font-mono font-bold outline-none focus:border-primary",
            size === "lg"
              ? "h-9 w-20 px-2 text-base"
              : "h-7 w-14 px-1.5 text-sm md:w-16",
            value === 0 && "text-muted-foreground",
          )}
        />
        <span
          className={cn(
            "font-bold uppercase tracking-wider",
            size === "lg" ? "text-xs" : "text-[10px]",
            value === 0 ? "text-accent" : "text-muted-foreground",
          )}
        >
          {value === 0 ? "off" : suffix}
        </span>
      </div>
    </div>
  );
}

function RestaurantPicker({
  restaurants,
  loading,
  selected,
  onSelect,
}: {
  restaurants: { id: number; name: string }[];
  loading: boolean;
  selected: { id: number; name: string } | null;
  onSelect: (id: number | null) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="brutal-border w-full justify-between font-normal"
        >
          <span className="flex min-w-0 items-center gap-2 truncate">
            {selected ? (
              <RestaurantBadge name={selected.name} size="sm" />
            ) : (
              <>
                <Store className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">All</span>
              </>
            )}
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[var(--radix-popover-trigger-width)] min-w-[260px] p-0"
        align="start"
      >
        <Command>
          <CommandInput placeholder={loading ? "Loading…" : "Search…"} />
          <CommandList>
            <CommandEmpty>No restaurant found.</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="__all__"
                onSelect={() => {
                  onSelect(null);
                  setOpen(false);
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    selected === null ? "opacity-100" : "opacity-0",
                  )}
                />
                <span className="text-muted-foreground">All restaurants</span>
              </CommandItem>
              {restaurants.map((r) => (
                <CommandItem
                  key={r.id}
                  value={r.name}
                  onSelect={() => {
                    onSelect(r.id);
                    setOpen(false);
                  }}
                  className="gap-2"
                >
                  <Check
                    className={cn(
                      "h-4 w-4",
                      selected?.id === r.id ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <RestaurantBadge name={r.name} size="sm" />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
