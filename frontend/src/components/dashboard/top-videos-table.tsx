import { ExternalLink, PlayCircle } from "lucide-react";

import { getHoursOptionLabel, type TopVideosResponse } from "@/lib/api";
import { formatNumber, formatSentimentLabel, formatTimestamp } from "@/lib/format";
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

interface TopVideosTableProps {
  data: TopVideosResponse;
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

function renderFilterLabel(data: TopVideosResponse) {
  if (data.filter_mode === "date_range") {
    return `${data.date_from || "?"} -> ${data.date_to || "?"}`;
  }

  return getHoursOptionLabel(data.window_hours ?? 0);
}

export function TopVideosTable({
  data,
  error,
  isLoading,
  isRefreshing,
  onPageChange,
}: TopVideosTableProps) {
  const hasItems = data.items.length > 0;

  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Top videos</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && !hasItems ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-6 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {isLoading && !hasItems ? (
          <div className="space-y-3">
            <Skeleton className="h-12 rounded-xl" />
            <Skeleton className="h-12 rounded-xl" />
            <Skeleton className="h-12 rounded-xl" />
          </div>
        ) : null}

        {!isLoading && !hasItems ? (
          <div className="rounded-2xl border bg-background/70 px-4 py-8 text-center text-sm text-muted-foreground">
            No results.
          </div>
        ) : null}

        {hasItems ? (
          <>
            <div className="grid gap-3 rounded-2xl border bg-background/60 px-4 py-3 text-sm text-muted-foreground md:grid-cols-2 xl:grid-cols-4">
              <div>
                <p className="font-medium text-foreground">Filter</p>
                <p className="font-data">{renderFilterLabel(data)}</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Range</p>
                <p className="font-data">
                  {formatTimestamp(data.from_time)} {"->"} {formatTimestamp(data.to_time)}
                </p>
              </div>
              <div>
                <p className="font-medium text-foreground">Items</p>
                <p className="font-data">{formatNumber(data.total_items)}</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Latest event</p>
                <p className="font-data">{formatTimestamp(data.latest_event_time)}</p>
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
                    <TableHead>#</TableHead>
                    <TableHead>Video</TableHead>
                    <TableHead>Entity ID</TableHead>
                    <TableHead>Engagement</TableHead>
                    <TableHead>Sentiment</TableHead>
                    <TableHead>Published</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item, index) => (
                    <TableRow key={`${item.entity_id}-${index}`}>
                      <TableCell className="font-data text-muted-foreground">
                        {(data.page - 1) * Math.max(data.page_size, 1) + index + 1}
                      </TableCell>
                      <TableCell className="min-w-72 whitespace-normal">
                        <div className="space-y-1">
                          <p className="font-medium text-foreground">
                            {item.title || "Untitled"}
                          </p>
                          {item.source_url ? (
                            <a
                              className="inline-flex items-center gap-1 text-xs text-primary"
                              href={item.source_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              Open
                              <ExternalLink className="size-3" />
                            </a>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell className="font-data text-xs text-muted-foreground">
                        {item.entity_id}
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1 text-sm">
                          <p className="font-data font-medium text-foreground">
                            Score {formatNumber(item.engagement_score)}
                          </p>
                          <p className="font-data text-xs text-muted-foreground">
                            Raw engagement {formatNumber(item.base_engagement_score)} · recency factor{" "}
                            {item.recency_multiplier?.toFixed(2) ?? "n/a"}
                          </p>
                          <p className="font-data text-xs text-muted-foreground">
                            {formatNumber(item.engagement_view_count)} views ·{" "}
                            {formatNumber(item.engagement_like_count)} likes ·{" "}
                            {formatNumber(item.engagement_comment_count)} comments
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={sentimentVariant(item.sentiment)}>
                          {formatSentimentLabel(item.sentiment)}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-data text-xs text-muted-foreground">
                        {formatTimestamp(item.published_at || item.event_time)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="grid gap-3 md:hidden">
              {data.items.map((item, index) => (
                <div
                  key={`${item.entity_id}-${index}`}
                  className="rounded-2xl border bg-background/70 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <PlayCircle className="size-4 text-primary" />
                        Rank {(data.page - 1) * Math.max(data.page_size, 1) + index + 1}
                      </div>
                      <p className="font-medium text-foreground">
                        {item.title || "Untitled"}
                      </p>
                    </div>
                    <Badge variant={sentimentVariant(item.sentiment)}>
                      {formatSentimentLabel(item.sentiment)}
                    </Badge>
                  </div>
                  <div className="mt-4 space-y-2 text-sm">
                    <p className="font-data text-muted-foreground">{item.entity_id}</p>
                    <p className="font-data">
                      Score {formatNumber(item.engagement_score)}
                    </p>
                    <p className="font-data text-xs text-muted-foreground">
                      Raw engagement {formatNumber(item.base_engagement_score)} · recency factor{" "}
                      {item.recency_multiplier?.toFixed(2) ?? "n/a"}
                    </p>
                    <p className="font-data text-xs text-muted-foreground">
                      {formatNumber(item.engagement_view_count)} views ·{" "}
                      {formatNumber(item.engagement_like_count)} likes ·{" "}
                      {formatNumber(item.engagement_comment_count)} comments
                    </p>
                    <p className="font-data text-xs text-muted-foreground">
                      {formatTimestamp(item.published_at || item.event_time)}
                    </p>
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
