"""Дисципліна Aging («дорослішання») та споріднені структури черги.

Чиста priority має ваду — **голодування** (starvation): легкий пацієнт може
чекати вічно, поки прибувають тяжчі. Aging вирішує це: ефективний пріоритет
зростає з часом очікування. Три варіанти, по модулю на кожен:

* `linear` — лінійний aging (`severity − очікування/T`): список-еталон і купа O(log n);
* `bucket` — bucket-черга O(1) для дискретних рівнів (та сама priority, без log n);
* `step`   — нелінійне порогове правило зі стелею безпеки на купі з лінивим видаленням.

Усі рушії — тонкі обгортки над спільним `run_single_server`; відрізняються лише
політикою черги. Публічний псевдонім `simulate_aging` = купна лінійна версія.
"""
from .bucket import BucketPolicy, simulate_bucket
from .linear import (
    ListAgingPolicy,
    simulate_aging,
    simulate_aging_heap,
    simulate_aging_list,
)
from .step import (
    ESCALATION,
    SAFETY_FLOOR,
    ListStepPolicy,
    StepLazyHeap,
    escalated_level,
    simulate_step_aging,
    simulate_step_aging_ref,
)

__all__ = [
    # лінійний aging
    "ListAgingPolicy", "simulate_aging", "simulate_aging_heap", "simulate_aging_list",
    # bucket-черга
    "BucketPolicy", "simulate_bucket",
    # порогова ескалація
    "ESCALATION", "SAFETY_FLOOR", "escalated_level", "StepLazyHeap", "ListStepPolicy",
    "simulate_step_aging", "simulate_step_aging_ref",
]
