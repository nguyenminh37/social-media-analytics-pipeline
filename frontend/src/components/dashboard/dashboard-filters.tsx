"use client";

import { RefreshCcw } from "lucide-react";

import {
  HOURS_OPTIONS,
  HOURS_OPTION_LABELS,
  type DashboardFilter,
  type FilterMode,
  type HoursOption,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface DashboardFiltersProps {
  filter: DashboardFilter;
  isRefreshing: boolean;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onFilterModeChange: (value: FilterMode) => void;
  onRefresh: () => void;
  onWindowHoursChange: (value: HoursOption) => void;
}

export function DashboardFilters({
  filter,
  isRefreshing,
  onDateFromChange,
  onDateToChange,
  onFilterModeChange,
  onRefresh,
  onWindowHoursChange,
}: DashboardFiltersProps) {
  const isDateRangeInvalid =
    filter.filterMode === "date_range" &&
    Boolean(filter.dateFrom) &&
    Boolean(filter.dateTo) &&
    filter.dateFrom > filter.dateTo;

  return (
    <section className="rounded-[1.75rem] border bg-white/85 p-4 shadow-[0_20px_70px_-55px_rgba(15,23,42,0.45)] backdrop-blur">
      <div className="flex flex-col gap-4">
        <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr_auto] lg:items-end">
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Filter</p>
            <Select
              value={filter.filterMode}
              onValueChange={(value) => onFilterModeChange(value as FilterMode)}
            >
              <SelectTrigger className="w-full bg-background">
                <SelectValue placeholder="Select filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hours">Last N hours</SelectItem>
                <SelectItem value="date_range">Date range</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {filter.filterMode === "hours" ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">Window</p>
              <Select
                value={String(filter.windowHours)}
                onValueChange={(value) =>
                  onWindowHoursChange(Number(value) as HoursOption)
                }
              >
                <SelectTrigger className="w-full bg-background">
                  <SelectValue placeholder="Select hours" />
                </SelectTrigger>
                <SelectContent>
                  {HOURS_OPTIONS.map((option) => (
                    <SelectItem key={option} value={String(option)}>
                      {HOURS_OPTION_LABELS[option]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-foreground">From</span>
                <input
                  className="w-full rounded-xl border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  onChange={(event) => onDateFromChange(event.target.value)}
                  type="date"
                  value={filter.dateFrom}
                />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-foreground">To</span>
                <input
                  className="w-full rounded-xl border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  onChange={(event) => onDateToChange(event.target.value)}
                  type="date"
                  value={filter.dateTo}
                />
              </label>
            </div>
          )}

          <Button
            className="w-full lg:w-auto"
            disabled={isRefreshing || isDateRangeInvalid}
            onClick={onRefresh}
          >
            <RefreshCcw
              className={isRefreshing ? "size-4 animate-spin" : "size-4"}
            />
            Refresh
          </Button>
        </div>

        {isDateRangeInvalid ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            `From` must be earlier than or equal to `To`.
          </div>
        ) : null}
      </div>
    </section>
  );
}
