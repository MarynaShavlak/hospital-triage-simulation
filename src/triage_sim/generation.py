"""Генерація реалістичного потоку пацієнтів (процес Пуассона).

Час **між** прибуттями розподілений експоненційно (процес Пуассона), тяжкість
розігрується за `SEVERITY_PROBS`, а час лікування — з
нормального розподілу навколо базового значення (±`SERVICE_NOISE`)
із захисним мінімумом `MIN_SERVICE`.

Семплери `sample_severities` та `sample_service_durations` —
**єдине джерело правди** про ці розподіли: ними користуються і генератор потоку,
і `service_moments` (валідація). Інакше формула
часу обслуговування жила б у двох місцях і могла б тихо розійтися, зробивши
валідацію недійсною.

Параметри підібрані так, щоб лікар був завантажений на ~85 % (ρ ≈ 0.85):
черга утворюється, але система стабільна — лише тоді різниця між дисциплінами
помітна. Див. `docs/02-patient-flow.md`.
"""
from __future__ import annotations

import numpy as np

from .model import BASE_SERVICE, MIN_SERVICE, SERVICE_NOISE, SEVERITY_PROBS, Patient


def sample_severities(rng, n):
    """`n` тяжкостей із розподілу `SEVERITY_PROBS`."""
    levels = list(SEVERITY_PROBS)
    probs = [SEVERITY_PROBS[severity] for severity in levels]
    return rng.choice(levels, size=n, p=probs)


def sample_service_durations(rng, severities):
    """Час лікування для кожної тяжкості: нормальний навколо `BASE_SERVICE`
    (±`SERVICE_NOISE`), обрізаний знизу до `MIN_SERVICE`."""
    means = np.array([BASE_SERVICE[int(severity)] for severity in severities], dtype=float)
    return np.maximum(MIN_SERVICE, rng.normal(means, means * SERVICE_NOISE))


def generate_patients(n: int = 180, arrival_rate: float = 0.075, seed: int = 42) -> list[Patient]:
    """Генерує потік пацієнтів.

    arrival_rate — пацієнтів за хвилину (0.075 = один кожні ~13 хв).
    Параметри підібрані так, щоб лікар був завантажений на ~85 % —
    черга утворюється, але система стабільна.
    """
    rng = np.random.default_rng(seed)

    # Час МІЖ прибуттями ~ експоненційний → це процес Пуассона.
    inter_arrivals = rng.exponential(1 / arrival_rate, size=n)
    arrival_times = np.cumsum(inter_arrivals)

    # Тяжкість і час лікування — зі спільних семплерів (єдине джерело правди).
    severities = sample_severities(rng, n)
    durations = sample_service_durations(rng, severities)

    return [Patient(i, float(arrival_times[i]), int(severities[i]), float(durations[i]))
            for i in range(n)]
