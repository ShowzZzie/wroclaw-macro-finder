import { useState } from "react";

import { cn } from "@/lib/utils";
import { getBrand, getLogoUrl } from "@/lib/restaurantBrand";

interface RestaurantBadgeProps {
  name: string;
  size?: "sm" | "md" | "lg";
  showName?: boolean;
  className?: string;
}

const sizeMap = {
  sm: { box: "h-7 w-7", text: "text-[10px]", img: "h-[18px] w-[18px]", name: "text-sm" },
  md: { box: "h-9 w-9", text: "text-[11px]", img: "h-[22px] w-[22px]", name: "text-sm" },
  lg: { box: "h-12 w-12", text: "text-sm", img: "h-7 w-7", name: "text-base" },
} as const;

export function RestaurantBadge({
  name,
  size = "md",
  showName = true,
  className,
}: RestaurantBadgeProps) {
  const brand = getBrand(name);
  const sizes = sizeMap[size];
  const [imgFailed, setImgFailed] = useState(false);

  const logoUrl = getLogoUrl(name);
  const showImage = logoUrl && !imgFailed;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span
        aria-hidden
        className={cn(
          "relative inline-flex shrink-0 items-center justify-center overflow-hidden border-2 border-foreground",
          sizes.box,
        )}
        style={{ background: brand.bg }}
      >
        {/* Monogram fallback */}
        <span
          className={cn(
            "absolute inset-0 flex items-center justify-center font-bold uppercase leading-none tracking-wide",
            sizes.text,
          )}
          style={{ color: brand.fg }}
        >
          {brand.monogram}
        </span>

        {/* Logo overlay */}
        {showImage ? (
          <img
            src={logoUrl ?? undefined}
            alt=""
            loading="lazy"
            decoding="async"
            referrerPolicy="no-referrer"
            onError={() => setImgFailed(true)}
            className={cn(
              "relative z-10 object-contain",
              sizes.img,
            )}
          />
        ) : null}
      </span>

      {showName ? (
        <span
          className={cn("truncate font-semibold text-foreground", sizes.name)}
        >
          {name}
        </span>
      ) : null}
    </div>
  );
}
