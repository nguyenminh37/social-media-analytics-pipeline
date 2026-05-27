"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import type { ReactNode } from "react";

import {
  DEFAULT_PAGE_SIZE,
  fetchPublicContentEvents,
  fetchPublicOverview,
  fetchPublicTrendAlerts,
  type DashboardFilter,
  type FilterMode,
  type HoursOption,
  type PublicContentEventsResponse,
  type PublicOverviewResponse,
  type PublicTrendAlertsResponse,
} from "@/lib/api";
import { DashboardFilters } from "@/components/dashboard/dashboard-filters";
import { PaginationControls } from "@/components/dashboard/pagination-controls";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface RemoteSection<T> {
  data: T;
  error: string | null;
}

const EMPTY_OVERVIEW: PublicOverviewResponse = {
  content_count: 0,
  scored_content_count: 0,
  trend_alert_count: 0,
  latest_content: null,
  latest_alert: null,
  platform_counts: [],
  sentiment_counts: [],
};

const EMPTY_ALERTS: PublicTrendAlertsResponse = {
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_items: 0,
  total_pages: 0,
  has_previous_page: false,
  has_next_page: false,
  items: [],
};

const EMPTY_CONTENT: PublicContentEventsResponse = {
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_items: 0,
  total_pages: 0,
  has_previous_page: false,
  has_next_page: false,
  items: [],
};

function getDefaultDateRange() {
  const toDate = new Date();
  const fromDate = new Date(toDate.getTime() - 6 * 24 * 60 * 60 * 1000);
  return {
    dateFrom: fromDate.toISOString().slice(0, 10),
    dateTo: toDate.toISOString().slice(0, 10),
  };
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatNumber(value?: number | null) {
  return new Intl.NumberFormat("vi-VN").format(value ?? 0);
}

function formatLag(value?: number | null) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (value < 0) {
    return "YouTube trước báo";
  }
  return `${Math.round(value)} phút`;
}

function MetricTile({
  label,
  value,
  subvalue,
}: {
  label: string;
  value: string;
  subvalue?: string | null;
}) {
  return (
    <div className="rounded-md border bg-white px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      {subvalue ? <div className="mt-1 text-sm text-slate-600">{subvalue}</div> : null}
    </div>
  );
}

