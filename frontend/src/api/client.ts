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
  menu_link?: string | null;
  macro_table_link?: string | null;
}

export interface SearchParams {
  max_kcal: number;
  min_protein: number;
  restaurant_id?: number | null;
  low_kcal_included?: boolean;
  limit?: number;
  sort_by?: SortBy;
}

class ApiError extends Error {
  status: number;
  detail?: unknown;
  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { Accept: "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text().catch(() => undefined);
    }
    const message =
      typeof detail === "object" && detail && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Request failed (${res.status})`;
    throw new ApiError(message, res.status, detail);
  }
  return (await res.json()) as T;
}

export async function searchFoods(
  params: SearchParams,
  signal?: AbortSignal,
): Promise<FoodSearchResult[]> {
  const search = new URLSearchParams();
  search.set("max_kcal", String(params.max_kcal));
  search.set("min_protein", String(params.min_protein));
  if (params.restaurant_id != null) {
    search.set("restaurant_id", String(params.restaurant_id));
  }
  if (params.low_kcal_included !== undefined) {
    search.set("low_kcal_included", params.low_kcal_included ? "true" : "false");
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  if (params.sort_by) {
    search.set("sort_by", params.sort_by);
  }
  return request<FoodSearchResult[]>(`/api/foods/search?${search.toString()}`, {
    signal,
  });
}

export async function listRestaurants(
  signal?: AbortSignal,
): Promise<Restaurant[]> {
  return request<Restaurant[]>("/api/restaurants", { signal });
}

export { ApiError };
