import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, RotateCcw, Store } from "lucide-react";

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
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { listRestaurants, type SortBy } from "@/api/client";
import { cn } from "@/lib/utils";
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

interface FiltersProps {
  values: FilterValues;
  onChange: (next: FilterValues) => void;
  className?: string;
}

export function Filters({ values, onChange, className }: FiltersProps) {
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

  const update = <K extends keyof FilterValues>(key: K, val: FilterValues[K]) =>
    onChange({ ...values, [key]: val });

  return (
    <div className={cn("space-y-3", className)}>
      {/* Filter boxes */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 md:gap-3">
        <FilterBox label="Max Kcal">
          <NumberWithSlider
            suffix="kcal"
            min={100}
            max={2500}
            step={25}
            value={values.maxKcal}
            onChange={(v) => update("maxKcal", v)}
          />
        </FilterBox>

        <FilterBox label="Min Protein">
          <NumberWithSlider
            suffix="g"
            min={5}
            max={120}
            step={1}
            value={values.minProtein}
            onChange={(v) => update("minProtein", v)}
          />
        </FilterBox>

        <FilterBox label="Restaurant">
          <RestaurantPicker
            restaurants={restaurants}
            loading={restaurantsQuery.isLoading}
            selected={selectedRestaurant}
            onSelect={(id) => update("restaurantId", id)}
          />
        </FilterBox>
      </div>

      {/* Sort bar + controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="brutal-border brutal-shadow flex flex-wrap overflow-hidden">
          {(
            [
              ["protein_ratio_desc", "Protein Ratio"],
              ["protein_desc", "Most Protein"],
              ["kcal_asc", "Kcal \u2191"],
              ["kcal_desc", "Kcal \u2193"],
            ] as const
          ).map(([val, label]) => (
            <button
              key={val}
              onClick={() => update("sortBy", val)}
              className={cn(
                "border-r border-border px-3 py-2 text-[11px] font-bold uppercase tracking-wide transition-colors last:border-r-0 md:px-4 md:text-xs",
                values.sortBy === val
                  ? "bg-foreground text-primary"
                  : "bg-card text-muted-foreground hover:bg-muted",
              )}
            >
              {label}
            </button>
          ))}
        </div>

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
    </div>
  );
}

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
}: {
  suffix: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (next: number) => void;
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
    <div className="flex items-center gap-2">
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={([v]) => v !== undefined && onChange(v)}
        className="min-w-0 flex-1"
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
          className="brutal-border h-7 w-14 bg-background px-1.5 text-right font-mono text-sm font-bold outline-none focus:border-primary md:w-16"
        />
        <span className="text-[10px] font-bold text-muted-foreground">
          {suffix}
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
          <CommandInput placeholder={loading ? "Loading\u2026" : "Search\u2026"} />
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
