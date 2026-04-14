import Marquee from "react-fast-marquee";

const LABELS = {
  NIFTY50: "NIFTY 50",
  BANKNIFTY: "BANK NIFTY",
  USDINR: "USD/INR",
  CRUDE: "CRUDE OIL",
};

export default function MacroTicker({ data }) {
  const entries = Object.entries(data || {});
  if (!entries.length) return null;

  return (
    <div
      data-testid="macro-ticker"
      className="h-9 border-b border-[#1F1F1F] flex items-center bg-[#050505] overflow-hidden"
    >
      <Marquee speed={30} gradient={false} pauseOnHover>
        {entries.map(([key, val]) => (
          <span key={key} className="inline-flex items-center gap-2 mx-6 text-xs tracking-wider">
            <span className="text-[#A1A1AA] uppercase">{LABELS[key] || key}</span>
            <span className="text-white font-medium">
              {val.price?.toLocaleString("en-IN")}
            </span>
            <span
              className={
                val.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"
              }
            >
              {val.change_pct >= 0 ? "+" : ""}
              {val.change_pct?.toFixed(2)}%
            </span>
          </span>
        ))}
      </Marquee>
    </div>
  );
}
