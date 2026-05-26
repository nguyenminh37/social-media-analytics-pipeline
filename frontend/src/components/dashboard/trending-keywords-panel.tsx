import type { TrendingKeywordsResponse } from "@/lib/api";
import {
  formatEntityTypeLabel,
  formatNumber,
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
        <CardTitle>Từ khóa trending</CardTitle>
       
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
            Không có từ khóa trending trong khoảng thời gian đã chọn.
          </div>
        ) : null}

        {hasItems ? (
          <>
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>Từ khóa</TableHead>
                    <TableHead>Loại dữ liệu</TableHead>
                    <TableHead>Tần suất</TableHead>
                    <TableHead>Kết thúc cửa sổ</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item, index) => (
                    <TableRow key={`${item.keyword}-${item.window_end}-${index}`}>
                      <TableCell className="font-data text-muted-foreground">
                        {index + 1}
                      </TableCell>
                      <TableCell className="font-medium text-foreground">
                        {item.keyword || "Từ khóa chưa có tên"}
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
                      <p className="text-sm text-muted-foreground">Hạng {index + 1}</p>
                      <p className="text-base font-medium text-foreground">
                        {item.keyword || "Từ khóa chưa có tên"}
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
                    <Badge variant="secondary">Kết thúc cửa sổ</Badge>
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
