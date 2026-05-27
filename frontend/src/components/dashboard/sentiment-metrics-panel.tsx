import {
  getHoursOptionLabel,
  type SentimentMetricsResponse,
} from "@/lib/api";
import {
  formatEntityTypeLabel,
  formatNumber,
  formatPercent,
  formatSentimentLabel,
  formatTimestamp,
} from "@/lib/format";
import { PaginationControls } from "@/components/dashboard/pagination-controls";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface SentimentMetricsPanelProps {
  data: SentimentMetricsResponse;
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  onPageChange: (page: number) => void;
}

function sentimentVariant(sentiment?: string | null) {
  switch (sentiment?.toLowerCase()) {
    case "positive":
      return "secondary" as const;
    case "negative":
      return "destructive" as const;
    default:
      return "outline" as const;
  }
}

export function SentimentMetricsPanel({
  data,
  error,
  isLoading,
  isRefreshing,
  onPageChange,
}: SentimentMetricsPanelProps) {
  const hasItems = data.items.length > 0;
  const totalEvents =
    data.total_events ??
    data.items.reduce((sum, item) => sum + (item.event_count ?? 0), 0);

  const filterLabel =
    data.filter_mode === "date_range"
      ? `${data.date_from || "?"} -> ${data.date_to || "?"}`
      : getHoursOptionLabel(data.window_hours ?? 0);

  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Sentiment</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && !hasItems ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-6 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {isLoading && !hasItems ? (
          <div className="grid gap-3 md:grid-cols-3">
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
          </div>
        ) : null}

        {!isLoading && !hasItems ? (
          <div className="rounded-2xl border bg-background/70 px-4 py-8 text-center text-sm text-muted-foreground">
            No results.
          </div>
        ) : null}

        {hasItems ? (
          <>
            <div className="grid gap-3 rounded-2xl border bg-background/60 px-4 py-3 text-sm md:grid-cols-2">
              <div>
                <p className="font-medium text-foreground">Events</p>
                <p className="font-data text-muted-foreground">
                  {formatNumber(totalEvents)}
                </p>
              </div>
              <div>
                <p className="font-medium text-foreground">Latest window</p>
                <p className="font-data text-muted-foreground">
                  {formatTimestamp(data.latest_window_end)}
                </p>
              </div>
              <div>
                <p className="font-medium text-foreground">Filter</p>
                <p className="font-data text-muted-foreground">{filterLabel}</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Page</p>
                <p className="font-data text-muted-foreground">
                  {data.page} / {Math.max(data.total_pages, 1)}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                Page {data.page} / {Math.max(data.total_pages, 1)}
              </p>
              <PaginationControls
                currentPage={data.page}
                hasNextPage={data.has_next_page}
                hasPreviousPage={data.has_previous_page}
                isDisabled={isRefreshing}
                onPageChange={onPageChange}
                totalPages={data.total_pages}
              />
            </div>
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Entity type</TableHead>
                    <TableHead>Sentiment</TableHead>
                    <TableHead>Events</TableHead>
                    <TableHead>Share</TableHead>
                    <TableHead>Latest window</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item, index) => (
                    <TableRow key={`${item.sentiment}-${item.entity_type}-${index}`}>
                      <TableCell className="font-medium text-foreground">
                        {formatEntityTypeLabel(item.entity_type)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={sentimentVariant(item.sentiment)}>
                          {formatSentimentLabel(item.sentiment)}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-data">
                        {formatNumber(item.event_count)}
                      </TableCell>
                      <TableCell className="font-data">
                        {formatPercent((item.event_count ?? 0) / Math.max(totalEvents, 1))}
                      </TableCell>
                      <TableCell className="font-data text-xs text-muted-foreground">
                        {formatTimestamp(data.latest_window_end)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="grid gap-3 md:hidden">
              {data.items.map((item, index) => (
                <div
                  key={`${item.sentiment}-${item.entity_type}-${index}`}
                  className="rounded-2xl border bg-background/70 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-foreground">
                        {formatEntityTypeLabel(item.entity_type)}
                      </p>
                      <p className="font-data text-xs text-muted-foreground">
                        {formatTimestamp(data.latest_window_end)}
                      </p>
                    </div>
                    <Badge variant={sentimentVariant(item.sentiment)}>
                      {formatSentimentLabel(item.sentiment)}
                    </Badge>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-xl border bg-white/60 p-3">
                      <p className="text-xs text-muted-foreground">Events</p>
                      <p className="font-data mt-1 text-lg font-semibold text-foreground">
                        {formatNumber(item.event_count)}
                      </p>
                    </div>
                    <div className="rounded-xl border bg-white/60 p-3">
                      <p className="text-xs text-muted-foreground">Share</p>
                      <p className="font-data mt-1 text-lg font-semibold text-foreground">
                        {formatPercent((item.event_count ?? 0) / Math.max(totalEvents, 1))}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
