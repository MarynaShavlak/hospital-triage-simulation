"""Готові Монте-Карло-експерименти: проганяють симуляцію на N незалежних seed і
повертають зібрану статистику — БЕЗ друку та графіків.

Один експеримент — **одне джерело правди**: `scripts/run_*.py` друкують ці числа,
а `figbuild` малює з НИХ САМИХ, тож текстовий звіт і графік не можуть розійтися.
Той самий патерн, що `validate_mg1`/`validate_mmc` у `validation.py`
(бібліотека рахує → скрипт друкує).
"""
from __future__ import annotations

import copy

import numpy as np

from .aging import simulate_aging
from .deterioration import (
    assign_det_rate,
    assign_deterioration,
    assign_patience_det,
    simulate_deter_reneg,
    simulate_deterioration,
)
from .engines import simulate
from .generation import generate_patients
from .metrics import metrics_by_severity
from .model import BASE_SERVICE, DEFAULT_AGING_THRESHOLD, DISCIPLINES, SEVERITY_PROBS, Patient
from .reneging import assign_patience, simulate_reneging

# Набір метрик однієї дисципліни: {severity: {'avg'|'max'|'count': значення}}.
Metrics = dict[int, dict[str, float]]


def _three_metrics(patients: list[Patient], aging_threshold: int) -> tuple[Metrics, Metrics, Metrics]:
    """Метрики FIFO / Priority / Aging на КОПІЯХ одного набору пацієнтів."""
    return (
        metrics_by_severity(simulate(copy.deepcopy(patients), "fifo")),
        metrics_by_severity(simulate(copy.deepcopy(patients), "priority")),
        metrics_by_severity(simulate_aging(copy.deepcopy(patients), aging_threshold)),
    )


