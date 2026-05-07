import { TrendingUp, TrendingDown, Minus, Loader2 } from "lucide-react";

/**
 * Three explicit states + clear visual treatment per state.
 *  - ok:           shows score with bullish/neutral/bearish styling
 *  - processing:   skeleton pulse ("Analyzing...")
 *  - unavailable:  grey "—" with tooltip
 *  - stale:        yellow dot indicator
 */
export default function SentimentBadge({ sentiment, size = "sm" }) {
  if (!sentiment) {
    return (
      <span
        data-testid="sentiment-badge-loading"
        title="Loading sentiment"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-700/40 border border-slate-700/50 text-slate-400 text-[10px]"
      >
        <Loader2 className="w-3 h-3 animate-spin" />
        <span>—</span>
      </span>
    );
  }

  const { state, label, score = 0, headline_count = 0 } = sentiment;

  if (state === "processing") {
    return (
      <span
        data-testid="sentiment-badge-processing"
        title="Analyzing news… refresh in 1–2 min"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-700/40 border border-slate-700/50 text-slate-300 text-[10px] animate-pulse"
      >
        <Loader2 className="w-3 h-3 animate-spin" />
        Analyzing
      </span>
    );
  }

  if (state === "unavailable" || headline_count === 0) {
    return (
      <span
        data-testid="sentiment-badge-unavailable"
        title="No recent news in last 24h"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/60 border border-slate-700/50 text-slate-500 text-[10px]"
      >
        No news
      </span>
    );
  }

  // OK state
  let bg, border, text, Icon;
  if (label === "bullish") {
    bg = "bg-emerald-500/10"; border = "border-emerald-500/30"; text = "text-emerald-300"; Icon = TrendingUp;
  } else if (label === "bearish") {
    bg = "bg-rose-500/10"; border = "border-rose-500/30"; text = "text-rose-300"; Icon = TrendingDown;
  } else {
    bg = "bg-slate-700/30"; border = "border-slate-600/40"; text = "text-slate-300"; Icon = Minus;
  }

  const padX = size === "lg" ? "px-2.5" : "px-2";
  const padY = size === "lg" ? "py-1" : "py-0.5";
  const txt = size === "lg" ? "text-xs" : "text-[10px]";
  const iconSz = size === "lg" ? "w-3.5 h-3.5" : "w-3 h-3";

  return (
    <span
      data-testid={`sentiment-badge-${label}`}
      title={`${label.toUpperCase()} · score ${score?.toFixed?.(2) ?? score} · ${headline_count} headlines`}
      className={`inline-flex items-center gap-1 ${padX} ${padY} rounded-md ${bg} border ${border} ${text} ${txt} font-medium`}
    >
      <Icon className={iconSz} />
      <span className="capitalize">{label}</span>
      {size === "lg" && score !== undefined && (
        <span className="opacity-70 tabular-nums ml-0.5">
          {score > 0 ? "+" : ""}{score.toFixed(2)}
        </span>
      )}
    </span>
  );
}
