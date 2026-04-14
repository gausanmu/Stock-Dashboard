import os
import asyncio
import logging

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self):
        self.api_key = os.environ.get("RESEND_API_KEY", "")
        self.sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
        self.recipient = os.environ.get("ALERT_EMAIL", "")

    def is_configured(self):
        return bool(self.api_key and self.recipient)

    async def send_regime_change_alert(self, stock, old_regime, new_regime):
        if not self.is_configured():
            logger.info(f"Alert queued (no RESEND_API_KEY): {stock.get('ticker')} {old_regime}->{new_regime}")
            return None
        try:
            import resend
            resend.api_key = self.api_key
            color_map = {"SPRINTER": "#00E676", "COMPOUNDER": "#2979FF", "REVERSAL": "#FFB300", "AVOID": "#FF3D00", "NEUTRAL": "#A1A1AA"}
            color = color_map.get(new_regime, "#A1A1AA")
            trade_types = ", ".join(stock.get("trade_types", []))
            html = f"""<div style="font-family:'Courier New',monospace;background:#0a0a0a;color:#fff;padding:24px;max-width:600px;">
<h2 style="color:#fff;margin:0 0 4px;">REGIME CHANGE ALERT</h2>
<p style="color:#666;font-size:11px;margin:0 0 20px;">NSE Quant Engine</p>
<div style="background:#111;border:1px solid #222;padding:16px;margin-bottom:16px;">
<h3 style="margin:0 0 4px;font-size:18px;">{stock.get('ticker','')}</h3>
<p style="color:#888;font-size:11px;margin:0 0 12px;">{stock.get('name','')}</p>
<p style="margin:4px 0;font-size:14px;"><span style="color:#FF3D00;text-decoration:line-through;">{old_regime}</span> <span style="color:#666;">&rarr;</span> <span style="color:{color};font-weight:bold;">{new_regime}</span></p>
</div>
<table style="width:100%;font-size:12px;color:#888;border-collapse:collapse;">
<tr><td style="padding:4px 0;">Price</td><td style="text-align:right;color:#fff;">&#8377;{stock.get('price',0)}</td></tr>
<tr><td style="padding:4px 0;">Quality</td><td style="text-align:right;color:#fff;">{stock.get('quality_score',0)}/100</td></tr>
<tr><td style="padding:4px 0;">RSI</td><td style="text-align:right;color:#fff;">{stock.get('rsi',0)}</td></tr>
<tr><td style="padding:4px 0;">Trade Types</td><td style="text-align:right;color:#fff;">{trade_types}</td></tr>
</table></div>"""
            params = {
                "from": self.sender,
                "to": [self.recipient],
                "subject": f"[NSE Quant] {stock.get('ticker','')}: {old_regime} -> {new_regime}",
                "html": html,
            }
            email = await asyncio.to_thread(resend.Emails.send, params)
            logger.info(f"Alert sent: {stock.get('ticker')} {old_regime}->{new_regime}")
            return email
        except Exception as e:
            logger.error(f"Alert send failed: {e}")
            return None

    async def send_daily_summary(self, summary):
        if not self.is_configured():
            return None
        try:
            import resend
            resend.api_key = self.api_key
            changes = summary.get("regime_changes", [])
            rows = ""
            for c in changes[:20]:
                rows += f"<tr><td style='padding:3px 6px;color:#fff;'>{c.get('ticker','')}</td><td style='padding:3px 6px;color:#FF3D00;'>{c.get('old_regime','')}</td><td style='padding:3px 6px;color:#666;'>&rarr;</td><td style='padding:3px 6px;color:#00E676;font-weight:bold;'>{c.get('new_regime','')}</td></tr>"
            html = f"""<div style="font-family:'Courier New',monospace;background:#0a0a0a;color:#fff;padding:24px;max-width:600px;">
<h2 style="color:#fff;">DAILY SUMMARY</h2>
<p style="color:#666;font-size:11px;">NSE Quant Engine | {summary.get('date','')}</p>
<div style="background:#111;border:1px solid #222;padding:16px;margin:16px 0;">
<p style="margin:4px 0;">Stocks: <b>{summary.get('total',0)}</b> | Confidence: <b>{summary.get('confidence',0)}/100</b> | Changes: <b>{len(changes)}</b></p>
</div>
{f'<table style="width:100%;font-size:12px;border-collapse:collapse;">{rows}</table>' if rows else '<p style="color:#555;">No regime changes.</p>'}
</div>"""
            params = {
                "from": self.sender,
                "to": [self.recipient],
                "subject": f"[NSE Quant] Daily Summary - {summary.get('date','')}",
                "html": html,
            }
            return await asyncio.to_thread(resend.Emails.send, params)
        except Exception as e:
            logger.error(f"Daily summary failed: {e}")
            return None