def monte_carlo(
    runs: int = 300, n: int = 180, arrival_rate: float = 0.075,
    aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> dict:
    """N незалежних прогонів Монте-Карло (seed = 0..runs−1) + опорна точка seed=42.

    Повертає `{'res', 's42', 'skipped'}` — нічого не друкує й не малює:

    * `res`     — словник списків по прогонах: `f_L1`/`p_L1`/`a_L1` (середнє L1),
                  `f_L5`/`p_L5`/`a_L5` (максимум L5), `speedup` (FIFO/Priority по L1);
    * `s42`     — ті самі показники для одного прогону seed=42 (для порівняння з розподілом);
    * `skipped` — скільки прогонів відсіяно (немає L1/L5 або вироджений Priority).
    """
    keys = ["f_L1", "p_L1", "a_L1", "f_L5", "p_L5", "a_L5", "speedup"]
    res: dict[str, list[float]] = {k: [] for k in keys}
    skipped = 0
    for seed in range(runs):
        pts = generate_patients(n=n, arrival_rate=arrival_rate, seed=seed)
        mf, mp, ma = _three_metrics(pts, aging_threshold)
        if 1 not in mf or 1 not in mp or 5 not in mf or 5 not in mp or mp[1]["avg"] < 0.5:
            skipped += 1
            continue
        res["f_L1"].append(mf[1]["avg"])
        res["p_L1"].append(mp[1]["avg"])
        res["a_L1"].append(ma[1]["avg"])
        res["f_L5"].append(mf[5]["max"])
        res["p_L5"].append(mp[5]["max"])
        res["a_L5"].append(ma[5]["max"])
        res["speedup"].append(mf[1]["avg"] / mp[1]["avg"])
    pts42 = generate_patients(n=n, arrival_rate=arrival_rate, seed=42)
    mf42, mp42, ma42 = _three_metrics(pts42, aging_threshold)
    s42 = {
        "f_L1": mf42[1]["avg"], "p_L1": mp42[1]["avg"], "a_L1": ma42[1]["avg"],
        "f_L5": mf42[5]["max"], "p_L5": mp42[5]["max"], "a_L5": ma42[5]["max"],
        "speedup": mf42[1]["avg"] / mp42[1]["avg"],
    }
    return {"res": res, "s42": s42, "skipped": skipped}


def load_sweep(
    seeds_per_rho: int = 40, n: int = 180, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> dict:
    """Sweep по навантаженню ρ ∈ [0.50, 0.95] із кроком 0.05.

    Для кожного ρ підбирає частоту прибуттів під потрібне завантаження й проганяє
    `seeds_per_rho` прогонів, агрегуючи через середнє. Повертає dict зі списками
    по ρ (нічого не друкує/не малює): `rho`, `fifo_L1`/`prio_L1`/`aging_L1`
    (середнє очікування L1), `prio_L5max` (max L5 під Priority), `speedup` (FIFO/Priority).
    """
    avg_service = sum(SEVERITY_PROBS[s] * BASE_SERVICE[s] for s in range(1, 6))
    rho_values = np.arange(0.50, 0.96, 0.05)
    keys = ["rho", "fifo_L1", "prio_L1", "aging_L1", "prio_L5max", "speedup"]
    data: dict[str, list] = {k: [] for k in keys}
    for rho in rho_values:
        arrival_rate = rho / avg_service          # підбираємо частоту під потрібне ρ
        fifo_l1, prio_l1, aging_l1, prio_l5max = [], [], [], []
        for seed in range(seeds_per_rho):
            pts = generate_patients(n=n, arrival_rate=arrival_rate, seed=seed)
            mf, mp, ma = _three_metrics(pts, aging_threshold)
            if 1 not in mf or 1 not in mp or 5 not in mp or mp[1]["avg"] < 0.3:
                continue
            fifo_l1.append(mf[1]["avg"])
            prio_l1.append(mp[1]["avg"])
            aging_l1.append(ma[1]["avg"] if 1 in ma else mp[1]["avg"])
            prio_l5max.append(mp[5]["max"])
        data["rho"].append(rho)
        data["fifo_L1"].append(np.mean(fifo_l1))
        data["prio_L1"].append(np.mean(prio_l1))
        data["aging_L1"].append(np.mean(aging_l1))
        data["prio_L5max"].append(np.mean(prio_l5max))
        data["speedup"].append(np.mean(fifo_l1) / np.mean(prio_l1))
    return data


def reneging_stats(
    runs: int = 300, n: int = 180, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> dict:
    """LWBS-статистика (Left Without Being Seen) по N прогонах × трьох дисциплінах.

    Повертає `{'overall', 'lwbs'}` (нічого не друкує/малює):
    * `overall[disc]`           = `{'left', 'total'}` — скільки пішло / усього;
    * `lwbs[disc][severity]`    = `{'left', 'total'}` — те саме за рівнями тяжкості.
    Кожному пацієнту присвоюється поріг терпіння (`assign_patience`).
    """
    lwbs = {d: {s: {"left": 0, "total": 0} for s in range(1, 6)} for d in DISCIPLINES}
    overall = {d: {"left": 0, "total": 0} for d in DISCIPLINES}
    for seed in range(runs):
        base = generate_patients(n=n, seed=seed)
        for disc in DISCIPLINES:
            pts = assign_patience(copy.deepcopy(base), seed=seed)
            served, reneged = simulate_reneging(pts, disc, aging_threshold)
            for patient in served:
                overall[disc]["total"] += 1
                lwbs[disc][patient.severity]["total"] += 1
            for patient in reneged:
                overall[disc]["total"] += 1
                overall[disc]["left"] += 1
                lwbs[disc][patient.severity]["total"] += 1
                lwbs[disc][patient.severity]["left"] += 1
    return {"overall": overall, "lwbs": lwbs}


def reneging_valve(runs: int = 300, n: int = 180) -> dict:
    """Ефект «клапана» під Priority: max очікування ОБСЛУЖЕНИХ L5 з reneging і без.

    Повертає `{'l5_no', 'l5_yes'}` — списки max-очікувань L5 по прогонах: `l5_no` —
    ідеально терплячі (ніхто не йде), `l5_yes` — зі скінченним терпінням. Довго
    застряглі легкі під reneging ПІШЛИ, тож max очікування обслужених L5 падає.
    """
    l5_no: list[float] = []
    l5_yes: list[float] = []
    for seed in range(runs):
        base = generate_patients(n=n, seed=seed)
        pts = copy.deepcopy(base)
        for patient in pts:
            patient.patience = float("inf")            # ідеально терплячі — ніхто не йде
        served_no, _ = simulate_reneging(pts, "priority")
        waits = [patient.wait_time for patient in served_no if patient.severity == 5]
        if waits:
            l5_no.append(max(waits))
        pts = assign_patience(copy.deepcopy(base), seed=seed)
        served_yes, _ = simulate_reneging(pts, "priority")
        waits = [patient.wait_time for patient in served_yes if patient.severity == 5]
        if waits:
            l5_yes.append(max(waits))
    return {"l5_no": l5_no, "l5_yes": l5_yes}


def deterioration_stats(
    runs: int = 300, n: int = 180, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> dict:
    """Динамічна тяжкість: наївна (погіршення+смерть) і реалістична (+вихід легких)
    моделі по N прогонах × трьох дисциплінах.

    Повертає (нічого не друкує/малює):
    * `arrived_l1`       — скільки пацієнтів прибуло критичними (L1) за всі прогони;
    * `naive[disc]`      — `{'deteriorated', 'died', 'total'}` (наївна модель);
    * `arrived_l1_died`  — `{disc: к-ть}` прибулих L1, що померли (наївна);
    * `R[disc]`          — `{'died', 'left', 'total', 'l1_died'}` (реалістична).
    """
    naive = {d: {"deteriorated": 0, "died": 0, "total": 0} for d in DISCIPLINES}
    arrived_l1_died = {d: 0 for d in DISCIPLINES}
    arrived_l1 = 0
    for seed in range(runs):
        base = generate_patients(n=n, seed=seed)
        arrived_l1 += sum(1 for p in base if p.severity == 1)
        for disc in DISCIPLINES:
            pts = assign_deterioration(copy.deepcopy(base), seed=seed)
            served, died = simulate_deterioration(pts, disc, aging_threshold)
            for p in served:
                naive[disc]["total"] += 1
                if p.orig_severity is not None and p.severity < p.orig_severity:
                    naive[disc]["deteriorated"] += 1
            for p in died:
                naive[disc]["total"] += 1
                naive[disc]["died"] += 1
                if p.orig_severity == 1:
                    arrived_l1_died[disc] += 1
    results = {d: {"died": 0, "left": 0, "total": 0, "l1_died": 0} for d in DISCIPLINES}
    for seed in range(runs):
        base = generate_patients(n=n, seed=seed)
        for disc in DISCIPLINES:
            pts = assign_patience_det(assign_deterioration(copy.deepcopy(base), seed=seed), seed=seed)
            served, died, left = simulate_deter_reneg(pts, disc, aging_threshold)
            results[disc]["total"] += len(served) + len(died) + len(left)
            results[disc]["died"] += len(died)
            results[disc]["left"] += len(left)
            results[disc]["l1_died"] += sum(1 for p in died if p.orig_severity == 1)
    return {"arrived_l1": arrived_l1, "naive": naive, "arrived_l1_died": arrived_l1_died, "R": results}


def deterioration_sensitivity(
    runs: int = 200, rates: tuple = (0.005, 0.01, 0.015, 0.02), n: int = 180,
) -> dict:
    """Чутливість смертності прибулих критичних (L1) до темпу погіршення.

    Для кожного `rate` проганяє повну модель (погіршення+смерть+вихід легких) і
    рахує L1-смерті. Повертає `{'rates', 'arrived_l1', 'l1_deaths'}`, де
    `l1_deaths[i] = {disc: к-ть}` для `rates[i]`. Лише обчислення, без друку.
    """
    arrived_l1 = 0
    l1_deaths = [{d: 0 for d in DISCIPLINES} for _ in rates]
    for i, rate in enumerate(rates):
        for seed in range(runs):
            base = generate_patients(n=n, seed=seed)
            if i == 0:                                 # arrived_l1 не залежить від темпу — рахуємо раз
                arrived_l1 += sum(1 for p in base if p.severity == 1)
            for disc in DISCIPLINES:
                pts = assign_patience_det(assign_det_rate(copy.deepcopy(base), seed, rate), seed=seed)
                _, died, _ = simulate_deter_reneg(pts, disc)
                l1_deaths[i][disc] += sum(1 for p in died if p.orig_severity == 1)
    return {"rates": list(rates), "arrived_l1": arrived_l1, "l1_deaths": l1_deaths}
