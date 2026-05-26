"use client";

import { RefreshCcw } from "lucide-react";

import {
  LIMIT_OPTIONS,
  WINDOW_OPTIONS,
  type LimitOption,
  type WindowOption,
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
  isRefreshing: boolean;
  limit: LimitOption;
  onLimitChange: (value: LimitOption) => void;
  onRefresh: () => void;
  onWindowChange: (value: WindowOption) => void;
  windowMinutes: WindowOption;
}

export function DashboardFilters({
  isRefreshing,
  limit,
  onLimitChange,
  onRefresh,
  onWindowChange,
  windowMinutes,
}: DashboardFiltersProps) {
  return (
    <section className="rounded-[1.75rem] border bg-white/85 p-4 shadow-[0_20px_70px_-55px_rgba(15,23,42,0.45)] backdrop-blur">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Time window</p>
            <Select
              value={String(windowMinutes)}
              onValueChange={(value) => onWindowChange(Number(value) as WindowOption)}
            >
              <SelectTrigger className="w-full min-w-40 bg-background">
                <SelectValue placeholder="Select a window" />
              </SelectTrigger>
              <SelectContent>
                {WINDOW_OPTIONS.map((option) => (
                  <SelectItem key={option} value={String(option)}>
                    {option} minutes
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Top N</p>
            <Select
              value={String(limit)}
              onValueChange={(value) => onLimitChange(Number(value) as LimitOption)}
            >
              <SelectTrigger className="w-full min-w-32 bg-background">
                <SelectValue placeholder="Select a limit" />
              </SelectTrigger>
              <SelectContent>
                {LIMIT_OPTIONS.map((option) => (
                  <SelectItem key={option} value={String(option)}>
                    {option} rows
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button
          className="w-full sm:w-auto"
          disabled={isRefreshing}
          onClick={onRefresh}
        >
          <RefreshCcw
            className={isRefreshing ? "size-4 animate-spin" : "size-4"}
          />
          Refresh data
        </Button>
      </div>
    </section>
  );
}
