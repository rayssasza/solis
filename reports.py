import logging
import os
import tempfile
from typing import Optional

from datetime import datetime, timedelta
from alerts import ALARMES_TRADUCAO
from api_client import SolisClient
from charts import generate_30day_chart
from email_sender import EmailSender, NOMES_USINAS
from config import SolisConfig

logger = logging.getLogger(__name__)

def get_yesterdays_alarms_html(api_client, station_id: str) -> str:
    try:
        alarm_data = api_client.get_alarm_list(station_id=station_id, page=1, page_size=50)
        records = (
            alarm_data.get("page", {}).get("records")
            or alarm_data.get("records")
            or alarm_data.get("alarmInfos")
            or []
        )

        if not records:
            return "<p><em>Nenhum alarme registrado ontem.</em></p>"

        ontem = (datetime.now() - timedelta(days=1)).date()
        alarmes_ontem = []

        for alarm in records:
            raw_time = alarm.get("alarmBeginTime") or alarm.get("alarmTime") or alarm.get("time")
            try:
                if isinstance(raw_time, (int, float)):
                    if raw_time > 2000000000:
                        raw_time = raw_time / 1000
                    dt_alarm = datetime.fromtimestamp(raw_time)
                elif isinstance(raw_time, str):
                    dt_alarm = datetime.strptime(raw_time[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                else:
                    continue
            except Exception:
                continue

            if dt_alarm.date() == ontem:
                alarm_msg = alarm.get("alarmMessage") or alarm.get("alarmMsg") or alarm.get("message") or "Sem detalhes"
                alarm_name = alarm.get("alarmName") or alarm.get("name") or ""

                if not alarm_name or alarm_name == "unknown" or alarm_name == "Alarme Desconhecido":
                    alarm_name = alarm_msg

                alarm_name_clean = str(alarm_name).strip().strip(".")
                alarm_msg_clean = str(alarm_msg).strip().strip(".")

                nome_final = alarm_name_clean
                if alarm_name_clean in ALARMES_TRADUCAO:
                    nome_final = ALARMES_TRADUCAO[alarm_name_clean]
                elif alarm_msg_clean in ALARMES_TRADUCAO:
                    nome_final = ALARMES_TRADUCAO[alarm_msg_clean]

                hora_str = dt_alarm.strftime("%H:%M:%S")
                alarmes_ontem.append(f"<li><strong>{hora_str}</strong> - {nome_final}</li>")

        if not alarmes_ontem:
            return "<p><em>Nenhum alarme registrado ontem.</em></p>"

        html_lista = "<ul>\n" + "\n".join(alarmes_ontem) + "\n</ul>"
        return html_lista

    except Exception as e:
        return f"<p><em>Não foi possível carregar os alarmes de ontem.</em></p>"

def run_daily_report_all(
    api_client: SolisClient,
    email_sender: EmailSender,
    config: SolisConfig,
    charts_dir: Optional[str] = None,
) -> bool:
    output_dir = charts_dir or tempfile.gettempdir()
    stations_data = []

    for sid in config.station_ids:
        try:
            detail = api_client.get_station_detail(sid)
        except Exception:
            detail = {}

        try:
            hist = api_client.get_historical_data(sid)
            seven_days = hist["seven_days"]
            thirty_days = hist["thirty_days"]
            prev_month_data = hist.get("prev_month_data", [])
            last_month_energy = hist.get("last_month_energy", 0.0)
        except Exception:
            seven_days = []
            thirty_days = []
            prev_month_data = []
            last_month_energy = 0.0

        chart_path = ""

        if prev_month_data:
            try:
                chart_path = generate_30day_chart(prev_month_data, output_dir=output_dir, prefix=sid)
            except Exception as e:
                print(f"ERRO AO GERAR GRÁFICO DA USINA, {sid}: {e} CONFERIR LOGS")

        nome = NOMES_USINAS.get(sid, sid)

        stations_data.append({
            "station_id": sid,
            "nome_usina": nome,
            "station_detail": detail,
            "seven_days": seven_days,
            "thirty_days": thirty_days,
            "last_month_energy": last_month_energy,
            "chart_30d_path": chart_path
        })

    try:
        return email_sender.send_daily_reports_batch(stations_data)
    except Exception:
        return False
    finally:
        for st in stations_data:
            p = st.get("chart_30d_path")
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
