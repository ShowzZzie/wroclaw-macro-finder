import { cva, type VariantProps } from "class-variance-authority";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const tile = cva(
  "flex flex-col items-center justify-center border-l border-border text-center first:border-l-0",
  {
    variants: {
      tone: {
        neutral: "bg-red-50 dark:bg-red-950/80",
        protein: "bg-primary",
        fats: "bg-amber-100 dark:bg-amber-950/80",
        carbs: "bg-sky-100 dark:bg-sky-950/80",
        primary:
          "bg-foreground text-primary",
      },
      size: {
        md: "min-w-0 flex-1 py-1.5 md:flex-none md:w-[68px] md:py-2",
        lg: "min-w-0 flex-1 py-2 md:flex-none md:w-[76px] md:py-2.5",
      },
    },
    defaultVariants: { tone: "neutral", size: "md" },
  },
);

const valueText = cva("font-mono font-bold leading-none tabular-nums", {
  variants: {
    size: {
      md: "text-sm md:text-base",
      lg: "text-base md:text-lg",
    },
  },
  defaultVariants: { size: "md" },
});

const valueColor = {
  neutral: "text-rose-600 dark:text-rose-400",
  protein: "text-foreground",
  fats: "text-amber-700 dark:text-amber-300",
  carbs: "text-sky-700 dark:text-sky-300",
  primary: "text-primary",
};

interface StatProps extends VariantProps<typeof tile> {
  label: string;
  value: string;
  unit?: string;
  icon?: ReactNode;
  className?: string;
  title?: string;
}

export function Stat({
  label,
  value,
  unit,
  tone,
  size,
  icon,
  className,
  title,
}: StatProps) {
  const toneKey = tone ?? "neutral";
  return (
    <div className={cn(tile({ tone, size }), className)} title={title}>
      <span className={cn("flex items-baseline gap-0.5", valueColor[toneKey])}>
        <span className={valueText({ size })}>{value}</span>
        {unit ? (
          <span className="text-[9px] font-bold opacity-70">{unit}</span>
        ) : null}
      </span>
      <span className="text-[7px] font-bold uppercase tracking-widest opacity-60 md:text-[8px]">
        {icon}
        {label}
      </span>
    </div>
  );
}
