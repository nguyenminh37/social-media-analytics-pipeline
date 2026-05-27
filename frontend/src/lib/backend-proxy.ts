function getAnalyticsApiBaseUrl() {
  return process.env.ANALYTICS_API_BASE_URL || "http://localhost:8081";
}

function buildTargetUrl(pathname: string, searchParams?: URLSearchParams) {
  const url = new URL(pathname, getAnalyticsApiBaseUrl());

  if (searchParams) {
    for (const [key, value] of searchParams.entries()) {
      url.searchParams.set(key, value);
    }
  }

  return url;
}

export async function proxyBackendRequest(
  pathname: string,
  searchParams?: URLSearchParams,
) {
  const targetUrl = buildTargetUrl(pathname, searchParams);

  try {
    const response = await fetch(targetUrl, {
      cache: "no-store",
      headers: { accept: "application/json" },
    });
    const payload = await response.json().catch(() => ({}));

    return {
      payload,
      status: response.status,
    };
  } catch (error) {
    return {
      payload: {
        error: "analytics_backend_unavailable",
        detail:
          error instanceof Error
            ? error.message
            : "Unknown backend connection error.",
      },
      status: 503,
    };
  }
}
