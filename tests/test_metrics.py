"""Тести метрик аналізу: статистика очікування та підрахунок «у небезпеці».

`metrics_by_severity` і `count_in_danger` — основа всіх таблиць, графіків і
harm-метрики (Фази 6, 11, 13), але досі не мали прямих тестів. Перевіряємо
структурні інваріанти на реальних прогонах (а не «золоті числа»), плюс точну
межу порога небезпеки на сконструйованих пацієнтах.
"""
import pytest

from triage_sim import (
    DANGER,
    Patient,
    count_in_danger,
    generate_patients,
    metrics_by_severity,
    simulate,
)


@pytest.mark.parametrize("discipline", ["fifo", "priority"])
@pytest.mark.parametrize("seed", range(10))
def test_count_in_danger_invariants(discipline, seed):
    """Підрахунок узгоджений: сума total = к-ть обслужених; на кожному рівні
    0 <= in_danger <= total."""
    served = simulate(generate_patients(seed=seed), discipline)
    in_danger, total = count_in_danger(served)
    assert sum(total.values()) == len(served)
    for severity in total:
        assert 0 <= in_danger[severity] <= total[severity]


def test_count_in_danger_threshold_is_strict():
    """«У небезпеці» = очікування СУВОРО перевищує поріг (рівно на порозі — ще ні)."""
    thr = DANGER[3]
    below = Patient(0, 0.0, 3, 5.0)
    below.start_time = thr - 1.0                 # wait = thr − 1
    boundary = Patient(1, 0.0, 3, 5.0)
    boundary.start_time = float(thr)             # wait = thr (НЕ > thr)
    above = Patient(2, 0.0, 3, 5.0)
    above.start_time = thr + 1.0                 # wait = thr + 1
    in_danger, total = count_in_danger([below, boundary, above])
    assert total[3] == 3
    assert in_danger[3] == 1                      # лише 'above' перевищив поріг


@pytest.mark.parametrize("seed", range(10))
def test_metrics_by_severity_structure(seed):
    """Структура метрик: к-ть по рівнях сумується до всіх обслужених, 0 <= avg <= max."""
    served = simulate(generate_patients(seed=seed), "priority")
    metrics = metrics_by_severity(served)
    assert sum(m["count"] for m in metrics.values()) == len(served)
    for m in metrics.values():
        assert m["count"] >= 1
        assert 0 <= m["avg"] <= m["max"]
