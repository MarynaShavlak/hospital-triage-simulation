"""Тести коректності: різні реалізації мають давати ТОЙ САМИЙ результат.

Запуск:  ``pytest -q``  (або ``python -m pytest``) з кореня репозиторію.
Ці перевірки — той самий «доказ біт-у-біт», що й у відповідних клітинках ноутбука.
"""
import copy
import heapq
import random

import numpy as np
import pytest

from triage_sim import (
    SAFETY_FLOOR,
    MyHeap,
    Patient,
    erlang_c,
    escalated_level,
    generate_patients,
    metrics_by_severity,
    mmc_wq,
    simulate,
    simulate_aging,
    simulate_aging_heap,
    simulate_aging_list,
    simulate_bucket,
    simulate_fifo_deque,
    simulate_md,
    simulate_step_aging,
    simulate_step_aging_ref,
)


def _order(served):
    return [patient.id for patient in served]


def _waits(served):
    return [patient.wait_time for patient in served]


# ---------------------------------------------------------------------------
# Базова осудність
# ---------------------------------------------------------------------------

def test_all_patients_served():
    patients = generate_patients(seed=42)
    assert len(simulate(copy.deepcopy(patients), "fifo")) == 180
    assert len(simulate(copy.deepcopy(patients), "priority")) == 180


def test_priority_helps_critical_seed42():
    """Відтворення головного результату seed=42: критичні чекають набагато менше."""
    patients = generate_patients(seed=42)
    metrics_fifo = metrics_by_severity(simulate(copy.deepcopy(patients), "fifo"))
    metrics_priority = metrics_by_severity(simulate(copy.deepcopy(patients), "priority"))
    assert round(metrics_fifo[1]["avg"]) == 80
    assert round(metrics_priority[1]["avg"]) == 7
    assert metrics_fifo[1]["avg"] / metrics_priority[1]["avg"] > 5  # принаймні у кілька разів швидше


# ---------------------------------------------------------------------------
# Поведінкові гарантії дисциплін — не лише «однакові реалізації», а ЩО вони роблять
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(30))
def test_aging_bounds_l5_starvation(seed):
    """Головна теза aging: воно НЕ збільшує максимальне очікування легких (L5)
    проти чистого priority, а майже завжди різко зрізає голодування (перевірено
    на 100 seed: 0 порушень, медіана ≈0.43×). Без цього тесту тиха регресія в
    aging лишилася б непоміченою."""
    patients = generate_patients(seed=seed)
    prio = metrics_by_severity(simulate(copy.deepcopy(patients), "priority"))
    aging = metrics_by_severity(simulate_aging(copy.deepcopy(patients)))
    assert aging[5]["max"] <= prio[5]["max"] + 1e-9


def test_aging_tradeoff_seed42():
    """seed=42 (головна цифра проєкту): aging зрізає голодування L5 щонайменше
    вдвічі, але критичних (L1) тримає набагато краще за FIFO — тобто це не FIFO
    в маскуванні, а компроміс, що зберігає захист критичних."""
    patients = generate_patients(seed=42)
    fifo = metrics_by_severity(simulate(copy.deepcopy(patients), "fifo"))
    prio = metrics_by_severity(simulate(copy.deepcopy(patients), "priority"))
    aging = metrics_by_severity(simulate_aging(copy.deepcopy(patients)))
    assert aging[5]["max"] < 0.6 * prio[5]["max"]      # L5: суттєвий зріз голодування (факт ≈0.35×)
    assert aging[1]["avg"] < 0.5 * fifo[1]["avg"]      # L1: лишається близько до priority, далеко від FIFO


@pytest.mark.parametrize("severity", [2, 3, 4, 5])
def test_escalated_level_respects_safety_floor(severity):
    """Інваріант безпеки порогової ескалації: хоч скільки чекай, легкий пацієнт
    НЕ дотягнеться до реанімаційного рівня — ескальований рівень лишається в межах
    [SAFETY_FLOOR, початковий]. SAFETY_FLOOR=2 > 1, тож конкуренції з реальним L1 немає."""
    patient = Patient(0, 0.0, severity, 10.0)
    for waited in (0, 15, 30, 45, 60, 120, 100_000):
        level = escalated_level(patient, now=patient.arrival_time + waited)
        assert SAFETY_FLOOR <= level <= severity


