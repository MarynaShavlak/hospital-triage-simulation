"""triage_sim — симуляція приймального відділення лікарні.

Порівнює три дисципліни обслуговування черги — **FIFO**, **Priority** та
**Priority + Aging** — на реалістичному пуассонівському потоці пацієнтів, і
показує, чому черга з пріоритетами (binary heap) рятує життя критичних, який у
неї зворотний бік (голодування легких) і як його лікують через aging.

Швидкий старт:

    import copy
    from triage_sim import generate_patients, simulate, simulate_aging, metrics_by_severity

    patients = generate_patients(seed=42)
    fifo  = metrics_by_severity(simulate(copy.deepcopy(patients), "fifo"))
    prio  = metrics_by_severity(simulate(copy.deepcopy(patients), "priority"))
    aging = metrics_by_severity(simulate_aging(copy.deepcopy(patients)))  # поріг = DEFAULT_AGING_THRESHOLD
    print("Критичні (L1) середнє очікування, хв:",
          round(fifo[1]["avg"]), "→", round(prio[1]["avg"]))

Повний наратив, результати та графіки — у каталозі `docs/`.
"""
from .aging import (
    ESCALATION,
    SAFETY_FLOOR,
    StepLazyHeap,
    escalated_level,
    simulate_aging,
    simulate_aging_heap,
    simulate_aging_list,
    simulate_bucket,
    simulate_step_aging,
    simulate_step_aging_ref,
)
from .deterioration import (
    DEATH_THR,
    DET_RATE,
    assign_det_rate,
    assign_deterioration,
    assign_patience_det,
    simulate_deter_reneg,
    simulate_deterioration,
)
from .engines import simulate, simulate_fifo_deque, simulate_md
from .experiments import (
    deterioration_sensitivity,
    deterioration_stats,
    load_sweep,
    monte_carlo,
    reneging_stats,
    reneging_valve,
)
from .generation import generate_patients
from .heap_demo import MyHeap, draw_heap, sift_down_steps, sift_up_steps
from .metrics import DANGER, count_in_danger, metrics_by_severity
from .model import (
    BASE_SERVICE,
    DEFAULT_AGING_THRESHOLD,
    DISCIPLINES,
    SEV_COLORS,
    SEV_NAMES,
    SEVERITY_PROBS,
    Patient,
)
from .reneging import PATIENCE_MEAN, assign_patience, simulate_reneging
from .validation import (
    erlang_c,
    gen_exponential,
    mmc_wq,
    service_moments,
    validate_mg1,
    validate_mmc,
)

__version__ = "1.0.0"

__all__ = [
    # model
    "Patient", "SEV_COLORS", "SEV_NAMES", "SEVERITY_PROBS", "BASE_SERVICE", "DISCIPLINES",
    # generation
    "generate_patients",
    # engines
    "simulate", "simulate_fifo_deque", "simulate_md",
    # aging / queue variants
    "simulate_aging", "simulate_aging_heap", "simulate_aging_list",
    "simulate_bucket", "escalated_level", "StepLazyHeap",
    "simulate_step_aging", "simulate_step_aging_ref",
    "ESCALATION", "SAFETY_FLOOR", "DEFAULT_AGING_THRESHOLD",
    # metrics
    "metrics_by_severity", "count_in_danger", "DANGER",
    # validation
    "service_moments", "validate_mg1", "validate_mmc",
    "erlang_c", "mmc_wq", "gen_exponential",
    # experiments (спільне джерело для скриптів і графіків)
    "monte_carlo", "load_sweep", "reneging_stats", "reneging_valve",
    "deterioration_stats", "deterioration_sensitivity",
    # reneging
    "assign_patience", "simulate_reneging", "PATIENCE_MEAN",
    # deterioration
    "assign_deterioration", "simulate_deterioration", "assign_patience_det",
    "simulate_deter_reneg", "assign_det_rate", "DET_RATE", "DEATH_THR",
    # heap demo
    "MyHeap", "sift_up_steps", "sift_down_steps", "draw_heap",
]
