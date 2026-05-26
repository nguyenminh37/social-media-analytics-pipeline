export const WINDOW_OPTIONS = [60, 180, 720, 1440] as const;
export const LIMIT_OPTIONS = [5, 10, 20] as const;

export type WindowOption = (typeof WINDOW_OPTIONS)[number];
export type LimitOption = (typeof LIMIT_OPTIONS)[number];

export interface HealthResponse {
  status: "ok" | "error" | "unknown";
  error?: string | null;
  freshness?: FreshnessResponse | null;
}

export interface FreshnessMarker {
  entity_id?: string | null;
  event_time?: string | null;
  window_end?: string | null;
}

export interface FreshnessResponse {
  checked_at?: string | null;
  latest_content?: FreshnessMarker | null;
  latest_sentiment_window?: FreshnessMarker | null;
  latest_trending_window?: FreshnessMarker | null;
}

export interface TopVideoItem {
  entity_id: string;
  title?: string | null;
  source_url?: string | null;
  sentiment?: string | null;
  published_at?: string | null;
  event_time?: string | null;
  engagement_score?: number | null;
  engagement_view_count?: number | null;
  engagement_like_count?: number | null;
  engagement_comment_count?: number | null;
}

export interface TopVideosResponse {
  window_minutes: number;
  limit: number;
  items: TopVideoItem[];
}

export interface SentimentMetricItem {
  sentiment?: string | null;
  entity_type?: string | null;
  event_count?: number | null;
  average_sentiment_score?: number | null;
  window_start?: string | null;
  window_end?: string | null;
}

export interface SentimentMetricsResponse {
  window_minutes: number;
  items: SentimentMetricItem[];
}

export interface TrendingKeywordItem {
  keyword?: string | null;
  frequency?: number | null;
  entity_type?: string | null;
  window_start?: string | null;
  window_end?: string | null;
}

export interface TrendingKeywordsResponse {
  window_minutes: number;
  limit: number;
  items: TrendingKeywordItem[];
}

export interface ApiResult<T> {
  ok: boolean;
  status: number;
  data: T;
  error: string | null;
}

function asObject(value: unknown) {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown) {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown) {
  return Array.isArray(value) ? value : [];
}

function normalizeFreshnessMarker(value: unknown): FreshnessMarker | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const record = asObject(value);
  return {
    entity_id: asString(record.entity_id),
    event_time: asString(record.event_time),
    window_end: asString(record.window_end),
  };
}

export function normalizeHealthResponse(value: unknown): HealthResponse {
  const record = asObject(value);
  const status = asString(record.status);

  return {
    status: status === "ok" || status === "error" ? status : "unknown",
    error: asString(record.error),
    freshness: normalizeFreshnessResponse(record.freshness),
  };
}

export function normalizeFreshnessResponse(value: unknown): FreshnessResponse {
  const record = asObject(value);
  return {
    checked_at: asString(record.checked_at),
    latest_content: normalizeFreshnessMarker(record.latest_content),
    latest_sentiment_window: normalizeFreshnessMarker(
      record.latest_sentiment_window,
    ),
    latest_trending_window: normalizeFreshnessMarker(
      record.latest_trending_window,
    ),
  };
}

export function normalizeTopVideosResponse(value: unknown): TopVideosResponse {
  const record = asObject(value);
  return {
    window_minutes: asNumber(record.window_minutes) ?? 0,
    limit: asNumber(record.limit) ?? 0,
    items: asArray(record.items).map((item) => {
      const video = asObject(item);
      return {
        entity_id: asString(video.entity_id) ?? "unknown-video",
        title: asString(video.title),
        source_url: asString(video.source_url),
        sentiment: asString(video.sentiment),
        published_at: asString(video.published_at),
        event_time: asString(video.event_time),
        engagement_score: asNumber(video.engagement_score),
        engagement_view_count: asNumber(video.engagement_view_count),
        engagement_like_count: asNumber(video.engagement_like_count),
        engagement_comment_count: asNumber(video.engagement_comment_count),
      };
    }),
  };
}

export function normalizeSentimentMetricsResponse(
  value: unknown,
): SentimentMetricsResponse {
  const record = asObject(value);
  return {
    window_minutes: asNumber(record.window_minutes) ?? 0,
    items: asArray(record.items).map((item) => {
      const metric = asObject(item);
      return {
        sentiment: asString(metric.sentiment),
        entity_type: asString(metric.entity_type),
        event_count: asNumber(metric.event_count),
        average_sentiment_score:
          asNumber(metric.average_sentiment_score) ??
          asNumber(metric.avg_sentiment_score),
        window_start: asString(metric.window_start),
        window_end: asString(metric.window_end),
      };
    }),
  };
}

export function normalizeTrendingKeywordsResponse(
  value: unknown,
): TrendingKeywordsResponse {
  const record = asObject(value);
  return {
    window_minutes: asNumber(record.window_minutes) ?? 0,
    limit: asNumber(record.limit) ?? 0,
    items: asArray(record.items).map((item) => {
      const keyword = asObject(item);
      return {
        keyword: asString(keyword.keyword),
        frequency: asNumber(keyword.frequency),
        entity_type: asString(keyword.entity_type),
        window_start: asString(keyword.window_start),
        window_end: asString(keyword.window_end),
      };
    }),
  };
}

function extractErrorMessage(payload: unknown, fallbackStatus: number) {
  const record = asObject(payload);
  return (
    asString(record.detail) ??
    asString(record.error) ??
    `Request failed with status ${fallbackStatus}.`
  );
}

async function requestProxy<T>(
  pathname: string,
  searchParams: Record<string, string | number | undefined>,
  normalize: (value: unknown) => T,
): Promise<ApiResult<T>> {
  const url = new URL(pathname, window.location.origin);

  for (const [key, value] of Object.entries(searchParams)) {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  }

  try {
    const response = await fetch(url, {
      cache: "no-store",
      headers: { accept: "application/json" },
    });
    const payload = await response.json().catch(() => ({}));

    return {
      ok: response.ok,
      status: response.status,
      data: normalize(payload),
      error: response.ok ? null : extractErrorMessage(payload, response.status),
    };
  } catch (error) {
    return {
      ok: false,
      status: 503,
      data: normalize({}),
      error:
        error instanceof Error
          ? error.message
          : "The dashboard could not reach the local proxy.",
    };
  }
}

export function fetchHealth() {
  return requestProxy("/api/health", {}, normalizeHealthResponse);
}

export function fetchFreshness() {
  return requestProxy("/api/youtube/freshness", {}, normalizeFreshnessResponse);
}

export function fetchTopVideos(windowMinutes: WindowOption, limit: LimitOption) {
  return requestProxy(
    "/api/youtube/top-videos",
    {
      window_minutes: windowMinutes,
      limit,
    },
    normalizeTopVideosResponse,
  );
}

export function fetchSentimentMetrics(windowMinutes: WindowOption) {
  return requestProxy(
    "/api/youtube/sentiment-metrics",
    {
      window_minutes: windowMinutes,
    },
    normalizeSentimentMetricsResponse,
  );
}

export function fetchTrendingKeywords(
  windowMinutes: WindowOption,
  limit: LimitOption,
) {
  return requestProxy(
    "/api/youtube/trending-keywords",
    {
      window_minutes: windowMinutes,
      limit,
    },
    normalizeTrendingKeywordsResponse,
  );
}