function Panel({
  title,
  children,
  error,
}: {
  title: string;
  children: ReactNode;
  error?: string | null;
}) {
  return (
    <section className="rounded-md border bg-white">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
        {error ? <span className="text-sm text-red-700">{error}</span> : null}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function DashboardShell() {
  const defaultDateRange = useMemo(() => getDefaultDateRange(), []);
  const [filter, setFilter] = useState<DashboardFilter>({
    filterMode: "hours",
    windowHours: 24,
    dateFrom: defaultDateRange.dateFrom,
    dateTo: defaultDateRange.dateTo,
  });
  const [alertPage, setAlertPage] = useState(1);
  const [contentPage, setContentPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, startTransition] = useTransition();
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [overview, setOverview] = useState<RemoteSection<PublicOverviewResponse>>({
    data: EMPTY_OVERVIEW,
    error: null,
  });
  const [alerts, setAlerts] = useState<RemoteSection<PublicTrendAlertsResponse>>({
    data: EMPTY_ALERTS,
    error: null,
  });
  const [content, setContent] = useState<RemoteSection<PublicContentEventsResponse>>({
    data: EMPTY_CONTENT,
    error: null,
  });

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      const [overviewResult, alertResult, contentResult] = await Promise.all([
        fetchPublicOverview(filter),
        fetchPublicTrendAlerts(filter, alertPage),
        fetchPublicContentEvents(filter, contentPage),
      ]);

      if (!active) {
        return;
      }

      setOverview({ data: overviewResult.data, error: overviewResult.error });
      setAlerts({ data: alertResult.data, error: alertResult.error });
      setContent({ data: contentResult.data, error: contentResult.error });
      setIsInitialLoading(false);
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [alertPage, contentPage, filter, refreshKey]);

  function resetPages() {
    setAlertPage(1);
    setContentPage(1);
  }

  function updateFilterMode(value: FilterMode) {
    startTransition(() => {
      setFilter((current) => ({ ...current, filterMode: value }));
      resetPages();
    });
  }

  function updateWindowHours(value: HoursOption) {
    startTransition(() => {
      setFilter((current) => ({ ...current, windowHours: value }));
      resetPages();
    });
  }

  function updateDateFrom(value: string) {
    startTransition(() => {
      setFilter((current) => ({ ...current, dateFrom: value }));
      resetPages();
    });
  }

  function updateDateTo(value: string) {
    startTransition(() => {
      setFilter((current) => ({ ...current, dateTo: value }));
      resetPages();
    });
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-3 border-b border-slate-300 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">
              Vietnamese Trend Radar
            </h1>
            <div className="mt-1 text-sm text-slate-600">
              {isInitialLoading
                ? "Loading data"
                : `Updated ${formatDateTime(overview.data.checked_at)}`}
            </div>
          </div>
        </header>

        <DashboardFilters
          filter={filter}
          isRefreshing={isRefreshing}
          onDateFromChange={updateDateFrom}
          onDateToChange={updateDateTo}
          onFilterModeChange={updateFilterMode}
          onRefresh={() => startTransition(() => setRefreshKey((value) => value + 1))}
          onWindowHoursChange={updateWindowHours}
        />

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricTile
            label="Content"
            value={formatNumber(overview.data.content_count)}
            subvalue={overview.data.platform_counts
              .map((item) => `${item.platform}: ${formatNumber(item.count)}`)
              .join(" / ")}
          />
          <MetricTile
            label="Trend alerts"
            value={formatNumber(overview.data.trend_alert_count)}
            subvalue={overview.data.latest_alert?.keyword ?? null}
          />
          <MetricTile
            label="Sentiment scored"
            value={formatNumber(overview.data.scored_content_count)}
            subvalue={overview.data.sentiment_counts
              .map((item) => `${item.sentiment}: ${formatNumber(item.count)}`)
              .join(" / ")}
          />
          <MetricTile
            label="Latest content"
            value={overview.data.latest_content?.source ?? "-"}
            subvalue={overview.data.latest_content?.title ?? null}
          />
        </section>

        <Panel title="Trend alerts" error={alerts.error}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Keyword</TableHead>
                <TableHead>Window</TableHead>
                <TableHead className="text-right">Count</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead>YouTube lag</TableHead>
                <TableHead>Signal</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.data.items.map((item) => (
                <TableRow key={`${item.keyword}-${item.window_end}`}>
                  <TableCell className="font-medium">{item.keyword}</TableCell>
                  <TableCell>{formatDateTime(item.window_end)}</TableCell>
                  <TableCell className="text-right">
                    {formatNumber(item.content_count)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(Math.round(item.trend_score ?? 0))}
                  </TableCell>
                  <TableCell>{formatLag(item.youtube_lag_minutes)}</TableCell>
                  <TableCell className="max-w-[420px] whitespace-normal text-slate-700">
                    {item.message}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <PaginationControls
            currentPage={alerts.data.page}
            hasNextPage={alerts.data.has_next_page}
            hasPreviousPage={alerts.data.has_previous_page}
            isDisabled={isRefreshing}
            onPageChange={setAlertPage}
            totalPages={alerts.data.total_pages}
          />
        </Panel>

        <Panel title="Latest content" error={content.error}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Keywords</TableHead>
                <TableHead>Sentiment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {content.data.items.map((item) => (
                <TableRow key={item.content_id ?? item.source_url ?? item.title}>
                  <TableCell>{formatDateTime(item.event_time)}</TableCell>
                  <TableCell>{item.source}</TableCell>
                  <TableCell className="max-w-[440px] whitespace-normal">
                    {item.source_url ? (
                      <a
                        className="text-slate-950 underline decoration-slate-300 underline-offset-2"
                        href={item.source_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {item.title}
                      </a>
                    ) : (
                      item.title
                    )}
                  </TableCell>
                  <TableCell className="max-w-[320px] whitespace-normal text-slate-700">
                    {item.keywords.slice(0, 6).join(", ")}
                  </TableCell>
                  <TableCell>{item.sentiment ?? "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <PaginationControls
            currentPage={content.data.page}
            hasNextPage={content.data.has_next_page}
            hasPreviousPage={content.data.has_previous_page}
            isDisabled={isRefreshing}
            onPageChange={setContentPage}
            totalPages={content.data.total_pages}
          />
        </Panel>
      </div>
    </main>
  );
}
