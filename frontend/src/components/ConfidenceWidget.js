export default function ConfidenceWidget({ data, backgroundUrl }) {
  const score = data?.score ?? 50;
  const status = data?.status ?? "CAUTIOUS";

  const color =
    score >= 60 ? "#00E676" : score >= 40 ? "#FFB300" : "#FF3D00";

  return (
    <div
      data-testid="confidence-widget"
      className="col-span-12 md:col-span-4 bg-[#0C0C0C] border border-[#1F1F1F] p-6 relative overflow-hidden"
    >
      {backgroundUrl && (
        <img
          src={backgroundUrl}
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-[0.08] pointer-events-none"
        />
      )}
      <div className="relative z-10">
        <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-3">
          Market Confidence
        </p>
        <div className="flex items-end gap-3 mb-3">
          <span
            className="text-5xl font-display font-black tracking-tighter"
            style={{ color }}
          >
            {score}
          </span>
          <span className="text-lg text-[#A1A1AA] font-display font-bold mb-1">/100</span>
        </div>
        <div
          className="inline-flex items-center gap-2 px-3 py-1 border text-xs uppercase font-bold tracking-wider"
          style={{
            color,
            borderColor: `${color}40`,
            backgroundColor: `${color}15`,
          }}
        >
          <span
            className="w-2 h-2 rounded-full animate-pulse-glow"
            style={{ backgroundColor: color }}
          />
          {status}
        </div>
        <div className="mt-4 w-full h-1 bg-[#1F1F1F]">
          <div
            className="h-full transition-all duration-700"
            style={{ width: `${score}%`, backgroundColor: color }}
          />
        </div>
      </div>
    </div>
  );
}