def test_escalated_level_threshold_steps():
    """Порогове правило ESCALATION=((30,1),(60,2)): до 30 хв — без змін, від 30 —
    +1 рівень, від 60 — +2, з урахуванням підлоги безпеки."""
    l4 = Patient(0, 0.0, 4, 10.0)
    assert escalated_level(l4, 0) == 4         # щойно прибув
    assert escalated_level(l4, 29) == 4        # поріг 30 ще не перетнуто
    assert escalated_level(l4, 30) == 3        # від 30 хв: +1 рівень
    assert escalated_level(l4, 60) == 2        # від 60 хв: +2 рівні
    l5 = Patient(1, 0.0, 5, 5.0)
    assert escalated_level(l5, 100_000) == 3   # L5 −2 = 3: стеля ескалації, підлоги не дотягується


# ---------------------------------------------------------------------------
# Еквівалентність реалізацій — біт-у-біт
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(20))
def test_fifo_deque_equals_heap(seed):
    patients = generate_patients(seed=seed)
    heap_result = simulate(copy.deepcopy(patients), "fifo")
    deque_result = simulate_fifo_deque(copy.deepcopy(patients))
    assert _order(heap_result) == _order(deque_result)
    assert all(abs(heap_wait - deque_wait) < 1e-9
               for heap_wait, deque_wait in zip(_waits(heap_result), _waits(deque_result), strict=True))


@pytest.mark.parametrize("seed", range(50))
def test_aging_heap_equals_list(seed):
    patients = generate_patients(seed=seed)
    list_result = simulate_aging_list(copy.deepcopy(patients), 45)
    heap_result = simulate_aging_heap(copy.deepcopy(patients), 45)
    assert _order(list_result) == _order(heap_result)
    assert all(abs(list_wait - heap_wait) < 1e-9
               for list_wait, heap_wait in zip(_waits(list_result), _waits(heap_result), strict=True))


@pytest.mark.parametrize("seed", range(30))
def test_bucket_equals_priority(seed):
    patients = generate_patients(seed=seed)
    bucket_result = simulate_bucket(copy.deepcopy(patients))
    priority_result = simulate(copy.deepcopy(patients), "priority")
    assert _order(bucket_result) == _order(priority_result)


@pytest.mark.parametrize("seed", range(30))
def test_step_aging_lazyheap_equals_bruteforce(seed):
    patients = generate_patients(n=300, seed=seed)
    lazyheap_result = simulate_step_aging(copy.deepcopy(patients))
    bruteforce_result = simulate_step_aging_ref(copy.deepcopy(patients))
    assert _order(lazyheap_result) == _order(bruteforce_result)


@pytest.mark.parametrize("seed", range(20))
def test_simulate_md_one_server_equals_simulate(seed):
    patients = generate_patients(seed=seed)
    md_result = simulate_md(copy.deepcopy(patients), "priority", 1)
    single_result = simulate(copy.deepcopy(patients), "priority")
    assert _order(md_result) == _order(single_result)


def test_myheap_matches_heapq():
    random.seed(0)
    data = [(random.randint(1, 5), f"P{k}") for k in range(200)]
    my_heap = MyHeap()
    for item in data:
        my_heap.push(item)
    my_output = [my_heap.pop() for _ in range(len(data))]
    reference_heap = []
    for item in data:
        heapq.heappush(reference_heap, item)
    ref_output = [heapq.heappop(reference_heap) for _ in range(len(reference_heap))]
    assert my_output == ref_output


# ---------------------------------------------------------------------------
# Валідація проти теорії черг (швидкі, зменшені прогони)
# ---------------------------------------------------------------------------

def test_erlang_c_known_value():
    # M/M/1 (c=1): ймовірність очікування = ρ
    assert erlang_c(1, 0.5) == pytest.approx(0.5, abs=1e-9)


def test_mmc_wq_against_simulation_light():
    """Швидка валідація M/M/c: simulate_md ≈ Erlang-C на експоненційному лікуванні."""
    import statistics

    from triage_sim import gen_exponential

    ES = 11.0
    c, rho = 2, 0.8
    a = rho * c
    lam = a / ES
    Wq_theory = mmc_wq(lam, ES, c)
    run_means = [statistics.mean(patient.wait_time for patient in
                 simulate_md(gen_exponential(8000, lam, ES, seed), "fifo", c)[1000:])
                 for seed in range(8)]
    sim_mean = float(np.mean(run_means))
    # у межах 25% — груба, але достатня для швидкого тесту
    assert abs(sim_mean - Wq_theory) / Wq_theory < 0.25
