import type { TrendingKeywordsResponse } from "@/lib/api";
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

interface TrendingKeywordsPanelProps {
  data: TrendingKeywordsResponse;
  error: string | null;
  isLoading: boolean;
}

export function TrendingKeywordsPanel({
  data,
  error,
  isLoading,
}: TrendingKeywordsPanelProps) {
  const hasItems = data.items.length > 0;

  return (
    <Card className="bg-white/88 shadow-[0_20px_70px_-58px_rgba(15,23,42,0.45)]">
      <CardHeader>
        <CardTitle>Trending keywords</CardTitle>
        <CardDescription>
          Keyword frequency snapshot exposed by the existing Python serving API.
        </CardDescription>
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
            No trending keywords were returned for the selected window.
          </div>
        ) : null}

        {hasItems ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.items.map((item, index) => (
              <div
                key={`${item.keyword}-${item.window_end}-${index}`}
                className="rounded-2xl border bg-background/70 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-medium text-foreground">
                      {item.keyword || "Unnamed keyword"}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.entity_type || "all entities"}
                    </p>
                  </div>
                  <Badge variant="outline" className="font-data">
                    {formatNumber(item.frequency)}
                  </Badge>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge variant="secondary">Live keyword window</Badge>
                  <Badge variant="outline" className="font-data">
                    {formatTimestamp(item.window_end)}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
