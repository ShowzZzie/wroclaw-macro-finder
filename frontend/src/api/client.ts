export type SortBy =
  | "protein_ratio_desc"
  | "protein_desc"
  | "kcal_asc"
  | "kcal_desc";

export interface FoodSearchResult {
  restaurant_name: string;
  food_name: string;
  size: string | null;
  kcal: number;
  protein: number;
  fats: number;
  carbs: number;
  protein_per_100_kcal: number;
}

export interface Restaurant {
  id: number;
  name: string;
}

export interface SearchParams {
  max_kcal: number;
  min_protein: number;
  restaurant_id?: number | null;
  low_kcal_included?: boolean;
  sort_by?: SortBy;
}

// ── Raw shape coming from the static JSON ──────────────────────
interface RawFood {
  restaurant_name: string;
  food_name: string;
  size: string | null;
  kcal: number;
  protein: number;
  fats: number;
  carbs: number;
}

// ── Singleton data cache (stale-while-revalidate) ─────────────
const LS_KEY = "wmf-foods-cache";
let _cache: RawFood[] | null = null;

async function fetchFresh(): Promise<RawFood[]> {
  const res = await fetch("/data/foods.json");
  if (!res.ok) throw new Error(`Failed to load data (${res.status})`);
  const data = (await res.json()) as RawFood[];
  _cache = data;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch {
    // quota exceeded — silently ignore
  }
  return data;
}

async function loadFoods(signal?: AbortSignal): Promise<RawFood[]> {
  if (_cache) return _cache;

  // Try localStorage for instant reload
  try {
    const stored = localStorage.getItem(LS_KEY);
    if (stored) {
      _cache = JSON.parse(stored) as RawFood[];
      // Background refresh for next visit
      fetchFresh();
      return _cache;
    }
  } catch {
    // parse error — fall through to network
  }

  // No cache at all — fetch from network (skeleton will show)
  const res = await fetch("/data/foods.json", { signal });
  if (!res.ok) throw new Error(`Failed to load data (${res.status})`);
  const data = (await res.json()) as RawFood[];
  _cache = data;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch {
    // quota exceeded
  }
  return data;
}

function proteinPer100(kcal: number, protein: number): number {
  return kcal > 0 ? (protein / kcal) * 100 : 0;
}

// ── Public API (same signatures the UI already calls) ──────────

export async function searchFoods(
  params: SearchParams,
  signal?: AbortSignal,
): Promise<FoodSearchResult[]> {
  const foods = await loadFoods(signal);

  // Filter — 0 means "off" for the kcal cap (protein >= 0 is naturally a no-op)
  const kcalCap = params.max_kcal > 0 ? params.max_kcal : Infinity;
  let filtered = foods.filter(
    (f) => f.kcal <= kcalCap && f.protein >= params.min_protein,
  );

  if (!params.low_kcal_included) {
    filtered = filtered.filter((f) => f.kcal > 150);
  }

  if (params.restaurant_id != null) {
    // restaurant_id in the new model is index-based from the
    // unique sorted restaurant list the UI builds.
    const restaurants = uniqueRestaurants(foods);
    const name = restaurants[params.restaurant_id - 1]?.name;
    if (name) {
      filtered = filtered.filter((f) => f.restaurant_name === name);
    }
  }

  // Sort
  const sortBy = params.sort_by ?? "protein_ratio_desc";
  switch (sortBy) {
    case "protein_desc":
      filtered.sort((a, b) => b.protein - a.protein);
      break;
    case "kcal_asc":
      filtered.sort((a, b) => a.kcal - b.kcal);
      break;
    case "kcal_desc":
      filtered.sort((a, b) => b.kcal - a.kcal);
      break;
    default: // protein_ratio_desc
      filtered.sort(
        (a, b) =>
          proteinPer100(b.kcal, b.protein) -
          proteinPer100(a.kcal, a.protein),
      );
  }

  return filtered.map((f) => ({
    ...f,
    protein_per_100_kcal: Math.round(proteinPer100(f.kcal, f.protein) * 100) / 100,
  }));
}

function uniqueRestaurants(foods: RawFood[]): Restaurant[] {
  const names = [...new Set(foods.map((f) => f.restaurant_name))].sort();
  return names.map((name, i) => ({ id: i + 1, name }));
}

export async function countAllFoods(signal?: AbortSignal): Promise<number> {
  const foods = await loadFoods(signal);
  return foods.length;
}

export async function listRestaurants(
  signal?: AbortSignal,
): Promise<Restaurant[]> {
  const foods = await loadFoods(signal);
  return uniqueRestaurants(foods);
}
