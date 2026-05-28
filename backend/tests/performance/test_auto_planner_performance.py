from datetime import datetime, timedelta

from backend.domain.services.auto_planner import build_candidate_slots


def test_build_candidate_slots_performance(benchmark):
    date_from = datetime.now() + timedelta(days=1)
    date_to = date_from + timedelta(days=14)

    result = benchmark(
        build_candidate_slots,
        existing_events=[],
        date_from=date_from,
        date_to=date_to,
        duration_minutes=60,
        day_start="08:00",
        day_end="22:00",
    )

    assert isinstance(result, list)
    assert len(result) > 0