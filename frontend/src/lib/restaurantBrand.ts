/**
 * Per-restaurant visual identity. Hand-curated for the known set so the
 * monograms feel close to the real brand; unknown chains fall back to a
 * deterministic-from-name color so they're still recognizable at a glance.
 */
export interface BrandIdentity {
  monogram: string;
  bg: string;
  fg: string;
  ring?: string;
}

const KNOWN: Record<string, BrandIdentity> = {
  hulthai: {
    monogram: "HT",
    bg: "linear-gradient(135deg, #f97316, #b45309)",
    fg: "#fff7ed",
  },
  kfc: {
    monogram: "KFC",
    bg: "#e4002b",
    fg: "#ffffff",
  },
  luca: {
    monogram: "L",
    bg: "linear-gradient(135deg, #1f2937, #0f172a)",
    fg: "#f5f5f4",
    ring: "rgba(245, 245, 244, 0.18)",
  },
  "max burgers": {
    monogram: "MAX",
    bg: "#fbbf24",
    fg: "#1c1917",
  },
  "mcdonald's": {
    monogram: "M",
    bg: "#da291c",
    fg: "#ffc72c",
  },
  mcdonalds: {
    monogram: "M",
    bg: "#da291c",
    fg: "#ffc72c",
  },
  "pan precel": {
    monogram: "PP",
    bg: "linear-gradient(135deg, #b45309, #78350f)",
    fg: "#fef3c7",
  },
  pasibus: {
    monogram: "Pa",
    bg: "#111111",
    fg: "#ffffff",
    ring: "rgba(255,255,255,0.18)",
  },
  "pizza hut": {
    monogram: "PH",
    bg: "#ee3124",
    fg: "#ffffff",
  },
  pizzatopia: {
    monogram: "Pz",
    bg: "linear-gradient(135deg, #16a34a, #166534)",
    fg: "#f0fdf4",
  },
  "popeye's": {
    monogram: "Po",
    bg: "#ff7a00",
    fg: "#1c1917",
  },
  popeyes: {
    monogram: "Po",
    bg: "#ff7a00",
    fg: "#1c1917",
  },
  "salad story": {
    monogram: "SS",
    bg: "linear-gradient(135deg, #65a30d, #3f6212)",
    fg: "#f7fee7",
  },
  "shrimp house": {
    monogram: "SH",
    bg: "linear-gradient(135deg, #f43f5e, #be123c)",
    fg: "#fff1f2",
  },
  subway: {
    monogram: "Sub",
    bg: "#008c44",
    fg: "#ffd400",
  },
  "sushi corner": {
    monogram: "鮨",
    bg: "linear-gradient(135deg, #1f2937, #4b5563)",
    fg: "#fef2f2",
  },
  "wrap me!": {
    monogram: "Wm",
    bg: "linear-gradient(135deg, #f59e0b, #ea580c)",
    fg: "#fffbeb",
  },
  "zahir kebab": {
    monogram: "ZK",
    bg: "linear-gradient(135deg, #b91c1c, #7c2d12)",
    fg: "#fef2f2",
  },
};

/* Fallback palette for chains we don't recognise yet. */
const FALLBACK_PALETTE: ReadonlyArray<{ bg: string; fg: string }> = [
  { bg: "#0ea5e9", fg: "#f0f9ff" },
  { bg: "#a855f7", fg: "#faf5ff" },
  { bg: "#14b8a6", fg: "#f0fdfa" },
  { bg: "#f59e0b", fg: "#1c1917" },
  { bg: "#ef4444", fg: "#fff1f2" },
  { bg: "#3b82f6", fg: "#eff6ff" },
  { bg: "#84cc16", fg: "#1a2e05" },
  { bg: "#ec4899", fg: "#fdf2f8" },
];

/**
 * Per-name overrides for cases where the menu_link domain points at a
 * subdomain or aggregator (e.g. amrest CDN) that doesn't host a clean logo.
 */
const DOMAIN_OVERRIDES: Record<string, string> = {
  kfc: "kfc.pl",
  "pizza hut": "pizzahut.pl",
  "mcdonald's": "mcdonalds.pl",
  mcdonalds: "mcdonalds.pl",
  "popeye's": "popeyeschicken.pl",
  popeyes: "popeyeschicken.pl",
  pasibus: "pasibus.pl",
  // pizzatopia — see comment above
  "shrimp house": "shrimp-house.pl",
  hulthai: "hulthai.pl",
  luca: "lucabakery.pl",
  "max burgers": "maxpremiumburgers.pl",
  "pan precel": "panprecel.pl",
  // "salad story" — S2 favicon is a generic placeholder; use monogram instead
  // "pizzatopia" — S2 favicon is a generic placeholder; use monogram instead
  subway: "subway.com",
  "sushi corner": "sushicorner.pl",
  "wrap me!": "wrapme.pl",
  "zahir kebab": "zahirkebab.pl",
};

/**
 * Resolve a logo URL for a restaurant via hand-curated domain
 * overrides → Google S2 favicon (sz=128). Returns null (monogram
 * fallback) for chains without a clean favicon.
 */
export function getLogoUrl(name: string): string | null {
  const key = name.trim().toLowerCase();
  const host = DOMAIN_OVERRIDES[key];
  if (!host) return null;
  return `https://www.google.com/s2/favicons?sz=128&domain=${encodeURIComponent(host)}`;
}

function hashName(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function deriveMonogram(name: string): string {
  const cleaned = name.replace(/[^\p{L}\p{N}\s]/gu, "").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) {
    return parts[0]!.slice(0, 2).toUpperCase();
  }
  return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
}

export function getBrand(name: string): BrandIdentity {
  const key = name.trim().toLowerCase();
  const known = KNOWN[key];
  if (known) return known;
  const palette = FALLBACK_PALETTE[hashName(key) % FALLBACK_PALETTE.length]!;
  return {
    monogram: deriveMonogram(name),
    bg: palette.bg,
    fg: palette.fg,
  };
}
