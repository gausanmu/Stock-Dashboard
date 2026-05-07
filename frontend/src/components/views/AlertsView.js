import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Bell, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

export default function AlertsView() {
  const [settings, setSettings] = useState({ email: "", enabled: false });
  const [changes, setChanges] = useState([]);

  useEffect(() => {
    api.getAlertSettings().then(r => setSettings(r.data || {})).catch(() => {});
    api.getRegimeChanges(50).then(r => setChanges(r.data || [])).catch(() => {});
  }, []);

  const save = async () => {
    try {
      await api.updateAlertSettings(settings);
      toast.success("Alert settings saved");
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <Bell className="w-5 h-5 text-amber-400" />
        <h1 className="text-2xl font-bold text-white">Alerts</h1>
      </div>

      <div className="bg-white/[0.04] border border-white/10 rounded-xl p-4 max-w-xl space-y-3">
        <div>
          <label className="text-[10px] uppercase tracking-widest text-slate-400">Email</label>
          <Input
            value={settings.email}
            onChange={(e) => setSettings({ ...settings, email: e.target.value })}
            className="bg-white/5 border-white/10 text-white mt-1"
            placeholder="you@example.com"
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-300">Enable email alerts on regime changes</span>
          <Switch checked={settings.enabled} onCheckedChange={(v) => setSettings({ ...settings, enabled: v })} />
        </div>
        <Button onClick={save} className="bg-emerald-500 text-slate-950 font-semibold">Save</Button>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-2">Recent regime changes</h2>
        <div className="bg-white/[0.03] border border-white/10 rounded-xl divide-y divide-white/5">
          {changes.length === 0 && (
            <div className="px-4 py-6 text-sm text-slate-500 text-center">No regime changes yet — they appear after subsequent scans.</div>
          )}
          {changes.map((c, i) => (
            <div key={i} className="px-4 py-3 flex items-center gap-3 text-sm">
              <span className="font-semibold text-white w-28">{c.ticker}</span>
              <span className="text-slate-400 flex-1 truncate">{c.name}</span>
              <span className="text-rose-300 text-xs">{c.old_regime}</span>
              <ArrowRight className="w-3 h-3 text-slate-500" />
              <span className="text-emerald-300 text-xs">{c.new_regime}</span>
              <span className="text-slate-500 text-xs ml-3">{new Date(c.timestamp).toLocaleString("en-IN")}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
