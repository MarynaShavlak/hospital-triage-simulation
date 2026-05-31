"""Спільний хелпер для скриптів: обслужити FIFO / Priority / Aging на КОПІЯХ
одного набору пацієнтів. Використовує `run_main_comparison.py`.
"""
import copy

from triage_sim import simulate, simulate_aging


def served_by_discipline(patients, aging_threshold=45):
    """Обслужені списки для FIFO / Priority / Aging на КОПІЯХ одного набору пацієнтів."""
    return {
        "fifo": simulate(copy.deepcopy(patients), "fifo"),
        "priority": simulate(copy.deepcopy(patients), "priority"),
        "aging": simulate_aging(copy.deepcopy(patients), aging_threshold),
    }
