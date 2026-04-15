import logging
from datetime import datetime
from typing import Any

from api_client import SolisClient
from email_sender import EmailSender
from config import SolisConfig

logger = logging.getLogger(__name__)

_alerted_cache: dict[str, datetime] = {}

STATION_STATE_MAP = {
    "0": "Aguardando",
    "1": "Normal",
    "2": "Alarme",
    "3": "Offline",
}

ALARMES_TRADUCAO = {
    "NO-Grid": "Queda ou ausência de energia da rede elétrica",
    "UN-G-V": "Subtensão na rede elétrica",
    "UN-G-V01": "Tensão da rede abaixo do limite mínimo de 1º nível",
    "UN-G-V02": "Valor transitório da tensão da rede abaixo de 0,85 do valor nominal",
    "OV-G-V": "Sobretensão na rede elétrica",
    "OV-G-V 01": "Tensão da rede acima do limite de sobretensão de 1º nível pelo tempo configurado",
    "OV-G-V 02": "Valor transitório da tensão da rede acima de 1,35 vezes o pico nominal",
    "OV-G-V 03": "Tensão da rede acima do limite de sobretensão de 10 minutos",
    "OV-G-V 04": "Tensão da rede acima do limite de sobretensão de 2º nível",
    "OV-G-V 05": "Valor RMS ou transitório da tensão da rede acima do limite configurado",
    "UN-G-F": "Subfrequência na rede elétrica",
    "UN-G-F01": "Frequência da rede abaixo do limite mínimo de 1º nível",
    "UN-G-F02": "Frequência da rede abaixo do limite mínimo de 2º nível",
    "OV-G-F": "Sobrefrequência na rede elétrica",
    "OV-G-F01": "Frequência da rede acima do limite máximo de 1º nível",
    "OV-G-F02": "Frequência da rede acima do limite máximo de 2º nível",
    "G-PHASE": "Desequilíbrio nas fases da rede elétrica",
    "G-F-FLU": "Frequência da rede instável ou anormal",
    "OV-G-I": "Sobrecorrente de saída da rede",
    "IGFOL-F": "Erro no rastreamento da corrente da rede",
    "PHASE-FAULT": "Ângulo de fase da rede elétrica anormal",
    "Backfeed_Iac": "Corrente de retroalimentação AC",
    "OV-DC": "Sobretensão no lado DC",
    "OV-DC01": "Sobretensão no barramento DC1",
    "OV-DC02": "Sobretensão no barramento DC2",
    "BoostFal": "Falha no circuito de elevação DC (boost)",
    "OV-BUS": "Sobretensão no barramento DC",
    "UNB-BUS": "Tensão do barramento DC e meia tensão inconsistentes",
    "UN-BUS": "Subtensão no barramento DC",
    "UN-BUS01": "Subtensão no barramento DC",
    "UN-BUS02": "Leitura anormal da tensão do barramento DC",
    "Vbus-Sam": "Erro de amostragem da tensão do barramento DC",
    "DC-INTF.": "Corrente de entrada DC anormal",
    "Reve-DC": "Conexão DC invertida",
    "PvMidIso": "Proteção de baixa isolação no ponto médio do PV",
    "PVGndRun": "Aterramento do terminal PV durante operação",
    "PV ISO-PRO 01": "Baixa isolação do PV para terra (negativo)",
    "PV ISO-PRO 02": "Baixa isolação do PV para terra (positivo)",
    "ILeak-PRO 01": "Proteção por corrente de fuga nível 1 (30mA)",
    "ILeak-PRO 02": "Proteção por corrente de fuga nível 2 (60mA)",
    "ILeak-PRO 03": "Proteção por corrente de fuga nível 3 (150mA)",
    "ILeak-PRO 04": "Proteção por corrente de fuga nível 4 (300mA)",
    "ILeak-Check": "Falha ou autodiagnóstico do sensor de corrente de fuga",
    "RelayChk-FAIL": "Falha no autoteste do relé",
    "DSP-B-Sam-Fau": "Erro ou ausência de software no DSP",
    "DSP-B-FAULT": "Falha de comunicação entre DSP mestre e escravo",
    "DSP-B-Com-Fau": "Software DSP ausente",
    "DSP-SelfCheck": "Firmware DSP incompatível com o hardware",
    "INI-FAULT": "Falha de inicialização do DSP",
    "DCInj-FAULT": "Injeção DC excessiva na saída AC",
    "12Power-FAULT": "Falha na fonte de alimentação 12V",
    "UN-TEM": "Temperatura ambiente muito baixa",
    "OV-TEM": "Temperatura interna excessiva nos IGBTs",
    "AFCI-Check": "Autoteste AFCI (detecção de arco) ativo",
    "ARC-FAULT": "Arco elétrico DC detectado",
    "IG-AD": "Erro de amostragem da corrente da rede",
    "IGBT-OV-I": "Sobrecorrente nos IGBTs",
    "GRID-INTF02": "Interferência severa na rede elétrica",
    "FailSafe": "Falha de comunicação com EPM ou medidor",
    "CT-Failsafe": "Perda de comunicação do TC com o medidor",
    "M-ComFailSafe": "Falha de comunicação do medidor",
    "M-VFailSafe": "Leitura de tensão do medidor anormal",
    "RS485AllFail": "Falha total na comunicação RS485",
    "RS485 Fail": "Falha parcial na comunicação RS485",
    "OV-IgTr": "Sobrecorrente temporária da rede",
    "OV-Vbatt": "Sobretensão da bateria",
    "UN-Vbatt": "Subtensão da bateria",
    "NO-Battery": "Bateria não conectada",
    "OV-Vbackup": "Tensão do backup acima do limite configurado",
    "Over-Load": "Carga do backup sobrecarregada",
    "BatName-FAIL": "Marca de bateria selecionada incorretamente",
    "CAN_Comm_FAIL": "Falha de comunicação CAN com a bateria",
    "DSP_Comm_FAIL": "Falha de comunicação do DSP",
    "Alarm1-BMS": "Alarme do sistema BMS da bateria",
    "Alarm2-BMS": "Segundo alarme do sistema BMS da bateria",
    "LG-BMS-Fault": "Falha no BMS da bateria LG",
    "LG-Comm-FAIL": "Falha de comunicação com bateria LG",
    "DRM_LINK_FAIL": "Falha de comunicação DRM",
    "GRID-INTF": "Interferência na Rede (Pico ou Oscilação)",
}

