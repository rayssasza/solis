import logging
import smtplib
from datetime import date, datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

from config import SolisConfig

logger = logging.getLogger(__name__)

NOMES_USINAS = {
    "111111110101010101010101": "Nome da Usina",
    "111111110101010101010101": "Nome da Usina",
    "111111110101010101010101": "Nome da Usina",
    "111111110101010101010101": "Nome da Usina",
    "111111110101010101010101": "Nome da Usina",
}

_HTML_REPORT_BASE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0F172A; color: #E2E8F0; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 680px; margin: 30px auto; background: #1E293B; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.5); }}
    .header {{ background: linear-gradient(135deg, #F59E0B, #EF4444); padding: 28px 32px; text-align: center; }}
    .header h1 {{ margin:0; font-size: 22px; color: #fff; letter-spacing:1px; }}
    .header p {{ margin:6px 0 0; color: rgba(255,255,255,0.85); font-size: 13px; }}
    .section {{ padding: 24px 32px; border-bottom: 1px solid #334155; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .kpi-card {{ background: #0F172A; border-radius: 8px; padding: 14px 16px; text-align: center; }}
    .kpi-card .value {{ font-size: 22px; font-weight: 700; color: #F59E0B; }}
    .kpi-card .label {{ font-size: 11px; color: #94A3B8; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #0F172A; color: #94A3B8; padding: 10px 12px; text-align: left; font-weight: 600; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #1E293B; color: #CBD5E1; }}
    tr:nth-child(even) td {{ background: #0F172A22; }}
    .badge-ok {{ display:inline-block; background:#16a34a; color:#fff; border-radius:4px; padding:2px 8px; font-size:11px; }}
    .badge-warn{{ display:inline-block; background:#d97706; color:#fff; border-radius:4px; padding:2px 8px; font-size:11px; }}
    .badge-err {{ display:inline-block; background:#dc2626; color:#fff; border-radius:4px; padding:2px 8px; font-size:11px; }}
    .footer {{ padding: 16px 32px; text-align: center; font-size: 11px; color: #f0f2f5; }}
    img.chart {{ width: 100%; border-radius: 8px; margin-top: 8px; }}
    .no-chart {{ text-align:center; color:#64748b; font-size:13px; padding:16px 0; }}
  </style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>&#9728;&#65039; Relatório das Usinas Solares</h1>
    <p>Dados referentes a {report_date} &nbsp;|&nbsp; Gerado em {generated_at}</p>
  </div>
  {stations_html}
  <div class="footer">Este relatório foi gerado automaticamente pelo Sistema de Monitoramento.</div>
</div>
</body>
</html>
"""

_HTML_STATION_SECTION = """\
  <div class="section">
    <h2 style="color: #F8FAFC; font-size: 18px; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 0; margin-bottom: 16px;">{station_name}</h2>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="value">{yesterday_energy}</div><div class="label">Geração (Ontem)</div></div>
      <div class="kpi-card"><div class="value">{yesterday_income}</div><div class="label">Rendimento (Ontem)</div></div>
      <div class="kpi-card"><div class="value">{full_hour}</div><div class="label">Horas Plena Carga (Ontem)</div></div>
      <div class="kpi-card"><div class="value">{power}</div><div class="label">Potencia (Hoje)</div></div>
      <div class="kpi-card"><div class="value">{all_income}</div><div class="label">Ganho Total (BRL)</div></div>
      <div class="kpi-card"><div class="value">{all_energy}</div><div class="label">Geração Histórica Total</div></div>
      <div class="kpi-card" style="grid-column: span 3;"><div class="value" style="font-size: 14px; margin-top: 6px;">{station_status_badge}</div><div class="label">Status Atual</div></div>
    </div>
    <h3 style="font-size: 14px; color: #94A3B8; margin-top: 20px; margin-bottom: 10px;">Histórico - Últimos 7 Dias</h3>
    <table><tr><th>Data</th><th>Geração (kWh)</th><th>Variação</th></tr>{seven_day_rows}</table>
    <h3 style="font-size: 14px; color: #94A3B8; margin-top: 20px; margin-bottom: 10px;">
      Gráfico - Mês Anterior <span style="font-weight:normal; font-size:12px;">(Mensal: {month_income} | {month_full_hour})</span>
    </h3>
    {chart_section}
  </div>
"""

_HTML_ALERT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <style>
    body  {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0F172A; color:#E2E8F0; margin:0; padding:0; }}
    .box  {{ max-width:560px; margin:30px auto; background:#1E293B; border-radius:12px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.5); }}
    .top  {{ background:#dc2626; padding:22px 28px; }}
    .top h1 {{ margin:0; font-size:19px; color:#fff; }}
    .body {{ padding:24px 28px; }}
    .detail {{ background:#0F172A; border-radius:8px; padding:14px 18px; font-size:13px; line-height:1.8; }}
    .label  {{ color:#94A3B8; }}
    .value  {{ color:#F8FAFC; font-weight:600; }}
    .footer {{ padding:14px 28px; text-align:center; font-size:11px; color:#475569; border-top:1px solid #334155; }}
  </style>
</head>
<body>
<div class="box">
  <div class="top">
    <h1>Alerta de Anomalia - Usina Solar</h1>
  </div>
  <div class="body">
    <p style="margin:0 0 16px;color:#CBD5E1;">{alert_description}</p>
    <div class="detail">
      <div><span class="label">Tipo de alerta: </span><span class="value">{alert_type}</span></div>
      <div><span class="label">Horário: </span><span class="value">{alert_time}</span></div>
      <div><span class="label">Usina: </span><span class="value">{station_id}</span></div>
      <div><span class="label">Detalhes: </span><span class="value">{alert_details}</span></div>
    </div>
  </div>
  <div class="footer", style="color:#f2f3f6">Sistema de Monitoramento - Alerta Automático</div>
</div>
</body>
</html>
"""

def _safe(value: Any, unit: str = "", decimals: int = 1, default: str = "-") -> str:
    try:
        return f"{float(value):.{decimals}f}{unit}"
    except (TypeError, ValueError):
        return default

def _status_badge(state: Any) -> str:
    mapping = {
        "0": '<span class="badge-warn">Aguardando</span>',
        "1": '<span class="badge-ok">Normal</span>',
        "2": '<span class="badge-warn">Alarme</span>',
        "3": '<span class="badge-err">Offline</span>',
    }
    return mapping.get(str(state), '<span class="badge-warn">Desconhecido</span>')

def _build_7day_rows(seven_days: list[dict[str, Any]]) -> str:
    if not seven_days:
        return '<tr><td colspan="3" style="text-align:center;color:#f2f3f6;">Sem dados disponíveis</td></tr>'

    rows = []
    prev_energy: Optional[float] = None
    for item in seven_days:
        d = item.get("date", "-")
        e = item.get("energy_kwh", 0.0)

        if prev_energy is not None and prev_energy > 0:
            delta = ((e - prev_energy) / prev_energy) * 100
            arrow = "▲" if delta >= 0 else "▼"
            color = "#22c55e" if delta >= 0 else "#ef4444"
            variation = f'<span style="color:{color}">{arrow} {abs(delta):.2f}%</span>'
        else:
            variation = "-"

        rows.append(f"<tr><td>{d}</td><td>{e:.2f}</td><td>{variation}</td></tr>")
        prev_energy = e

    return "\n".join(rows)

class EmailSender:
    def __init__(self, config: SolisConfig):
        self._cfg = config

    def _send(self, msg: MIMEMultipart, recipients: list[str]) -> bool:
        try:
            with smtplib.SMTP(self._cfg.smtp_host, self._cfg.smtp_port, timeout=30) as server:
                server.ehlo()
                if self._cfg.smtp_use_tls:
                    server.starttls()
                if self._cfg.smtp_username:
                    server.login(self._cfg.smtp_username, self._cfg.smtp_password)
                server.sendmail(
                    self._cfg.email_from,
                    recipients,
                    msg.as_string(),
                )
            return True
        except Exception as exc:
            print(f"\n[ERRO SMTP/REDE]: Não foi possivel enviar o e-mail, favor verificar. {exc}\n")
            return False

    def send_daily_reports_batch(self, stations_data: list[dict[str, Any]]) -> bool:
        try:
            yesterday_date = date.today() - timedelta(days=1)
            yesterday_str = yesterday_date.strftime("%d/%m/%Y")

            sections_html = []
            attached_images = []

            for st in stations_data:
                sid = st.get("station_id", "")
                nome = st.get("nome_usina", sid)
                detail = st.get("station_detail", {})
                seven_days = st.get("seven_days", [])
                chart_path = st.get("chart_30d_path", "")

                has_chart = bool(chart_path and Path(chart_path).exists())
                cid = f"chart_{sid}"

                chart_section = (
                    f'<img class="chart" src="cid:{cid}" alt="Gráfico do Mês Anterior">'
                    if has_chart
                    else '<p class="no-chart">Gráfico indisponível para este relatório.</p>'
                )

                if has_chart:
                    attached_images.append((chart_path, cid))

                if seven_days:
                    y_energy = float(seven_days[-1].get("energy_kwh", 0.0))
                else:
                    y_energy = 0.0
                yesterday_energy_str = f"{y_energy:.1f} kWh"

                try:
                    capacity = float(detail.get("capacity") or 0.0)
                except (TypeError, ValueError):
                    capacity = 0.0

                try:
                    price = float(detail.get("price") or 0.90)
                except (TypeError, ValueError):
                    price = 0.90

                y_income = y_energy * price
                yesterday_income_str = f"{y_income:.2f} BRL"

                y_full_hour = (y_energy / capacity) if capacity > 0 else 0.0
                yesterday_full_hour_str = f"{y_full_hour:.2f} h"

                try:
                    all_val = float(detail.get("allEnergy", 0))
                    all_unit = detail.get("allEnergyStr", "MWh").strip().upper()
                    if all_unit in ["MWH", "MW"]:
                        all_val = all_val * 1000.0
                    elif all_unit in ["GWH", "GW"]:
                        all_val = all_val * 1000000.0
                    all_energy_str = f"{all_val:,.0f} kWh".replace(",", ".")
                except (TypeError, ValueError):
                    all_energy_str = "-"

                try:
                    a_income = float(detail.get("allInCome") or 0.0)
                except (TypeError, ValueError):
                    a_income = 0.0
                all_income_str = f"{a_income:.4f}k"

                try:
                    m_income = float(detail.get("monthInCome") or 0.0)
                except (TypeError, ValueError):
                    m_income = 0.0
                month_income_str = f"{m_income:.4f}k BRL"

                try:

                    m_energy_val = float(st.get("last_month_energy", 0.0))

                    m_income = m_energy_val * price
                    month_income_str = f"{m_income:.2f}k BRL"

                    m_full_hour = (m_energy_val / capacity) if capacity > 0 else 0.0
                    month_full_hour_str = f"{m_full_hour:.2f} h"
                except Exception:
                    month_income_str = "0.00 BRL"
                    month_full_hour_str = "0.00 h"

                section = _HTML_STATION_SECTION.format(
                    station_name=nome,
                    yesterday_energy=yesterday_energy_str,
                    yesterday_income=yesterday_income_str,
                    full_hour=yesterday_full_hour_str,
                    power=_safe(detail.get("power"), " kW"),
                    all_income=all_income_str,
                    all_energy=all_energy_str,
                    station_status_badge=_status_badge(detail.get("state")),
                    seven_day_rows=_build_7day_rows(seven_days),
                    month_income=month_income_str,
                    month_full_hour=month_full_hour_str,
                    chart_section=chart_section,
                )
                sections_html.append(section)

            full_html = _HTML_REPORT_BASE.format(
                report_date=yesterday_str,
                generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
                stations_html="\n".join(sections_html)
            )

            msg = MIMEMultipart("related")
            msg["Subject"] = f"Relatório das Usinas Solares - {yesterday_str}"
            msg["From"] = self._cfg.email_from
            msg["To"] = ", ".join(self._cfg.report_recipients)

            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(full_html, "html", "utf-8"))
            msg.attach(alt)

            for path, c_id in attached_images:
                with open(path, "rb") as f:
                    img = MIMEImage(f.read(), name=Path(path).name)
                    img.add_header("Content-ID", f"<{c_id}>")
                    img.add_header("Content-Disposition", "inline", filename=Path(path).name)
                    msg.attach(img)

            return self._send(msg, self._cfg.report_recipients)

        except Exception as exc:
            print(f"\n[ERRO AO MONTAR RELATÓRIO]: {exc}\n")
            return False

    def send_alert(
        self,
        alert_type: str,
        description: str,
        details: str,
        station_id: str,
    ) -> bool:
        nome_usina = NOMES_USINAS.get(station_id, station_id)

        html = _HTML_ALERT_TEMPLATE.format(
            alert_description=description,
            alert_type=alert_type,
            alert_time=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            station_id=nome_usina,
            alert_details=details,
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ALERTA - {alert_type} | {nome_usina}"
        msg["From"] = self._cfg.email_from
        msg["To"] = ", ".join(self._cfg.alert_recipients)
        msg.attach(MIMEText(html, "html", "utf-8"))

        return self._send(msg, self._cfg.alert_recipients)

    def send_test_report(self) -> bool:
        fake_detail: dict[str, Any] = {
            "capacity": 12.3,
            "price": 1.23,
            "power": 1.2,
            "allEnergy": 123.4,
            "allEnergyStr": "MWh",
            "allInCome": 1234.56,
            "monthEnergy": 123.4,
            "monthInCome": 123.4,
            "state": "1",
        }
        fake_days = [
            {"date": f"2026-04-{str(i).zfill(2)}", "energy_kwh": 30.0 + i}
            for i in range(1, 8)
        ]

        station_id = list(NOMES_USINAS.keys())[0]
        fake_data = [
            {
                "station_id": station_id,
                "nome_usina": NOMES_USINAS[station_id],
                "station_detail": fake_detail,
                "seven_days": fake_days,
                "thirty_days": fake_days,
                "chart_30d_path": ""
            }
        ]
        return self.send_daily_reports_batch(fake_data)

    def send_test_alert(self) -> bool:
        station_id = list(NOMES_USINAS.keys())[0]
        return self.send_alert(
            alert_type="Teste de Alerta",
            description="Este é um e-mail de teste, por favor desconsiderar.",
            details="Teste enviado automáticamente pelo Sistema de Monitoramento.",
            station_id=station_id,
        )
