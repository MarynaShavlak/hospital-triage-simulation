"""Валідація рушія проти точних формул теорії черг.

Якщо симуляція збігається з аналітичними формулами — рушій фізично правильний,
а не просто «дає гарну картинку».

* `validate_mg1` — порівняння середнього очікування FIFO із формулою
  **Pollaczek–Khinchine** (M/G/1, загальний розподіл обслуговування).
* `erlang_c` / `mmc_wq` — точний розв'язок **M/M/c** (експоненційне
  обслуговування), яким валідовано багатосерверну логіку `simulate_md`.
"""
from __future__ import annotations

import math
import statistics

import numpy as np

from .engines import simulate, simulate_md
from .generation import generate_patients, sample_service_durations, sample_severities
from .model import Patient


def service_moments(n: int = 2_000_000, seed: int = 1) -> tuple[float, float]:
    """Перший і другий моменти часу обслуговування — з ТОГО САМОГО розподілу,
    що й у `generate_patients` (спільні семплери — єдине джерело правди,
    тож валідація гарантовано звіряється з реально симульованим розподілом)."""
    rng = np.random.default_rng(seed)
    sev = sample_severities(rng, n)
    dur = sample_service_durations(rng, sev)
    return dur.mean(), (dur ** 2).mean()


def validate_mg1(arrival_rate: float = 0.075, n: int = 20000, warmup: int = 2000, runs: int = 20) -> dict:
    """Звірити симуляцію FIFO з формулою Pollaczek–Khinchine (M/G/1).

    Лише рахує й повертає `{'rho', 'Wq_theory', 'Wq_sim', 'ci', 'ok'}` —
    форматування/друк лишаємо на боці скрипта (бібліотека не робить I/O).
    `ok` = теорія потрапляє в 95 % довірчий інтервал симуляції.
    """
    ES, ES2 = service_moments()
    rho = arrival_rate * ES
    Wq = arrival_rate * ES2 / (2 * (1 - rho))               # Pollaczek–Khinchine
    run_means = [statistics.mean(patient.wait_time for patient in
          simulate(generate_patients(n=n, arrival_rate=arrival_rate, seed=seed), "fifo")[warmup:])
          for seed in range(runs)]
    sim_mean = float(np.mean(run_means))
    std_error = float(np.std(run_means, ddof=1)) / np.sqrt(runs)
    ci_low, ci_high = sim_mean - 1.96 * std_error, sim_mean + 1.96 * std_error
    return {"rho": rho, "Wq_theory": Wq, "Wq_sim": sim_mean, "ci": (ci_low, ci_high), "ok": ci_low <= Wq <= ci_high}


def erlang_c(c: int, a: float) -> float:
    """Ймовірність очікування (формула Erlang-C). a = пропонована загрузка lam*E[S]."""
    rho = a / c
    head = sum(a ** k / math.factorial(k) for k in range(c))
    tail = a ** c / math.factorial(c) / (1 - rho)
    return tail / (head + tail)


def mmc_wq(lam: float, ES: float, c: int) -> float:
    """Середнє очікування в черзі для M/M/c."""
    return erlang_c(c, lam * ES) / (c / ES - lam)


def gen_exponential(n: int, lam: float, ES: float, seed: int) -> list[Patient]:
    """Тестовий потік: Пуассон + ЕКСПОНЕНЦІЙНЕ лікування (там Erlang-C точна)."""
    rng = np.random.default_rng(seed)
    arr = np.cumsum(rng.exponential(1 / lam, size=n))
    dur = rng.exponential(ES, size=n)
    return [Patient(j, float(arr[j]), 3, float(dur[j])) for j in range(n)]


def validate_mmc(configs=((2, 0.85), (3, 0.80)), n: int = 20000, warmup: int = 2000, runs: int = 20) -> list:
    """Звірити `simulate_md` з точним M/M/c (Erlang-C) на експоненційному
    обслуговуванні.

    Лише рахує й повертає список `{'c', 'rho', 'Wq_theory', 'Wq_sim', 'ci', 'ok'}`
    по конфігурації (c, ρ) — друк лишаємо на боці скрипта.
    """
    ES, _ = service_moments()        # середній час лікування (~11.3 хв), щоб режим був реалістичним
    results = []
    for c, rho in configs:
        a = rho * c
        lam = a / ES
        Wq_theory = mmc_wq(lam, ES, c)
        run_means = [statistics.mean(patient.wait_time for patient in
              simulate_md(gen_exponential(n, lam, ES, seed), "fifo", c)[warmup:])
              for seed in range(runs)]
        sim_mean = float(np.mean(run_means))
        std_error = float(np.std(run_means, ddof=1)) / np.sqrt(len(run_means))
        ci_low, ci_high = sim_mean - 1.96 * std_error, sim_mean + 1.96 * std_error
        results.append({"c": c, "rho": rho, "Wq_theory": Wq_theory, "Wq_sim": sim_mean,
                        "ci": (ci_low, ci_high), "ok": ci_low <= Wq_theory <= ci_high})
    return results