def _is_daytime() -> bool:
    hour = datetime.now().hour
    return 6 <= hour < 20

def _should_alert(alert_key: str) -> bool:
    if alert_key in _alerted_cache:
        return False
    return True

def _mark_alerted(alert_key: str) -> None:
    _alerted_cache[alert_key] = datetime.now()

def _clear_alert(alert_key: str) -> None:
    _alerted_cache.pop(alert_key, None)

def check_station_status(
    station_id: str,
    station_detail: dict[str, Any],
    email_sender: EmailSender,
) -> None:
    state = str(station_detail.get("state", ""))
    exception_flag = station_detail.get("stateExceptionFlag", 0)
    station_label = STATION_STATE_MAP.get(state, f"Desconhecido ({state})")

    alert_key = f"station_offline_{station_id}"
    if state == "3":
        if _should_alert(alert_key):
            sent = email_sender.send_alert(
                alert_type="Usina Offline",
                description=(
                    "A usina solar foi detectada como <strong>OFFLINE</strong>. "
                    "Verifique a conectividade do inversor com a Solis."
                ),
                details="Diagnóstico: O datalogger (antena Wi-Fi) parou de se comunicar com o servidor da Solis.",
                station_id=station_id,
            )
            if sent:
                _mark_alerted(alert_key)
    else:
        if alert_key in _alerted_cache:
            email_sender.send_alert(
                alert_type="✅ Usina Online Novamente",
                description=(
                    "A comunicação com a usina foi <strong>restabelecida</strong>! "
                    "A internet voltou e o inversor está enviando dados normalmente."
                ),
                details=f"Status da Usina: {station_label} (Operação normalizada)",
                station_id=station_id,
            )
        _clear_alert(alert_key)

    exception_key = f"station_exception_{station_id}"
    try:
        flag_value = int(exception_flag)
    except (TypeError, ValueError):
        flag_value = 0

    if flag_value != 0:
        if _should_alert(exception_key):
            sent = email_sender.send_alert(
                alert_type="Exceção Anormal na Usina",
                description=(
                    "A usina retornou um <strong>flag de exceção anormal</strong> "
                    "no monitoramento. Pode indicar falha de hardware ou comunicação."
                ),
                details=(
                    f"state={state} ({station_label}) | "
                    f"stateExceptionFlag={exception_flag}"
                ),
                station_id=station_id,
            )
            if sent:
                _mark_alerted(exception_key)
    else:

        if exception_key in _alerted_cache:
            email_sender.send_alert(
                alert_type="✅ Exceção Resolvida",
                description="O flag de exceção de hardware da usina voltou ao normal (0).",
                details=f"Status Atual: {station_label}",
                station_id=station_id,
            )
        _clear_alert(exception_key)

