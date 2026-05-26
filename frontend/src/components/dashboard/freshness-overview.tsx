import type { ReactNode } from "react";
import { Clock3, TimerReset, Waves } from "lucide-react";

import type { FreshnessResponse } from "@/lib/api";
import {
  formatTimestamp,
  getFreshnessState,
  relativeAgeLabel,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface FreshnessOverviewProps {
  data: FreshnessResponse;
  error: string | null;
  isLoading: boolean;
}

function FreshnessTile({
  icon,
  label,
  subtitle,
  timestamp,
  staleAfterMinutes,
}: {
  icon: ReactNode;
  label: string;
  staleAfterMinutes: number;
  subtitle?: string | null;
  timestamp?: string | null;
}) {
  const freshness = getFreshnessState(timestamp, staleAfterMinutes);

  return (
    <div className="rounded-2xl border bg-background/70 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            <span className="rounded-full bg-primary/10 p-2 text-primary">
              {icon}
            </span>
            {label}
          </div>
          <p className="font-data text-sm text-muted-foreground">
            {formatTimestamp(timestamp)}
          </p>
        </div>
        <Badge variant={freshness.tone}>{freshness.label}</Badge>
      </div>
      <p className="mt-3 text-sm text-foreground">{relativeAgeLabel(timestamp)}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {subtitle || freshness.detail}
      </p>
    </div>
  );
}

export function FreshnessOverview({
  data,
  error,
  isLoading,
}: FreshnessOverviewProps) {
  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Freshness overview</CardTitle>
        <CardDescription>
          Quick read on whether the serving layer is receiving recent YouTube
          pipeline outputs.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between rounded-2xl border bg-background/60 px-4 py-3">
          <div>
            <p className="text-sm font-medium text-foreground">Checked at</p>
            <p className="font-data text-sm text-muted-foreground">
              {formatTimestamp(data.checked_at)}
            </p>
          </div>
          {error ? (
            <Badge variant="destructive">Serving API unavailable</Badge>
          ) : (
            <Badge variant="outline">Freshness probe</Badge>
          )}
        </div>

        {isLoading && !data.checked_at ? (
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <FreshnessTile
              icon={<Clock3 className="size-4" />}
              label="Latest content event"
              staleAfterMinutes={120}
              subtitle={data.latest_content?.entity_id || "Latest content entity id unavailable."}
              timestamp={data.latest_content?.event_time}
            />
            <FreshnessTile
              icon={<TimerReset className="size-4" />}
              label="Latest sentiment window"
              staleAfterMinutes={240}
              timestamp={data.latest_sentiment_window?.window_end}
            />
            <FreshnessTile
              icon={<Waves className="size-4" />}
              label="Latest trending window"
              staleAfterMinutes={240}
              timestamp={data.latest_trending_window?.window_end}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
