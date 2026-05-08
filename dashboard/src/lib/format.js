export const formatCurrency = (val) => {
  if (val === undefined || val === null) return "₹0.00";
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(val);
};

export const formatPct = (val) => {
  if (val === undefined || val === null) return "0.00%";
  const sign = val > 0 ? "+" : "";
  return `${sign}${val.toFixed(2)}%`;
};

export const formatCompactNum = (val) => {
  if (val === undefined || val === null) return "0";
  return new Intl.NumberFormat('en-IN', {
    notation: "compact",
    compactDisplay: "short",
  }).format(val);
};
