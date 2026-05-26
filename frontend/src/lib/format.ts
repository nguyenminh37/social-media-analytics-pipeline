const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
});

const compactNumberFormatter = new Intl.NumberFormat("en", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatTimestamp(value?: string | null) {
  if (!value) {
    return "No data yet";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return dateTimeFormatter.format(date);
}

export function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }

  return compactNumberFormatter.format(value);
}

export function formatScore(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }

  return value.toFixed(2);
}

export function relativeAgeLabel(value?: string | null) {
  if (!value) {
    return "Missing";
  }

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Unknown";
  }

  const diffMs = Date.now() - timestamp;
  const diffMinutes = Math.max(Math.round(diffMs / 60000), 0);

  if (diffMinutes < 1) {
    return "Just now";
  }

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

export function getFreshnessState(
  value: string | null | undefined,
  staleAfterMinutes: number,
) {
  if (!value) {
    return {
      label: "Missing",
      detail: "No event has been materialized yet.",
      tone: "destructive" as const,
    };
  }

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return {
      label: "Unknown",
      detail: "Timestamp format is not readable.",
      tone: "outline" as const,
    };
  }

  const ageMinutes = Math.max(Math.round((Date.now() - timestamp) / 60000), 0);
  if (ageMinutes > staleAfterMinutes) {
    return {
      label: "Stale",
      detail: `Older than ${staleAfterMinutes}m.`,
      tone: "destructive" as const,
    };
  }

  if (ageMinutes > Math.round(staleAfterMinutes * 0.5)) {
    return {
      label: "Aging",
      detail: `${ageMinutes}m behind the latest check.`,
      tone: "outline" as const,
    };
  }

  return {
    label: "Fresh",
    detail: `${ageMinutes}m behind the latest check.`,
    tone: "secondary" as const,
  };
}
