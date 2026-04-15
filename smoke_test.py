import argparse
import json
import logging
import sys
import os
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("smoke_test")

PASS = "  [PASSOU]"
FAIL = "  [FALHOU]"

def section(title: str) -> None:
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")

def result(ok: bool, label: str, detail: str = "") -> None:
    icon = PASS if ok else FAIL
    detail_str = f" — {detail}" if detail else ""
    print(f"{icon} {label}{detail_str}")

def test_config() -> bool:
    section("1. CONFIGURACAO (.env)")
    try:
        from config import load_config
        cfg = load_config()
        result(True, "load_config() carregado com sucesso")
        result(bool(cfg.api_id), "SOLIS_API_ID presente")
        result(bool(cfg.api_secret), "SOLIS_API_SECRET presente")
        result(bool(cfg.station_ids), f"STATION_IDS presente: {cfg.station_ids}")
        result(bool(cfg.email_from), "EMAIL_FROM presente")
        result(True, f"Usando TLS: {cfg.smtp_use_tls}")
        return True
    except Exception as exc:
        result(False, "Falha ao carregar configuracao", str(exc))
        return False

def test_auth_headers() -> bool:
    section("2. AUTENTICACAO HMAC (sem chamada de rede)")
    try:
        from auth import SolisAuth
        auth = SolisAuth(api_id="test_id", api_secret="test_secret")
        body = {"id": "123456789"}
        headers = auth.build_headers(method="POST", endpoint="/v1/api/stationDetail", body=body)

        has_md5 = "Content-MD5" in headers
        has_auth = "Authorization" in headers and headers["Authorization"].startswith("API ")

        import hashlib, base64
        body_str = json.dumps(body, separators=(",", ":"))
        expected_md5 = base64.b64encode(hashlib.md5(body_str.encode()).digest()).decode()
        md5_match = headers["Content-MD5"] == expected_md5

        result(md5_match, "Content-MD5 correto")
        return all([has_md5, has_auth, md5_match])
    except Exception:
        return False

def test_api_connection() -> bool:
    section("3. CONEXAO COM API SOLIS CLOUD")
    try:
        from config import load_config
        from api_client import SolisClient
        cfg = load_config()
        client = SolisClient(cfg)
        test_id = cfg.station_ids[0]

        detail = client.get_station_detail(test_id)
        result(True, "get_station_detail() respondeu com sucesso")
        return True
    except Exception as exc:
        result(False, "Falha na conexao com API", str(exc))
        return False

def test_historical_data() -> bool:
    section("4. DADOS HISTORICOS")
    try:
        from config import load_config
        from api_client import SolisClient
        cfg = load_config()
        client = SolisClient(cfg)
        test_id = cfg.station_ids[0]

        hist = client.get_historical_data(test_id)
        days_7 = hist["seven_days"]
        days_30 = hist["thirty_days"]

        result(len(days_7) == 7, f"7 dias: OK")
        result(len(days_30) == 30, f"30 dias: OK")
        return True
    except Exception as exc:
        result(False, "Falha ao coletar dados historicos", str(exc))
        return False

def test_alarm_list() -> bool:
    section("5. LISTA DE ALARMES")
    try:
        from config import load_config
        from api_client import SolisClient
        cfg = load_config()
        client = SolisClient(cfg)
        test_id = cfg.station_ids[0]

        alarm_data = client.get_alarm_list(test_id, page=1, page_size=5)
        result(True, f"get_alarm_list() OK")
        return True
    except Exception as exc:
        result(False, "Falha ao obter lista de alarmes", str(exc))
        return False

def test_chart_generation() -> bool:
    section("6. GERACAO DE GRAFICOS")
    try:
        import tempfile
        from charts import generate_30day_chart, generate_7day_chart

        fake_data = [
            {"date": (date.today() - timedelta(days=i)).isoformat(), "energy_kwh": 30.0 + i % 10}
            for i in range(30, 0, -1)
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path_30 = generate_30day_chart(fake_data, output_dir=tmpdir, prefix="teste")
            path_7 = generate_7day_chart(fake_data[-7:], output_dir=tmpdir, prefix="teste")
        result(True, "Graficos gerados com sucesso")
        return True
    except Exception:
        return False

def test_email_report() -> bool:
    section("7. E-MAIL DE TESTE — RELATORIO")
    try:
        from config import load_config
        from email_sender import EmailSender
        cfg = load_config()
        sender = EmailSender(cfg)
        ok = sender.send_test_report()
        result(ok, "E-mail de relatorio enviado")
        return ok
    except Exception:
        return False

def test_email_alert() -> bool:
    section("8. E-MAIL DE TESTE — ALERTA")
    try:
        from config import load_config
        from email_sender import EmailSender
        cfg = load_config()
        sender = EmailSender(cfg)
        ok = sender.send_test_alert()
        result(ok, "E-mail de alerta enviado")
        return ok
    except Exception:
        return False

def test_full_report_pipeline() -> bool:
    section("9. PIPELINE COMPLETO DO RELATORIO DIARIO")
    try:
        from config import load_config
        from api_client import SolisClient
        from email_sender import EmailSender
        from reports import run_daily_report_all
        cfg = load_config()
        client = SolisClient(cfg)
        sender = EmailSender(cfg)

        ok = run_daily_report_all(client, sender, cfg)
        result(ok, "Pipeline completo executado com sucesso")
        return ok
    except Exception:
        return False

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    results = [
        ("Config", test_config()),
        ("Auth HMAC", test_auth_headers()),
        ("API Connection", test_api_connection()),
        ("Historical Data", test_historical_data()),
        ("Alarm List", test_alarm_list()),
        ("Chart Generation", test_chart_generation()),
        ("Email Report", test_email_report()),
        ("Email Alert", test_email_alert()),
    ]

    if args.full:
        results.append(("Full Pipeline", test_full_report_pipeline()))

    section("RESUMO")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        icon = PASS if ok else FAIL
        print(f"{icon} {name}")

    if passed < total:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
