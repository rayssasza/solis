import logging
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
import schedule

from config import load_config
from api_client import SolisClient
from email_sender import EmailSender
from alerts import run_alarm_check

def setup_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)
    root = logging.getLogger()
    root.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    try:
        file_handler = RotatingFileHandler(
            "solis_monitor.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except PermissionError:
        pass

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def job_daily_report(api_client: SolisClient, email_sender: EmailSender, config) -> None:
    try:
        from reports import run_daily_report_all
        run_daily_report_all(api_client, email_sender, config)
    except Exception:
        pass

def job_alarm_check(api_client: SolisClient, email_sender: EmailSender, config) -> None:
    for station_id in config.station_ids:
        try:
            run_alarm_check(api_client, email_sender, config, station_id)
        except Exception:
            pass

def main() -> None:
    setup_logging(log_level="INFO")

    try:
        config = load_config()
    except ValueError:
        sys.exit(1)

    api_client = SolisClient(config)
    email_sender = EmailSender(config)

    schedule.every().day.at(config.daily_report_time).do(
        job_daily_report,
        api_client=api_client,
        email_sender=email_sender,
        config=config,
    )

    schedule.every(config.alarm_check_interval).minutes.do(
        job_alarm_check,
        api_client=api_client,
        email_sender=email_sender,
        config=config,
    )

    job_alarm_check(api_client, email_sender, config)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        pass
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
