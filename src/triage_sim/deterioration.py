"""Динамічна тяжкість: пацієнти погіршуються з часом очікування і можуть померти.

Найреалістичніша модель проєкту. Кожному пацієнту наперед розігрується «розклад
погіршення» (моменти, коли тяжкість падає на рівень). Якщо пацієнт досяг L1 і
пробув критичним понад `DEATH_THR` хв — він помирає.

* `simulate_deterioration` — погіршення + смерть (БЕЗ виходу пацієнтів).
* `simulate_deter_reneg` — повна модель: погіршення + смерть + вихід легких
  (reneging). Саме «клапан» виходу легких рятує критичних від смерті під Priority.

Обидва рушії — обгортки над `run_with_departures`:
спільний крок зміни стану — `_deteriorate`, а різниця лише в тому, кого
саме хук `review` відсіює (смерть / смерть + вихід). Розклади погіршення теж
будує один спільний `_assign_schedule`.
"""
from __future__ import annotations

import numpy as np

from .engines import discipline_sort_key, run_with_departures
from .model import BASE_SERVICE, DEFAULT_AGING_THRESHOLD, Patient
from .reneging import PATIENCE_MEAN, PATIENCE_SEED_OFFSET, _sample_patience

BASE = dict(BASE_SERVICE)                      # базовий час лікування за рівнями

# Темп погіршення (ймовірність падіння на рівень за хвилину). Зв'язок «L5 деградує
# у 1/L5_SLOWDOWN разів повільніше» описаний ОДИН раз тут і перевикористовується
# в assign_det_rate — щоб два описи того самого факту не розійшлися.
DET_BASE_RATE = 0.01
L5_SLOWDOWN = 0.1
DET_RATE = {2: DET_BASE_RATE, 3: DET_BASE_RATE, 4: DET_BASE_RATE, 5: DET_BASE_RATE * L5_SLOWDOWN}

DEATH_THR = 60.0                               # хвилин у стані L1 до смерті
DETERIORATION_SEED_OFFSET = 20000              # окремий потік RNG для розкладу погіршення


def _rate_for(sev: int, base_rate: float) -> float:
    """Темп погіршення рівня `sev` за базового темпу `base_rate` (L5 — повільніше)."""
    return base_rate if sev in (2, 3, 4) else base_rate * L5_SLOWDOWN


def _assign_schedule(patients: list[Patient], seed: int, base_rate: float) -> list[Patient]:
    """Спільний крок: кожному — 'розклад погіршення' (моменти падіння тяжкості).

    `base_rate` — темп для L2–L4; L5 деградує у `1/L5_SLOWDOWN` разів повільніше.
    """
    rng = np.random.default_rng(seed + DETERIORATION_SEED_OFFSET)
    for patient in patients:
        patient.orig_severity = patient.severity
        patient.orig_duration = patient.service_duration
        patient.det_times = []                       # моменти (від прибуття), коли тяжкість падає
        sev = patient.severity
        elapsed = 0.0
        while sev > 1:
            elapsed += rng.exponential(1.0 / _rate_for(sev, base_rate))
            patient.det_times.append(elapsed)
            sev -= 1
    return patients


def assign_deterioration(patients: list[Patient], seed: int) -> list[Patient]:
    """Кожному — 'розклад погіршення' за стандартним темпом `DET_BASE_RATE`."""
    return _assign_schedule(patients, seed, DET_BASE_RATE)


def assign_det_rate(patients: list[Patient], seed: int, rate: float) -> list[Patient]:
    """Як `assign_deterioration`, але з налаштовуваним базовим темпом
    (для аналізу чутливості; L5 деградує у `1/L5_SLOWDOWN` разів повільніше)."""
    return _assign_schedule(patients, seed, rate)


def _current_severity(patient: Patient, wait: float) -> int:
    """Поточна тяжкість = початкова мінус кількість пройдених порогів погіршення."""
    assert patient.orig_severity is not None and patient.det_times is not None
    return patient.orig_severity - sum(1 for elapsed in patient.det_times if elapsed <= wait)


def _deteriorate(patient: Patient, now: float) -> tuple[float, float]:
    """Оновлює тяжкість і час лікування пацієнта на момент `now`.

    Повертає `(wait, became_crit)`: скільки чекає і момент (від прибуття), коли
    він став критичним (0, якщо прибув L1) — для перевірки смерті у викликачі.
    """
    assert patient.orig_severity is not None and patient.orig_duration is not None
    wait = now - patient.arrival_time
    patient.severity = _current_severity(patient, wait)
    patient.service_duration = patient.orig_duration * BASE[patient.severity] / BASE[patient.orig_severity]
    became_crit = patient.det_times[-1] if patient.det_times else 0.0
    return wait, became_crit


def simulate_deterioration(
    patients: list[Patient], discipline: str, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> tuple[list[Patient], list[Patient]]:
    """Симуляція з погіршенням і смертю (поки БЕЗ виходу пацієнтів).

    Повертає пару `(served, died)`. Вимагає `assign_deterioration`.
    """
    died = []

    def review(waiting, now):
        alive = []
        for patient in waiting:
            wait, became_crit = _deteriorate(patient, now)
            if patient.severity == 1 and wait >= became_crit + DEATH_THR:
                patient.death_time = patient.arrival_time + became_crit + DEATH_THR
                died.append(patient)
            else:
                alive.append(patient)
        return alive

    served = run_with_departures(patients, discipline_sort_key(discipline, aging_threshold), review)
    return served, died


def assign_patience_det(patients: list[Patient], seed: int = 0) -> list[Patient]:
    """Терпіння (як у reneging), але прив'язане до ПОЧАТКОВОЇ тяжкості."""
    rng = np.random.default_rng(seed + PATIENCE_SEED_OFFSET)
    for patient in patients:
        assert patient.orig_severity is not None
        patient.patience = _sample_patience(rng, PATIENCE_MEAN[patient.orig_severity])
    return patients


def simulate_deter_reneg(
    patients: list[Patient], discipline: str, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> tuple[list[Patient], list[Patient], list[Patient]]:
    """Погіршення + смерть + вихід легких (повна реалістична модель).

    Повертає трійку `(served, died, left)`. Вимагає послідовно
    `assign_deterioration` та `assign_patience_det`.
    """
    died = []
    left = []

    def review(waiting, now):
        alive = []
        for patient in waiting:
            wait, became_crit = _deteriorate(patient, now)
            if patient.severity == 1 and wait >= became_crit + DEATH_THR:
                patient.death_time = patient.arrival_time + became_crit + DEATH_THR
                died.append(patient)
                continue                       # критичний помер
            if patient.severity > 1 and patient.arrival_time + patient.patience <= now:
                patient.leave_time = patient.arrival_time + patient.patience
                left.append(patient)
                continue                       # легкий пішов (не критичний — не йде)
            alive.append(patient)
        return alive

    served = run_with_departures(patients, discipline_sort_key(discipline, aging_threshold), review)
    return served, died, left
