import {
  getHoursOptionLabel,
  type TrendingKeywordsResponse,
} from "@/lib/api";
import {
  formatEntityTypeLabel,
  formatNumber,
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

interface TrendingKeywordsPanelProps {
  data: TrendingKeywordsResponse;
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  onPageChange: (page: number) => void;
}

export function TrendingKeywordsPanel({
  data,
  error,
  isLoading,
  isRefreshing,
  onPageChange,
}: TrendingKeywordsPanelProps) {
  const hasItems = data.items.length > 0;
  const filterLabel =
    data.filter_mode === "date_range"
      ? `${data.date_from || "?"} -> ${data.date_to || "?"}`
      : getHoursOptionLabel(data.window_hours ?? 0);

  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Trending keywords</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && !hasItems ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-6 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {isLoading && !hasItems ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <Skeleton className="h-28 rounded-2xl" />
            <Skeleton className="h-28 rounded-2xl" />
            <Skeleton className="h-28 rounded-2xl" />
          </div>
        ) : null}

        {!isLoading && !hasItems ? (
          <div className="rounded-2xl border bg-background/70 px-4 py-8 text-center text-sm text-muted-foreground">
            No results.
          </div>
        ) : null}

        {hasItems ? (
          <>
            <div className="rounded-2xl border bg-background/60 px-4 py-3 text-sm">
              <p className="font-medium text-foreground">Trending window</p>
              <p className="font-data text-muted-foreground">
                {formatTimestamp(data.window_start)} {"->"} {formatTimestamp(data.window_end)}
              </p>
              <p className="mt-2 text-muted-foreground">Filter: {filterLabel}</p>
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
                    <TableHead>Keyword</TableHead>
                    <TableHead>Entity type</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Window end</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item, index) => (
                    <TableRow key={`${item.keyword}-${item.window_end}-${index}`}>
                      <TableCell className="font-data text-muted-foreground">
                        {index + 1}
                      </TableCell>
                      <TableCell className="font-medium text-foreground">
                        {item.keyword || "Unnamed"}
                      </TableCell>
                      <TableCell>{formatEntityTypeLabel(item.entity_type)}</TableCell>
                      <TableCell className="font-data">
                        {formatNumber(item.frequency)}
                      </TableCell>
                      <TableCell className="font-data text-xs text-muted-foreground">
                        {formatTimestamp(item.window_end)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="grid gap-3 md:hidden">
              {data.items.map((item, index) => (
                <div
                  key={`${item.keyword}-${item.window_end}-${index}`}
                  className="rounded-2xl border bg-background/70 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm text-muted-foreground">Rank {index + 1}</p>
                      <p className="text-base font-medium text-foreground">
                        {item.keyword || "Unnamed"}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatEntityTypeLabel(item.entity_type)}
                      </p>
                    </div>
                    <Badge variant="outline" className="font-data">
                      {formatNumber(item.frequency)}
                    </Badge>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge variant="secondary">Window end</Badge>
                    <Badge variant="outline" className="font-data">
                      {formatTimestamp(item.window_end)}
                    </Badge>
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
