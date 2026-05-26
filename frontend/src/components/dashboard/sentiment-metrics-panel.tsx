import type { SentimentMetricsResponse } from "@/lib/api";
import {
  formatEntityTypeLabel,
  formatNumber,
  formatScore,
  formatSentimentLabel,
  formatTimestamp,
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
}: SentimentMetricsPanelProps) {
  const hasItems = data.items.length > 0;

  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Chỉ số sentiment</CardTitle>
        <CardDescription>
          Các lát cắt sentiment tổng hợp theo cửa sổ thời gian từ backend.
        </CardDescription>
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
            Không có dữ liệu sentiment trong khoảng thời gian đã chọn.
          </div>
        ) : null}

        {hasItems ? (
          <>
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Loại dữ liệu</TableHead>
                    <TableHead>Sentiment</TableHead>
                    <TableHead>Bắt đầu</TableHead>
                    <TableHead>Kết thúc</TableHead>
                    <TableHead>Số sự kiện</TableHead>
                    <TableHead>Điểm trung bình</TableHead>
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
                      <TableCell className="font-data text-xs text-muted-foreground">
                        {formatTimestamp(item.window_start)}
                      </TableCell>
                      <TableCell className="font-data text-xs text-muted-foreground">
                        {formatTimestamp(item.window_end)}
                      </TableCell>
                      <TableCell className="font-data">
                        {formatNumber(item.event_count)}
                      </TableCell>
                      <TableCell className="font-data">
                        {formatScore(item.average_sentiment_score)}
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
                        {formatTimestamp(item.window_start)} đến{" "}
                        {formatTimestamp(item.window_end)}
                      </p>
                    </div>
                    <Badge variant={sentimentVariant(item.sentiment)}>
                      {formatSentimentLabel(item.sentiment)}
                    </Badge>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-xl border bg-white/60 p-3">
                      <p className="text-xs text-muted-foreground">Số sự kiện</p>
                      <p className="font-data mt-1 text-lg font-semibold text-foreground">
                        {formatNumber(item.event_count)}
                      </p>
                    </div>
                    <div className="rounded-xl border bg-white/60 p-3">
                      <p className="text-xs text-muted-foreground">Điểm trung bình</p>
                      <p className="font-data mt-1 text-lg font-semibold text-foreground">
                        {formatScore(item.average_sentiment_score)}
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
