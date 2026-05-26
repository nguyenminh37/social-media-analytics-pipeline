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
    return "Chưa có dữ liệu";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return dateTimeFormatter.format(date);
}

export function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "không có";
  }

  return compactNumberFormatter.format(value);
}

export function formatEntityTypeLabel(value?: string | null) {
  switch (value?.toLowerCase()) {
    case "video":
      return "Video";
    case "comment":
      return "Bình luận";
    case "channel":
      return "Kênh";
    default:
      return value || "Tất cả entity";
  }
}

export function formatSentimentLabel(value?: string | null) {
  switch (value?.toLowerCase()) {
    case "positive":
      return "Tích cực";
    case "negative":
      return "Tiêu cực";
    case "neutral":
      return "Trung tính";
    default:
      return value || "Không rõ";
  }
}

export function formatScore(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "không có";
  }

  return value.toFixed(2);
}

export function relativeAgeLabel(value?: string | null) {
  if (!value) {
    return "Thiếu dữ liệu";
  }

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Không xác định";
  }

  const diffMs = Date.now() - timestamp;
  const diffMinutes = Math.max(Math.round(diffMs / 60000), 0);

  if (diffMinutes < 1) {
    return "Vừa xong";
  }

  if (diffMinutes < 60) {
    return `${diffMinutes} phút trước`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours} giờ trước`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays} ngày trước`;
}

export function getFreshnessState(
  value: string | null | undefined,
  staleAfterMinutes: number,
) {
  if (!value) {
    return {
      label: "Thiếu dữ liệu",
      detail: "Chưa có sự kiện nào được materialize.",
      tone: "destructive" as const,
    };
  }

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return {
      label: "Không xác định",
      detail: "Định dạng thời gian không đọc được.",
      tone: "outline" as const,
    };
  }

  const ageMinutes = Math.max(Math.round((Date.now() - timestamp) / 60000), 0);
  if (ageMinutes > staleAfterMinutes) {
    return {
      label: "Cũ",
      detail: `Cũ hơn ${staleAfterMinutes} phút.`,
      tone: "destructive" as const,
    };
  }

  if (ageMinutes > Math.round(staleAfterMinutes * 0.5)) {
    return {
      label: "Đang cũ dần",
      detail: `Chậm ${ageMinutes} phút so với lần kiểm tra gần nhất.`,
      tone: "outline" as const,
    };
  }

  return {
    label: "Mới",
    detail: `Chậm ${ageMinutes} phút so với lần kiểm tra gần nhất.`,
    tone: "secondary" as const,
  };
}
