"""Пакет побудови графіків дослідження.

`FIGURES` — впорядкований реєстр `(ім'я_файлу, функція(Data) -> Figure)`, зібраний
із модулів за фазами дослідження:

* `flow`        — потік пацієнтів (01-03);
* `structure`   — купа та aging (04-08);
* `comparison`  — головне порівняння дисциплін (09-14);
* `queue_trace` — візуалізація черги наживо (15-16);
* `robustness`  — Монте-Карло та чутливість до навантаження (17-19);
* `outcomes`    — шкода, відхід, смертність (20-23).

Точка входу — `scripts/save_figures.py`, що бере звідси `FIGURES`, `Data` і `save_fig`.
"""
from .comparison import FIGURES as _comparison
from .data import Data
from .flow import FIGURES as _flow
from .helpers import save_fig
from .outcomes import FIGURES as _outcomes
from .queue_trace import FIGURES as _queue_trace
from .robustness import FIGURES as _robustness
from .structure import FIGURES as _structure

FIGURES = [*_flow, *_structure, *_comparison, *_queue_trace, *_robustness, *_outcomes]

__all__ = ["FIGURES", "Data", "save_fig"]
