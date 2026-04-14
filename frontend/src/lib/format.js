export function formatPrice(value) {
  if (!value && value !== 0) return "-";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatMarketCap(value) {
  if (!value) return "-";
  const cr = value / 1e7;
  if (cr >= 100000) return `${(cr / 100000).toFixed(1)}L Cr`;
  if (cr >= 1000) return `${(cr / 1000).toFixed(1)}K Cr`;
  if (cr >= 1) return `${cr.toFixed(0)} Cr`;
  return `${(value / 1e5).toFixed(1)} L`;
}

export function formatPct(value) {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}%`;
}

export function formatNum(value, decimals = 2) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(decimals);
}
