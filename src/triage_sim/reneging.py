"""Reneging: пацієнти йдуть, не дочекавшись (LWBS — Left Without Being Seen).

Кожному пацієнту присвоюється випадковий **поріг терпіння**; якщо до моменту,
коли лікар звільнився, поріг сплив — пацієнт іде. Критичні (L1) ніколи не йдуть.

Несподіваний наслідок — **ефект клапана (release valve)**: під Priority довго
застряглі легкі не дочікуються катастрофічних 700+ хв, а просто йдуть, тож
максимум очікування *обслужених* легких падає (шкода не зникає, а змінює форму).
"""
from __future__ import annotations

import numpy as np

from .engines import discipline_sort_key, run_with_departures
from .model import DEFAULT_AGING_THRESHOLD, Patient

# Середній поріг терпіння (хв); L1 ніколи не йде.
PATIENCE_MEAN = {1: None, 2: 240, 3: 180, 4: 150, 5: 120}

# Зсув seed для окремого потоку RNG (щоб терпіння не корелювало з потоком пацієнтів).
PATIENCE_SEED_OFFSET = 10000

# Параметри розподілу порога терпіння навколо середнього (єдине джерело — тут).
PATIENCE_NOISE = 0.3    # відносний розкид (±30 %)
PATIENCE_FLOOR = 15.0   # хв: навіть найнетерплячіший чекає бодай стільки


def _sample_patience(rng, mean_patience: float | None) -> float:
    """Поріг терпіння одного пацієнта: ∞ для критичних (`mean_patience is None`),
    інакше нормальний навколо середнього (±`PATIENCE_NOISE`), не нижче `PATIENCE_FLOOR`.

    Єдине джерело формули — нею користуються і `assign_patience` (reneging),
    і `assign_patience_det` (deterioration), щоб опис розподілу не розійшовся.
    """
    if mean_patience is None:
        return float("inf")
    return max(PATIENCE_FLOOR, rng.normal(mean_patience, mean_patience * PATIENCE_NOISE))


def assign_patience(patients: list[Patient], seed: int = 0) -> list[Patient]:
    """Кожному пацієнту — свій випадковий поріг терпіння (нормальний, ±30 %)."""
    rng = np.random.default_rng(seed + PATIENCE_SEED_OFFSET)
    for patient in patients:
        patient.patience = _sample_patience(rng, PATIENCE_MEAN[patient.severity])
    return patients


def simulate_reneging(
    patients: list[Patient], discipline: str, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> tuple[list[Patient], list[Patient]]:
    """Як `simulate`, але пацієнт іде (LWBS), якщо поріг терпіння сплив до обслуговування.

    Повертає пару `(served, reneged)`. Вимагає попереднього виклику
    `assign_patience` (кожен пацієнт має атрибут `patience`).
    """
    reneged = []

    def review(waiting, now):
        # хто пішов, не дочекавшись (поріг сплив до моменту, коли лікар звільнився)
        still = []
        for patient in waiting:
            if patient.arrival_time + patient.patience <= now:
                patient.leave_time = patient.arrival_time + patient.patience
                reneged.append(patient)
            else:
                still.append(patient)
        return still

    served = run_with_departures(patients, discipline_sort_key(discipline, aging_threshold), review)
    return served, reneged
