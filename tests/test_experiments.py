"""Тести спільного шару Монте-Карло-експериментів (`triage_sim.experiments`).

Перевіряємо КОНТРАКТ `monte_carlo` (структуру й узгодженість), а не «золоті
числа»: саме на цей контракт спираються і `run_monte_carlo.py` (друк), і
`figbuild` (графіки 17/18) — тож звіт і графік не можуть розійтися.
"""
import math

from triage_sim import (
    deterioration_sensitivity,
    deterioration_stats,
    load_sweep,
    monte_carlo,
    reneging_stats,
    reneging_valve,
)

KEYS = ["f_L1", "p_L1", "a_L1", "f_L5", "p_L5", "a_L5", "speedup"]


def test_monte_carlo_structure_and_consistency():
    data = monte_carlo(runs=8)
    res, s42, skipped = data["res"], data["s42"], data["skipped"]
    # усі 7 серій присутні й однакової довжини
    assert set(res) == set(KEYS)
    lengths = {len(v) for v in res.values()}
    assert len(lengths) == 1
    kept = lengths.pop()
    # кожен прогін або врахований, або відсіяний
    assert kept + skipped == 8
    # speedup узгоджений із сирими L1 (FIFO / Priority)
    for f, p, sp in zip(res["f_L1"], res["p_L1"], res["speedup"], strict=True):
        assert sp == f / p
    # s42 має ті самі показники й ту саму узгодженість
    assert set(s42) == set(KEYS)
    assert s42["speedup"] == s42["f_L1"] / s42["p_L1"]


def test_monte_carlo_runs_zero_still_has_seed42():
    # 0 прогонів: серії порожні, але опорна точка seed=42 рахується завжди
    data = monte_carlo(runs=0)
    assert all(series == [] for series in data["res"].values())
    assert data["skipped"] == 0
    assert math.isfinite(data["s42"]["speedup"])


def test_load_sweep_structure():
    data = load_sweep(seeds_per_rho=5)
    keys = {"rho", "fifo_L1", "prio_L1", "aging_L1", "prio_L5max", "speedup"}
    assert set(data) == keys
    n_rho = len(data["rho"])
    assert n_rho == 10                                   # ρ ∈ [0.50, 0.95], крок 0.05
    assert all(len(series) == n_rho for series in data.values())


def test_reneging_stats_structure_and_invariants():
    data = reneging_stats(runs=5)
    overall, lwbs = data["overall"], data["lwbs"]
    for disc in ("fifo", "priority", "aging"):
        assert 0 <= overall[disc]["left"] <= overall[disc]["total"]
        # сума total по рівнях = загальний total дисципліни
        assert sum(lwbs[disc][s]["total"] for s in range(1, 6)) == overall[disc]["total"]
        # критичні (L1) ніколи не йдуть
        assert lwbs[disc][1]["left"] == 0


def test_reneging_valve_returns_two_series():
    data = reneging_valve(runs=5)
    assert data["l5_no"] and data["l5_yes"]              # обидві серії непорожні


def test_deterioration_stats_structure_and_invariants():
    data = deterioration_stats(runs=5)
    assert data["arrived_l1"] > 0
    for disc in ("fifo", "priority", "aging"):
        naive = data["naive"][disc]
        assert 0 <= naive["deteriorated"] <= naive["total"]
        assert 0 <= naive["died"] <= naive["total"]
        assert 0 <= data["arrived_l1_died"][disc] <= data["arrived_l1"]
        r = data["R"][disc]
        assert r["died"] + r["left"] <= r["total"]       # served = total − died − left ≥ 0
        assert 0 <= r["l1_died"] <= data["arrived_l1"]


def test_deterioration_sensitivity_shape():
    sens = deterioration_sensitivity(runs=3, rates=(0.01, 0.02))
    assert sens["rates"] == [0.01, 0.02]
    assert sens["arrived_l1"] > 0
    assert len(sens["l1_deaths"]) == 2
    assert all(set(deaths) == {"fifo", "priority", "aging"} for deaths in sens["l1_deaths"])
