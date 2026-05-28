export const HOURS_OPTIONS = [24, 72, 168, 720] as const;
export const DEFAULT_PAGE_SIZE = 10;

export const HOURS_OPTION_LABELS: Record<(typeof HOURS_OPTIONS)[number], string> = {
  24: "Last 24h",
  72: "Last 3d",
  168: "Last 7d",
  720: "Last 30d",
};

export type HoursOption = (typeof HOURS_OPTIONS)[number];
export type FilterMode = "hours" | "date_range";

export interface DashboardFilter {
  filterMode: FilterMode;
  windowHours: HoursOption;
  dateFrom: string;
  dateTo: string;
}

export interface PaginationResponse {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_previous_page: boolean;
  has_next_page: boolean;
  filter_mode?: FilterMode | null;
  window_hours?: number | null;
  date_from?: string | null;
  date_to?: string | null;
  from_time?: string | null;
  to_time?: string | null;
}

export function getHoursOptionLabel(windowHours: number) {
  return HOURS_OPTION_LABELS[windowHours as HoursOption] ?? `Last ${windowHours}h`;
}

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
  ranking_timestamp?: string | null;
  engagement_score?: number | null;
  base_engagement_score?: number | null;
  recency_multiplier?: number | null;
  engagement_view_count?: number | null;
  engagement_like_count?: number | null;
  engagement_comment_count?: number | null;
}

export interface TopVideosResponse extends PaginationResponse {
  ranking_mode?: string | null;
  latest_event_time?: string | null;
  items: TopVideoItem[];
}

export interface SentimentMetricItem {
  sentiment?: string | null;
  entity_type?: string | null;
  event_count?: number | null;
}

export interface SentimentMetricsResponse extends PaginationResponse {
  latest_window_end?: string | null;
  total_events?: number | null;
  items: SentimentMetricItem[];
}

export interface TrendingKeywordItem {
  keyword?: string | null;
  frequency?: number | null;
  entity_type?: string | null;
  window_start?: string | null;
  window_end?: string | null;
}

