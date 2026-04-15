import os
import logging
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class SolisConfig:
    api_id: str
    api_secret: str
    base_url: str
    station_ids: List[str]

    email_from: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool

    report_recipients: List[str]
    alert_recipients: List[str]

    daily_report_time: str
    alarm_check_interval: int

def _parse_list(raw: str) -> List[str]:
    return [e.strip() for e in raw.split(",") if e.strip()]

def load_config() -> SolisConfig:
    required = [
        "SOLIS_API_ID",
        "SOLIS_API_SECRET",
        "STATION_IDS",
        "EMAIL_FROM",
        "REPORT_RECIPIENTS",
        "ALERT_RECIPIENTS",
    ]

    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(
            f"Variaveis de ambiente ausentes: {', '.join(missing)}\n"
            "Verificar o arquivo .env"
        )

    use_tls_str = os.getenv("SMTP_USE_TLS", "false").lower()
    use_tls = use_tls_str in ("true", "1", "yes")

    cfg = SolisConfig(
        api_id=os.environ["SOLIS_API_ID"],
        api_secret=os.environ["SOLIS_API_SECRET"],
        base_url=os.getenv("SOLIS_BASE_URL", "https://www.soliscloud.com:13333"),
        station_ids=_parse_list(os.environ["STATION_IDS"]),
        email_from=os.environ["EMAIL_FROM"],
        smtp_host=os.getenv("SMTP_HOST", "localhost"),
        smtp_port=int(os.getenv("SMTP_PORT", "25")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_use_tls=use_tls,
        report_recipients=_parse_list(os.environ["REPORT_RECIPIENTS"]),
        alert_recipients=_parse_list(os.environ["ALERT_RECIPIENTS"]),
        daily_report_time=os.getenv("DAILY_REPORT_TIME", "08:00"),
        alarm_check_interval=int(os.getenv("ALARM_CHECK_INTERVAL_MINUTES", "15")),
    )

    return cfg