def check_power_zero(
    station_id: str,
    station_detail: dict[str, Any],
    email_sender: EmailSender,
) -> None:
    if not _is_daytime():
        return

    try:
        power = float(
            station_detail.get("power")
            or station_detail.get("pac")
            or 0
        )
    except (TypeError, ValueError):
        power = 0.0

    state = str(station_detail.get("state", ""))
    alert_key = f"power_zero_{station_id}"

    if state == "1" and power == 0.0:
        if _should_alert(alert_key):
            sent = email_sender.send_alert(
                alert_type="Potência Zero Durante o Dia",
                description=(
                    "A usina esta <strong>em estado Normal</strong>, porém a "
                    "potência atual registrada é <strong>0 kW</strong> durante "
                    "o horário de geração solar esperado. Pode indicar falha no "
                    "inversor. Verifique ou avise a equipe responsável."
                ),
                details=f"Geração de energia interrompida às {datetime.now().strftime('%H:%M')}. Verifique o quadro de disjuntores ou o inversor.",
                station_id=station_id,
            )
            if sent:
                _mark_alerted(alert_key)
    else:
        if power > 0:
            _clear_alert(alert_key)

def check_active_alarms(
    station_id: str,
    email_sender: EmailSender,
    api_client: SolisClient,
) -> None:
    try:
        alarm_data = api_client.get_alarm_list(station_id=station_id, page=1, page_size=20)

        records = (
            alarm_data.get("page", {}).get("records")
            or alarm_data.get("records")
            or alarm_data.get("alarmInfos")
            or []
        )

        if not records:
            return

        for alarm in records:
            status = str(alarm.get("alarmStatus", "1"))
            if status != "1":
                continue

            alarm_msg = alarm.get("alarmMessage") or alarm.get("alarmMsg") or alarm.get("message") or "Sem detalhes"
            alarm_name = alarm.get("alarmName") or alarm.get("name") or ""
            alarm_code = str(alarm.get("alarmCode") or alarm.get("id") or "")

            if "Inefficient Power Plants" in alarm_msg or "Inefficient Power Plants" in alarm_name or "1D4C3" in alarm_code:
                continue

            if not alarm_name or alarm_name == "unknown" or alarm_name == "Alarme Desconhecido":
                alarm_name = alarm_msg

            alarm_name_clean = alarm_name.strip().strip(".")
            alarm_msg_clean = alarm_msg.strip().strip(".")

            alarm_name = alarm_name_clean

            if alarm_name_clean in ALARMES_TRADUCAO:
                alarm_name = ALARMES_TRADUCAO[alarm_name_clean]
            elif alarm_msg_clean in ALARMES_TRADUCAO:
                alarm_name = ALARMES_TRADUCAO[alarm_msg_clean]

            raw_time = alarm.get("alarmBeginTime") or alarm.get("alarmTime") or alarm.get("time")
            alarm_time_str = "-"

            try:
                if isinstance(raw_time, (int, float)):
                    if raw_time > 2000000000:
                        raw_time = raw_time / 1000
                    dt_alarm = datetime.fromtimestamp(raw_time)
                elif isinstance(raw_time, str):
                    dt_alarm = datetime.strptime(raw_time[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                else:
                    dt_alarm = datetime.now()

                alarm_time_str = dt_alarm.strftime("%d/%m/%Y %H:%M:%S")

                if (datetime.now() - dt_alarm).days > 3:
                    continue
            except Exception:
                pass

            alarm_level = alarm.get("alarmLevel") or alarm.get("level") or "-"
            raw_id = str(alarm.get("id") or alarm.get("alarmId") or "-1")

            alarm_key = f"alarm_{station_id}_{alarm_name}"

            if not _should_alert(alarm_key):
                continue

            sent = email_sender.send_alert(
                alert_type=f"Alarme Inversor: {alarm_name}",
                description=(
                    f"O seguinte alarme foi detectado no inversor: "
                    f"<strong>{alarm_name}</strong>."
                ),
                details=f"Gravidade: Nível {alarm_level} | Ocorrência: {alarm_time_str}",
                station_id=station_id,
            )
            if sent:
                _mark_alerted(alert_key)

    except Exception as exc:
        logger.error("Erro ao verificar lista de alarmes: %s", exc)

def run_alarm_check(
    api_client: SolisClient,
    email_sender: EmailSender,
    config: SolisConfig,
    station_id: str,
) -> None:

    if 0 <= datetime.now().hour < 6:
        return

    try:
        station_detail = api_client.get_station_detail(station_id)
    except Exception as exc:
        alert_key = f"api_unavailable_{station_id}"
        if _should_alert(alert_key):
            email_sender.send_alert(
                alert_type="API Solis Indisponivel",
                description=(
                    "Não foi possivel obter dados da usina via API Solis Cloud. "
                    "O monitoramento esta temporariamente fora do ar. "
                    "Por favor, avise o setor responsável sobre o problema."
                ),
                details=str(exc),
                station_id=station_id,
            )
            _mark_alerted(alert_key)
        return

    _clear_alert(f"api_unavailable_{station_id}")
    check_station_status(station_id, station_detail, email_sender)
    check_power_zero(station_id, station_detail, email_sender)
    check_active_alarms(station_id, email_sender, api_client)
