"""Generate synthetic WINDFOR / FUELHH fixtures for tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def main() -> None:
    delivery = datetime(2026, 1, 15, 0, 0, tzinfo=LONDON)
    starts = [delivery + timedelta(minutes=30 * i) for i in range(48)]

    early = datetime(2026, 1, 14, 6, 0, tzinfo=LONDON)
    at_gate = datetime(2026, 1, 14, 9, 50, tzinfo=LONDON)
    late = datetime(2026, 1, 14, 12, 0, tzinfo=LONDON)

    def gen(pub: datetime, base: int) -> list[dict]:
        rows = []
        for i, st in enumerate(starts):
            rows.append(
                {
                    "dataset": "WINDFOR",
                    "publishTime": pub.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "startTime": st.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "generation": base + i * 10,
                }
            )
        return rows

    windfor: list[dict] = []
    windfor += gen(early, 1000)
    windfor += gen(at_gate, 5000)
    windfor += gen(late, 9000)

    other = datetime(2026, 1, 16, 0, 0, tzinfo=LONDON)
    windfor.append(
        {
            "dataset": "WINDFOR",
            "publishTime": early.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "startTime": other.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": 1,
        }
    )

    jan1_starts = [
        datetime(2026, 1, 1, 0, 0, tzinfo=LONDON) + timedelta(minutes=30 * i)
        for i in range(4)
    ]
    dec31_early = datetime(2025, 12, 31, 8, 0, tzinfo=LONDON)
    dec31_late = datetime(2025, 12, 31, 11, 0, tzinfo=LONDON)
    for st in jan1_starts:
        for pub, gen_mw in ((dec31_early, 2000), (dec31_late, 3000)):
            windfor.append(
                {
                    "dataset": "WINDFOR",
                    "publishTime": pub.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "startTime": st.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "generation": gen_mw,
                }
            )

    fuelhh: list[dict] = []
    for i, st in enumerate(starts):
        fuelhh.append(
            {
                "dataset": "FUELHH",
                "publishTime": (st + timedelta(minutes=30))
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "startTime": st.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "settlementDate": "2026-01-15",
                "settlementPeriod": i + 1,
                "fuelType": "WIND",
                "generation": 5000 + i * 10 + 50,
            }
        )
    for i, st in enumerate(jan1_starts):
        fuelhh.append(
            {
                "dataset": "FUELHH",
                "publishTime": (st + timedelta(minutes=30))
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "startTime": st.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "settlementDate": "2026-01-01",
                "settlementPeriod": i + 1,
                "fuelType": "WIND",
                "generation": 2100,
            }
        )

    out = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    (out / "windfor.json").write_text(json.dumps(windfor, indent=2), encoding="utf-8")
    (out / "fuelhh_wind.json").write_text(
        json.dumps(fuelhh, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(windfor)} windfor, {len(fuelhh)} fuelhh -> {out}")


if __name__ == "__main__":
    main()