export interface TrendingKeywordsResponse extends PaginationResponse {
  window_start?: string | null;
  window_end?: string | null;
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

function normalizePaginationResponse(value: unknown): PaginationResponse {
  const record = asObject(value);
  const filterMode = asString(record.filter_mode);

  return {
    page: asNumber(record.page) ?? 1,
    page_size: asNumber(record.page_size) ?? DEFAULT_PAGE_SIZE,
    total_items: asNumber(record.total_items) ?? 0,
    total_pages: asNumber(record.total_pages) ?? 0,
    has_previous_page: record.has_previous_page === true,
    has_next_page: record.has_next_page === true,
    filter_mode:
      filterMode === "hours" || filterMode === "date_range" ? filterMode : null,
    window_hours: asNumber(record.window_hours),
    date_from: asString(record.date_from),
    date_to: asString(record.date_to),
    from_time: asString(record.from_time),
    to_time: asString(record.to_time),
  };
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
    ...normalizePaginationResponse(record),
    ranking_mode: asString(record.ranking_mode),
    latest_event_time: asString(record.latest_event_time),
    items: asArray(record.items).map((item) => {
      const video = asObject(item);
      return {
        entity_id: asString(video.entity_id) ?? "video-khong-xac-dinh",
        title: asString(video.title),
        source_url: asString(video.source_url),
        sentiment: asString(video.sentiment),
        published_at: asString(video.published_at),
        event_time: asString(video.event_time),
        ranking_timestamp: asString(video.ranking_timestamp),
        engagement_score: asNumber(video.engagement_score),
        base_engagement_score: asNumber(video.base_engagement_score),
        recency_multiplier: asNumber(video.recency_multiplier),
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
    ...normalizePaginationResponse(record),
    latest_window_end: asString(record.latest_window_end),
    total_events: asNumber(record.total_events),
    items: asArray(record.items).map((item) => {
      const metric = asObject(item);
      return {
        sentiment: asString(metric.sentiment),
        entity_type: asString(metric.entity_type),
        event_count: asNumber(metric.event_count),
      };
    }),
  };
}

export function normalizeTrendingKeywordsResponse(
  value: unknown,
): TrendingKeywordsResponse {
  const record = asObject(value);
  return {
    ...normalizePaginationResponse(record),
    window_start: asString(record.window_start),
    window_end: asString(record.window_end),
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
          : "Dashboard cannot reach the local proxy.",
    };
  }
}

function buildFilterSearchParams(filter: DashboardFilter) {
  if (filter.filterMode === "date_range") {
    return {
      filter_mode: "date_range",
      date_from: filter.dateFrom,
      date_to: filter.dateTo,
    } as const;
  }

  return {
    filter_mode: "hours",
    window_hours: filter.windowHours,
  } as const;
}

export function fetchHealth() {
  return requestProxy("/api/health", {}, normalizeHealthResponse);
}

export function fetchFreshness() {
  return requestProxy("/api/youtube/freshness", {}, normalizeFreshnessResponse);
}

export function fetchTopVideos(filter: DashboardFilter, page: number) {
  return requestProxy(
    "/api/youtube/top-videos",
    {
      ...buildFilterSearchParams(filter),
      page,
      page_size: DEFAULT_PAGE_SIZE,
    },
    normalizeTopVideosResponse,
  );
}

export function fetchSentimentMetrics(filter: DashboardFilter, page: number) {
  return requestProxy(
    "/api/youtube/sentiment-metrics",
    {
      ...buildFilterSearchParams(filter),
      page,
      page_size: DEFAULT_PAGE_SIZE,
    },
    normalizeSentimentMetricsResponse,
  );
}

export function fetchTrendingKeywords(filter: DashboardFilter, page: number) {
  return requestProxy(
    "/api/youtube/trending-keywords",
    {
      ...buildFilterSearchParams(filter),
      page,
      page_size: DEFAULT_PAGE_SIZE,
    },
    normalizeTrendingKeywordsResponse,
  );
}

export interface PublicCountItem {
  platform?: string | null;
  sentiment?: string | null;
  count: number;
}

export interface PublicContentEvent {
  content_id?: string | null;
  platform?: string | null;
  source?: string | null;
  title?: string | null;
  source_url?: string | null;
  event_time?: string | null;
  keywords: string[];
  sentiment?: string | null;
  sentiment_score?: number | null;
}

export interface PublicTrendAlert {
  keyword?: string | null;
  alert_type?: string | null;
  message?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  content_count?: number | null;
  news_count?: number | null;
  youtube_count?: number | null;
  trend_score?: number | null;
  representative_titles: string[];
}

export interface PublicOverviewResponse {
  checked_at?: string | null;
  content_count: number;
  scored_content_count: number;
  trend_alert_count: number;
  latest_content?: PublicContentEvent | null;
  latest_alert?: PublicTrendAlert | null;
  platform_counts: PublicCountItem[];
  sentiment_counts: PublicCountItem[];
}

export interface PublicTrendAlertsResponse extends PaginationResponse {
  items: PublicTrendAlert[];
}

export interface PublicContentEventsResponse extends PaginationResponse {
  items: PublicContentEvent[];
}

function asStringArray(value: unknown) {
  return asArray(value).filter((item): item is string => typeof item === "string");
}

function normalizePublicContentEvent(value: unknown): PublicContentEvent {
  const record = asObject(value);
  return {
    content_id: asString(record.content_id),
    platform: asString(record.platform),
    source: asString(record.source),
    title: asString(record.title),
    source_url: asString(record.source_url),
    event_time: asString(record.event_time),
    keywords: asStringArray(record.keywords),
    sentiment: asString(record.sentiment),
    sentiment_score: asNumber(record.sentiment_score),
  };
}

function normalizePublicTrendAlert(value: unknown): PublicTrendAlert {
  const record = asObject(value);
  return {
    keyword: asString(record.keyword),
    alert_type: asString(record.alert_type),
    message: asString(record.message),
    window_start: asString(record.window_start),
    window_end: asString(record.window_end),
    content_count: asNumber(record.content_count),
    news_count: asNumber(record.news_count),
    youtube_count: asNumber(record.youtube_count),
    trend_score: asNumber(record.trend_score),
    representative_titles: asStringArray(record.representative_titles),
  };
}

export function normalizePublicOverviewResponse(
  value: unknown,
): PublicOverviewResponse {
  const record = asObject(value);
  return {
    checked_at: asString(record.checked_at),
    content_count: asNumber(record.content_count) ?? 0,
    scored_content_count: asNumber(record.scored_content_count) ?? 0,
    trend_alert_count: asNumber(record.trend_alert_count) ?? 0,
    latest_content: record.latest_content
      ? normalizePublicContentEvent(record.latest_content)
      : null,
    latest_alert: record.latest_alert
      ? normalizePublicTrendAlert(record.latest_alert)
      : null,
    platform_counts: asArray(record.platform_counts).map((item) => {
      const count = asObject(item);
      return {
        platform: asString(count.platform),
        count: asNumber(count.count) ?? 0,
      };
    }),
    sentiment_counts: asArray(record.sentiment_counts).map((item) => {
      const count = asObject(item);
      return {
        sentiment: asString(count.sentiment),
        count: asNumber(count.count) ?? 0,
      };
    }),
  };
}

export function normalizePublicTrendAlertsResponse(
  value: unknown,
): PublicTrendAlertsResponse {
  const record = asObject(value);
  return {
    ...normalizePaginationResponse(record),
    items: asArray(record.items).map(normalizePublicTrendAlert),
  };
}

export function normalizePublicContentEventsResponse(
  value: unknown,
): PublicContentEventsResponse {
  const record = asObject(value);
  return {
    ...normalizePaginationResponse(record),
    items: asArray(record.items).map(normalizePublicContentEvent),
  };
}

export function fetchPublicOverview(filter: DashboardFilter) {
  return requestProxy(
    "/api/public/overview",
    buildFilterSearchParams(filter),
    normalizePublicOverviewResponse,
  );
}

export function fetchPublicTrendAlerts(filter: DashboardFilter, page: number) {
  return requestProxy(
    "/api/public/trend-alerts",
    {
      ...buildFilterSearchParams(filter),
      page,
      page_size: DEFAULT_PAGE_SIZE,
    },
    normalizePublicTrendAlertsResponse,
  );
}

export function fetchPublicContentEvents(filter: DashboardFilter, page: number) {
  return requestProxy(
    "/api/public/content-events",
    {
      ...buildFilterSearchParams(filter),
      page,
      page_size: DEFAULT_PAGE_SIZE,
    },
    normalizePublicContentEventsResponse,
  );
}
