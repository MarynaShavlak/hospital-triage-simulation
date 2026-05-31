"""Узагальнені драйвери дискретно-подійної симуляції «один лікар + черга».

Уся механіка часу (впуск прибулих, простій лікаря, обслуговування) живе тут —
один раз на всі дисципліни. Драйвери НЕ знають про конкретну чергу: працюють
через інтерфейс `QueuePolicy` (`run_single_server`) або через функції
ключ/перегляд (`run_with_departures`). Конкретні політики — у `policies.py`.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ..model import Patient


class QueuePolicy(Protocol):
    """Інтерфейс політики черги для драйвера: push / pop / довжина (truthiness)."""

    def push(self, patient: Patient) -> None: ...
    def pop(self, now: float) -> Patient: ...
    def __len__(self) -> int: ...


def run_single_server(patients: list[Patient], policy: QueuePolicy) -> list[Patient]:
    """Єдиний цикл «один лікар + черга». `policy` інкапсулює дисципліну.

    `policy` має підтримувати `push(patient)`, `pop(now) -> patient` і
    `__len__` (truthiness = «у черзі ще хтось є»). Уся механіка часу та
    простою — тут, один раз на всі дисципліни.
    """
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0                  # індекс наступного прибуття
    now = 0.0              # коли лікар звільниться
    served = []

    while i < len(arrivals) or policy:
        # Додаємо всіх, хто вже прибув до поточного моменту.
        while i < len(arrivals) and arrivals[i].arrival_time <= now:
            policy.push(arrivals[i])
            i += 1

        if not policy:
            now = arrivals[i].arrival_time     # лікар простоює — до наступного прибуття
            continue

        patient = policy.pop(now)
        patient.start_time = now
        now += patient.service_duration
        served.append(patient)

    return served


def run_with_departures(
    patients: list[Patient],
    sort_key: Callable[[Patient, float], tuple],
    review: Callable[[list[Patient], float], list[Patient]],
) -> list[Patient]:
    """Драйвер для моделей із ВИБУТТЯМ пацієнтів (reneging / deterioration).

    Той самий цикл, що `run_single_server`, але перед кожним
    обслуговуванням викликає `review(waiting, now) -> survivors`. `review`
    може мутувати стан пацієнтів і відсіювати тих, хто вибув (LWBS / смерть),
    складаючи їх у власні списки (через замикання). Тих, хто лишився,
    сортуємо за `sort_key(p, now)` і беремо першого.
    """
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0
    now = 0.0
    waiting: list[Patient] = []   # звичайний список — пріоритет/склад черги змінюються з часом
    served = []

    while i < len(arrivals) or waiting:
        while i < len(arrivals) and arrivals[i].arrival_time <= now:
            waiting.append(arrivals[i])
            i += 1

        if not waiting:
            now = arrivals[i].arrival_time
            continue

        waiting = review(waiting, now)         # хтось міг вибути / змінити стан
        if not waiting:
            if i < len(arrivals):
                now = arrivals[i].arrival_time
                continue
            break

        waiting.sort(key=lambda patient: sort_key(patient, now))
        patient = waiting.pop(0)
        patient.start_time = now
        now += patient.service_duration
        served.append(patient)

    return served
