"""Спільні константи побудови графіків: палітра, підписи та порядок дисциплін.

Без залежності від matplotlib — щоб шар даних (`data.py`) міг їх імпортувати,
не тягнучи за собою графічний стек. Канонічний список дисциплін — у
`triage_sim.model`; тут лише короткий локальний псевдонім `DISCS`.
"""
from triage_sim import DISCIPLINES

# Короткий псевдонім канонічного списку (єдине джерело — triage_sim.model).
DISCS = DISCIPLINES

# Палітра й підписи дисциплін — єдині для всіх графіків.
DISC_COLOR = {"fifo": "#5c6bc0", "priority": "#26a69a", "aging": "#ab47bc"}
DISC_LABEL = {"fifo": "FIFO", "priority": "Priority", "aging": "Aging"}

# Поріг aging у всіх прогонах графіків (як у ноутбуці).
AGING_THR = 45
