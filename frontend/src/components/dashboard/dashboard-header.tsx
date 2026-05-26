import { Activity, AlertTriangle, DatabaseZap } from "lucide-react";

import type { HealthResponse } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

interface DashboardHeaderProps {
  health: HealthResponse;
  error: string | null;
  isLoading: boolean;
}

export function DashboardHeader({
  health,
  error,
  isLoading,
}: DashboardHeaderProps) {
  const badgeVariant =
    isLoading && health.status === "unknown"
      ? "outline"
      : health.status === "ok"
        ? "secondary"
        : "destructive";

  const badgeLabel =
    isLoading && health.status === "unknown"
      ? "Đang kiểm tra backend"
      : health.status === "ok"
        ? "Backend ổn định"
        : "Backend có vấn đề";

  return (
    <header className="relative overflow-hidden rounded-[2rem] border border-white/60 bg-white/80 px-6 py-6 shadow-[0_30px_90px_-48px_rgba(15,118,110,0.45)] backdrop-blur sm:px-8 sm:py-8">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl space-y-4">
          <Badge variant="outline" className="bg-background/75 text-muted-foreground">
            <DatabaseZap className="size-3.5" />
            Lớp serving Kappa chỉ đọc
          </Badge>
          <div className="space-y-3">
            <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              Bảng điều khiển YouTube Analytics
            </h1>
            
          </div>
        </div>

        <div className="grid gap-3 sm:min-w-72">
          <div className="flex items-center justify-between rounded-2xl border bg-card/90 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/10 p-2 text-primary">
                {health.status === "ok" ? (
                  <Activity className="size-4" />
                ) : (
                  <AlertTriangle className="size-4" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  Trạng thái Serving API
                </p>
                <p className="text-xs text-muted-foreground">
                  `/health` được proxy qua Next.js
                </p>
              </div>
            </div>
            <Badge variant={badgeVariant}>{badgeLabel}</Badge>
          </div>

          <div className="rounded-2xl border bg-card/85 px-4 py-3 text-sm">
            <p className="font-medium text-foreground">Lần kiểm tra gần nhất</p>
            <p className="mt-1 text-muted-foreground">
              {formatTimestamp(health.freshness?.checked_at)}
            </p>
            {error ? (
              <p className="mt-2 text-xs text-destructive">{error}</p>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
