import { ExternalLink, PlayCircle } from "lucide-react";

import type { TopVideosResponse } from "@/lib/api";
import { formatNumber, formatTimestamp } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
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

export function TopVideosTable({
  data,
  error,
  isLoading,
}: TopVideosTableProps) {
  const hasItems = data.items.length > 0;

  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Top videos</CardTitle>
        <CardDescription>
          Ranked from the read-only serving API by engagement score inside the
          selected window.
        </CardDescription>
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
            No top videos were returned for the current window.
          </div>
        ) : null}

        {hasItems ? (
          <>
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
                        {index + 1}
                      </TableCell>
                      <TableCell className="min-w-72 whitespace-normal">
                        <div className="space-y-1">
                          <p className="font-medium text-foreground">
                            {item.title || "Untitled video"}
                          </p>
                          {item.source_url ? (
                            <a
                              className="inline-flex items-center gap-1 text-xs text-primary"
                              href={item.source_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              Open source
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
                            {formatNumber(item.engagement_view_count)} views ·{" "}
                            {formatNumber(item.engagement_like_count)} likes ·{" "}
                            {formatNumber(item.engagement_comment_count)} comments
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={sentimentVariant(item.sentiment)}>
                          {item.sentiment || "unknown"}
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
                        Rank {index + 1}
                      </div>
                      <p className="font-medium text-foreground">
                        {item.title || "Untitled video"}
                      </p>
                    </div>
                    <Badge variant={sentimentVariant(item.sentiment)}>
                      {item.sentiment || "unknown"}
                    </Badge>
                  </div>
                  <div className="mt-4 space-y-2 text-sm">
                    <p className="font-data text-muted-foreground">
                      {item.entity_id}
                    </p>
                    <p className="font-data">
                      Score {formatNumber(item.engagement_score)}
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
