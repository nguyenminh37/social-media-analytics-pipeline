"use client";

import { useEffect, useState, useTransition } from "react";

import {
  fetchFreshness,
  fetchHealth,
  fetchSentimentMetrics,
  fetchTopVideos,
  fetchTrendingKeywords,
  type FreshnessResponse,
  type HealthResponse,
  type LimitOption,
  type SentimentMetricsResponse,
  type TopVideosResponse,
  type TrendingKeywordsResponse,
  type WindowOption,
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

const EMPTY_HEALTH: HealthResponse = {
  status: "unknown",
  error: null,
  freshness: null,
};

const EMPTY_FRESHNESS: FreshnessResponse = {};

const EMPTY_TOP_VIDEOS: TopVideosResponse = {
  window_minutes: 0,
  limit: 0,
  items: [],
};

const EMPTY_SENTIMENT: SentimentMetricsResponse = {
  window_minutes: 0,
  items: [],
};

const EMPTY_TRENDING: TrendingKeywordsResponse = {
  window_minutes: 0,
  limit: 0,
  items: [],
};

export function DashboardShell() {
  const [windowMinutes, setWindowMinutes] = useState<WindowOption>(180);
  const [limit, setLimit] = useState<LimitOption>(10);
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
        fetchTopVideos(windowMinutes, limit),
        fetchSentimentMetrics(windowMinutes),
        fetchTrendingKeywords(windowMinutes, limit),
      ]);

      if (!active) {
        return;
      }

      setHealth({
        data: healthResult.data,
        error: healthResult.error,
      });
      setFreshness({
        data: freshnessResult.data,
        error: freshnessResult.error,
      });
      setTopVideos({
        data: topVideosResult.data,
        error: topVideosResult.error,
      });
      setSentiment({
        data: sentimentResult.data,
        error: sentimentResult.error,
      });
      setTrending({
        data: trendingResult.data,
        error: trendingResult.error,
      });
      setIsInitialLoading(false);
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [limit, refreshKey, windowMinutes]);

  function triggerRefresh() {
    startTransition(() => {
      setRefreshKey((value) => value + 1);
    });
  }

  function updateWindow(value: WindowOption) {
    startTransition(() => {
      setWindowMinutes(value);
    });
  }

  function updateLimit(value: LimitOption) {
    startTransition(() => {
      setLimit(value);
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
          isRefreshing={isRefreshing}
          limit={limit}
          onLimitChange={updateLimit}
          onRefresh={triggerRefresh}
          onWindowChange={updateWindow}
          windowMinutes={windowMinutes}
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
          />
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <SentimentMetricsPanel
              data={sentiment.data}
              error={sentiment.error}
              isLoading={isInitialLoading}
            />
            <TrendingKeywordsPanel
              data={trending.data}
              error={trending.error}
              isLoading={isInitialLoading}
            />
          </div>
        </section>
      </div>
    </main>
  );
}
