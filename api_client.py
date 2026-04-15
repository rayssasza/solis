import json
import logging
import time
from datetime import date, timedelta
from typing import Any

import requests

from auth import SolisAuth
from config import SolisConfig

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30

class SolisAPIError(Exception):
    def __init__(self, endpoint: str, code: Any, message: str):
        self.endpoint = endpoint
        self.code = code
        self.message = message
        super().__init__(f"[{endpoint}] codigo={code} | {message}")

class SolisClient:
    def __init__(self, config: SolisConfig):
        self._cfg = config
        self._auth = SolisAuth(config.api_id, config.api_secret)
        self._session = requests.Session()
        self._session.verify = True

    def _post(self, endpoint: str, body: dict[str, Any]) -> Any:
        url = f"{self._cfg.base_url}{endpoint}"
        body_str = json.dumps(body, separators=(",", ":"))
        headers = self._auth.build_headers(method="POST", endpoint=endpoint, body=body)
        headers["Connection"] = "close"

        try:
            resp = self._session.post(
                url,
                data=body_str.encode("utf-8"),
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.Timeout:
            raise
        except requests.ConnectionError:
            raise
        except requests.HTTPError:
            raise

        result = resp.json()

        if str(result.get("code")) != "0":
            raise SolisAPIError(
                endpoint=endpoint,
                code=result.get("code"),
                message=result.get("msg", "Erro desconhecido"),
            )

        return result.get("data")

    def get_station_detail(self, station_id: str) -> dict[str, Any]:
        body = {"id": station_id}
        data = self._post("/v1/api/stationDetail", body)
        return data or {}

    def get_alarm_list(
        self,
        station_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        body = {
            "stationId": station_id,
            "pageNo": page,
            "pageSize": page_size,
        }
        data = self._post("/v1/api/alarmList", body)
        return data or {}

    def get_historical_data(self, station_id: str) -> dict[str, list[dict[str, Any]]]:
        today = date.today()
        start_30 = today - timedelta(days=30)

        first_day = today.replace(day=1)
        prev_month = first_day - timedelta(days=1)

        months_needed = set()
        months_needed.add((today.year, today.month))
        months_needed.add((start_30.year, start_30.month))
        months_needed.add((prev_month.year, prev_month.month))

        all_daily_data = {}
        for y, m in sorted(months_needed):
            body = {
                "id": station_id,
                "money": "BRL",
                "month": f"{y}-{m:02d}"
            }
            try:
                data = self._post("/v1/api/stationMonth", body)
                if isinstance(data, list):
                    for item in data:
                        day_str = item.get("dateStr") or ""
                        try:
                            energy = float(item.get("energy") or 0.0)
                        except (TypeError, ValueError):
                            energy = 0.0

                        if len(day_str) >= 10:
                            all_daily_data[day_str[:10]] = energy
            except Exception as exc:
                logger.error("Erro historico da usina %s: %s", station_id, exc)
            time.sleep(0.5)

        thirty_days = []
        for i in range(31, 0, -1):
            d = today - timedelta(days=i)
            d_str = d.isoformat()
            thirty_days.append({
                "date": d_str,
                "energy_kwh": all_daily_data.get(d_str, 0.0)
            })
        seven_days = thirty_days[-7:]

        prev_month_str = prev_month.strftime("%Y-%m")
        prev_month_energy = sum(e for d, e in all_daily_data.items() if d.startswith(prev_month_str))

        first_day_prev = prev_month.replace(day=1)
        prev_month_data = []
        curr_date = first_day_prev
        while curr_date <= prev_month:
            d_str = curr_date.isoformat()
            prev_month_data.append({
                "date": d_str,
                "energy_kwh": all_daily_data.get(d_str, 0.0)
            })
            curr_date += timedelta(days=1)

        return {
            "seven_days": seven_days,
            "thirty_days": thirty_days,
            "last_month_energy": prev_month_energy,
            "prev_month_data": prev_month_data
        }
