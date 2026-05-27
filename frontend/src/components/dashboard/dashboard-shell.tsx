"use client";

import { useEffect, useState, useTransition } from "react";

import {
  DEFAULT_PAGE_SIZE,
  fetchFreshness,
  fetchHealth,
  fetchSentimentMetrics,
  fetchTopVideos,
  fetchTrendingKeywords,
  type DashboardFilter,
  type FilterMode,
  type FreshnessResponse,
  type HealthResponse,
  type HoursOption,
  type SentimentMetricsResponse,
  type TopVideosResponse,
  type TrendingKeywordsResponse,
} from "@/lib/api";
import { DashboardFilters } from "@/components/dashboard/dashboard-filters";
import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { FreshnessOverview } from "@/components/dashboard/freshness-overview";
import { SentimentMetricsPanel } from "@/components/dashboard/sentiment-metrics-panel";
import { TopVideosTable } from "@/components/dashboard/top-videos-table";
import { TrendingKeywordsPanel } from "@/components/dashboard/trending-keywords-panel";
import { Separator } from "@/components/ui/separator";

interface RemoteSection<T> {
  data: T;
  error: string | null;
}

function getDefaultDateRange() {
  const toDate = new Date();
  const fromDate = new Date(toDate.getTime() - 6 * 24 * 60 * 60 * 1000);

  return {
    dateFrom: fromDate.toISOString().slice(0, 10),
    dateTo: toDate.toISOString().slice(0, 10),
  };
}

const EMPTY_HEALTH: HealthResponse = {
  status: "unknown",
  error: null,
  freshness: null,
};

const EMPTY_FRESHNESS: FreshnessResponse = {};

const EMPTY_TOP_VIDEOS: TopVideosResponse = {
  ranking_mode: null,
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_items: 0,
  total_pages: 0,
  has_previous_page: false,
  has_next_page: false,
  filter_mode: null,
  window_hours: null,
  date_from: null,
  date_to: null,
  from_time: null,
  to_time: null,
  latest_event_time: null,
  items: [],
};

const EMPTY_SENTIMENT: SentimentMetricsResponse = {
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_items: 0,
  total_pages: 0,
  has_previous_page: false,
  has_next_page: false,
  filter_mode: null,
  window_hours: null,
  date_from: null,
  date_to: null,
  from_time: null,
  to_time: null,
  latest_window_end: null,
  total_events: 0,
  items: [],
};

const EMPTY_TRENDING: TrendingKeywordsResponse = {
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_items: 0,
  total_pages: 0,
  has_previous_page: false,
  has_next_page: false,
  filter_mode: null,
  window_hours: null,
  date_from: null,
  date_to: null,
  from_time: null,
  to_time: null,
  window_start: null,
  window_end: null,
  items: [],
};

export function DashboardShell() {
  const defaultDateRange = getDefaultDateRange();
  const [filter, setFilter] = useState<DashboardFilter>({
    filterMode: "hours",
    windowHours: 24,
    dateFrom: defaultDateRange.dateFrom,
    dateTo: defaultDateRange.dateTo,
  });
  const [topVideosPage, setTopVideosPage] = useState(1);
  const [sentimentPage, setSentimentPage] = useState(1);
  const [trendingPage, setTrendingPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, startTransition] = useTransition();

  const [health, setHealth] = useState<RemoteSection<HealthResponse>>({
    data: EMPTY_HEALTH,
    error: null,
  });
  const [freshness, setFreshness] = useState<RemoteSection<FreshnessResponse>>({
    data: EMPTY_FRESHNESS,
    error: null,
  });
  const [topVideos, setTopVideos] = useState<RemoteSection<TopVideosResponse>>({
    data: EMPTY_TOP_VIDEOS,
    error: null,
  });
  const [sentiment, setSentiment] = useState<
    RemoteSection<SentimentMetricsResponse>
  >({
    data: EMPTY_SENTIMENT,
    error: null,
  });
  const [trending, setTrending] = useState<RemoteSection<TrendingKeywordsResponse>>(
    {
      data: EMPTY_TRENDING,
      error: null,
    },
  );

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      const [
        healthResult,
        freshnessResult,
        topVideosResult,
        sentimentResult,
        trendingResult,
      ] = await Promise.all([
        fetchHealth(),
        fetchFreshness(),
        fetchTopVideos(filter, topVideosPage),
        fetchSentimentMetrics(filter, sentimentPage),
        fetchTrendingKeywords(filter, trendingPage),
      ]);

      if (!active) {
        return;
      }

      setHealth({ data: healthResult.data, error: healthResult.error });
      setFreshness({ data: freshnessResult.data, error: freshnessResult.error });
      setTopVideos({ data: topVideosResult.data, error: topVideosResult.error });
      setSentiment({ data: sentimentResult.data, error: sentimentResult.error });
      setTrending({ data: trendingResult.data, error: trendingResult.error });
      setIsInitialLoading(false);
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [filter, refreshKey, sentimentPage, topVideosPage, trendingPage]);

  function resetPages() {
    setTopVideosPage(1);
    setSentimentPage(1);
    setTrendingPage(1);
  }

  function triggerRefresh() {
    startTransition(() => {
      setRefreshKey((value) => value + 1);
    });
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
    <main className="dashboard-shell flex-1">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <DashboardHeader
          error={health.error}
          health={{
            ...health.data,
            freshness: health.data.freshness ?? freshness.data,
          }}
          isLoading={isInitialLoading}
        />

        <DashboardFilters
          filter={filter}
          isRefreshing={isRefreshing}
          onDateFromChange={updateDateFrom}
          onDateToChange={updateDateTo}
          onFilterModeChange={updateFilterMode}
          onRefresh={triggerRefresh}
          onWindowHoursChange={updateWindowHours}
        />

        <section className="grid gap-6">
          <FreshnessOverview
            data={freshness.data}
            error={freshness.error}
            isLoading={isInitialLoading}
          />
          <Separator className="bg-border/70" />
          <TopVideosTable
            data={topVideos.data}
            error={topVideos.error}
            isLoading={isInitialLoading}
            isRefreshing={isRefreshing}
            onPageChange={setTopVideosPage}
          />
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <SentimentMetricsPanel
              data={sentiment.data}
              error={sentiment.error}
              isLoading={isInitialLoading}
              isRefreshing={isRefreshing}
              onPageChange={setSentimentPage}
            />
            <TrendingKeywordsPanel
              data={trending.data}
              error={trending.error}
              isLoading={isInitialLoading}
              isRefreshing={isRefreshing}
              onPageChange={setTrendingPage}
            />
          </div>
        </section>
      </div>
    </main>
  );
}
