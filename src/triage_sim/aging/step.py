"""Нелінійне (порогове) правило ескалації + купа з лінивим видаленням.

Ескалація стрибками на порогах очікування (30/60 хв) зі **стелею безпеки**
`SAFETY_FLOOR`, щоб ескальований легкий не дотягнувся до реанімаційного L1.
Лінива купа (`StepLazyHeap`) дає O(log n) амортизовано; брутфорс-список
(`ListStepPolicy`) — прозорий еталон для звірки.
"""
from __future__ import annotations

import heapq

from ..engines import run_single_server
from ..model import Patient

ESCALATION = ((30, 1), (60, 2))   # >30 хв: +1 рівень; >60 хв: +2
SAFETY_FLOOR = 2                  # ескальований легкий НЕ дотягнеться до L1


def escalated_level(
    patient: Patient, now: float, esc: tuple[tuple[int, int], ...] = ESCALATION, floor: int = SAFETY_FLOOR,
) -> int:
    """Поточний (ескальований) рівень: тяжчає з очікуванням, але не нижче floor
    і не легше за початковий рівень."""
    waited = now - patient.arrival_time
    bump = max((bump for thr, bump in esc if waited >= thr), default=0)
    return min(patient.severity, max(floor, patient.severity - bump))


class StepLazyHeap:
    """Нелінійне (порогове) правило на купі з лінивим видаленням.

    Ключ міняється лише в дискретні моменти (перетин порогів 30/60 хв). При
    перетині кладемо НОВИЙ запис, старий лишаємо протухати, а при вийманні
    пропускаємо протухлі (актуальність відстежуємо за `id`). Кожен пацієнт
    перевставляється ≤ (к-ть порогів + 1) разів → O(log n) амортизовано.

    Інтерфейс `push` / `pop` / `__len__` робить його повноцінною
    політикою для `run_single_server`.
    """

    def __init__(self, esc: tuple[tuple[int, int], ...] = ESCALATION, floor: int = SAFETY_FLOOR) -> None:
        self.esc = esc
        self.floor = floor
        self._h: list[tuple] = []
        self._cross: list[tuple] = []
        self._live: dict[int, int] = {}
        self._seq = 0
        self._cseq = 0

    def _key(self, patient: Patient, bump: int) -> tuple:
        return (min(patient.severity, max(self.floor, patient.severity - bump)), patient.arrival_time)

    def push(self, patient: Patient) -> None:
        heapq.heappush(self._h, (self._key(patient, 0), self._seq, patient))
        self._live[patient.id] = self._seq
        self._seq += 1
        for thr, bump in self.esc:                                   # розклад перетинів порогів
            heapq.heappush(self._cross, (patient.arrival_time + thr, self._cseq, bump, patient))
            self._cseq += 1

    def pop(self, now: float) -> Patient:
        while self._cross and self._cross[0][0] <= now:           # застосувати перетини до 'now'
            crossing_time, _, bump, patient = heapq.heappop(self._cross)
            if patient.id in self._live:                                # ще чекає → новий запис, старий протухне
                heapq.heappush(self._h, (self._key(patient, bump), self._seq, patient))
                self._live[patient.id] = self._seq
                self._seq += 1
        while True:                                               # виймаємо, пропускаючи протухлі
            key, seq, patient = heapq.heappop(self._h)
            if self._live.get(patient.id) == seq:
                del self._live[patient.id]
                return patient

    def __len__(self) -> int:
        return len(self._live)


def simulate_step_aging(
    patients: list[Patient], esc: tuple[tuple[int, int], ...] = ESCALATION, floor: int = SAFETY_FLOOR,
) -> list[Patient]:
    """Порогова ескалація на купі з лінивим видаленням — O(log n) амортизовано."""
    return run_single_server(patients, StepLazyHeap(esc, floor))


class ListStepPolicy:
    """Брутфорс-еталон порогового правила: щокроку `min` за ПОТОЧНИМ ескальованим
    рівнем (O(n)/крок). Для звірки з лінивою купою (`StepLazyHeap`)."""

    def __init__(self, esc: tuple[tuple[int, int], ...] = ESCALATION, floor: int = SAFETY_FLOOR) -> None:
        self._esc = esc
        self._floor = floor
        self._w: list[Patient] = []

    def push(self, patient: Patient) -> None:
        self._w.append(patient)

    def pop(self, now: float) -> Patient:
        patient = min(
            self._w,
            key=lambda candidate: (escalated_level(candidate, now, self._esc, self._floor),
                                   candidate.arrival_time))
        self._w.remove(patient)
        return patient

    def __len__(self) -> int:
        return len(self._w)


def simulate_step_aging_ref(
    patients: list[Patient], esc: tuple[tuple[int, int], ...] = ESCALATION, floor: int = SAFETY_FLOOR,
) -> list[Patient]:
    """Брутфорс-еталон (O(n)/крок): щокроку перебираємо всіх за ПОТОЧНИМ ескальованим рівнем."""
    return run_single_server(patients, ListStepPolicy(esc, floor))
