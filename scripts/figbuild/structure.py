"""Графіки механіки структури (Фаза 3): двійкова купа та дисципліна aging.

04-06 — як влаштована купа (дерево, sift-up, sift-down) через навчальні
утиліти `triage_sim.heap_demo`; 07-08 — крива «дорослішання» пріоритету та
компроміс порога aging.
"""
from __future__ import annotations

import copy
import heapq

import numpy as np

from triage_sim import (
    SEV_COLORS,
    draw_heap,
    generate_patients,
    metrics_by_severity,
    sift_down_steps,
    sift_up_steps,
    simulate,
    simulate_aging,
)

from .constants import AGING_THR
from .helpers import plt


def fig_heap_tree_04(d):
    demo = [(3, "P1"), (5, "P2"), (2, "P3"), (4, "P4"), (1, "P5"), (5, "P6"), (4, "P7")]
    h: list = []
    for x in demo:
        heapq.heappush(h, x)
    fig, ax = plt.subplots(figsize=(8, 5))
    draw_heap(ax, h, "Купа пацієнтів (min-heap за тяжкістю)\nу корені — найтяжчий")
    ax.text(0.5, -3.0, f"Масив: {[s for s, _ in h]}   (індекси 0..{len(h) - 1})",
            ha="center", fontsize=10, family="monospace")
    ax.text(0.5, -2.7, "батько i → (i-1)//2     діти i → 2i+1, 2i+2", ha="center", fontsize=9, color="#555")
    fig.tight_layout()
    return fig


def fig_heap_sift_up_05(d):
    start = [(2, "A"), (3, "B"), (4, "C"), (5, "D"), (4, "E"), (5, "F")]
    steps = sift_up_steps(start, (1, "NEW"))
    frames = [steps[0], steps[2], steps[4]]
    titles = ["1) Новий критичний (sev=1)\nдодається в КІНЕЦЬ",
              "2) 1 < батько (4) → обмін\nспливає вгору",
              "3) 1 < батько (2) → обмін\nстало коренем. Готово"]
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.2))
    for ax, (arr, hl, sw), title in zip(axes, frames, titles, strict=True):
        draw_heap(ax, arr, title, highlight={hl}, swap=set(sw) if sw else None)
    fig.suptitle('PUSH = sift-up: новий елемент "спливає" вгору, поки не стане на місце',
                 fontweight="bold", y=1.04)
    fig.tight_layout()
    return fig


def fig_heap_sift_down_06(d):
    start = [(1, "P5"), (2, "P3"), (3, "P1"), (5, "P2"), (4, "P4"), (5, "P6"), (4, "P7")]
    steps = sift_down_steps(start)
    frames = [steps[0], steps[1], steps[-1]]
    titles = ["1) Беремо корінь (sev=1, обслужили).\nОстанній (4) → у корінь",
              "2) 4 > менша дитина (2) → обмін\nтоне вниз",
              "3) 4 ≤ дітей → стоп.\nКупа відновлена, корінь=2"]
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.2))
    for ax, (arr, hl, sw), title in zip(axes, frames, titles, strict=True):
        draw_heap(ax, arr, title, highlight={hl}, swap=set(sw) if sw else None)
    fig.suptitle('POP = sift-down: корінь забрали, останній елемент "тоне" вниз до місця',
                 fontweight="bold", y=1.04)
    fig.tight_layout()
    return fig


def fig_aging_priority_curve_07(d):
    fig, ax = plt.subplots(figsize=(11, 6))
    waits = np.linspace(0, 180, 200)
    for sev in [3, 4, 5]:
        ax.plot(waits, sev - waits / AGING_THR, lw=2.5, color=SEV_COLORS[sev],
                label=f"Пацієнт L{sev} (чекає від t=0)")
    for lvl in range(1, 6):
        ax.axhline(lvl, color="gray", ls=":", alpha=0.5)
        ax.text(183, lvl, f"L{lvl}", va="center", fontsize=9, color="gray")
    ax.scatter([45, 90, 135], [4, 3, 2], color="#43a047", s=80, zorder=5, ec="black")
    ax.annotate("L5 чекав 135 хв →\nефективно L2!", xy=(135, 2), xytext=(95, 0.8),
                arrowprops=dict(arrowstyle="->", color="darkgreen"),
                color="darkgreen", fontweight="bold", fontsize=10)
    ax.set_xlabel("Час очікування (хв)")
    ax.set_ylabel("Ефективний пріоритет (менше = тяжчий)")
    ax.set_title("Aging: як ефективний пріоритет «дорослішає» з часом очікування", fontweight="bold")
    ax.invert_yaxis()
    ax.legend(loc="upper right")
    ax.set_xlim(0, 195)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    return fig


def fig_aging_threshold_tradeoff_08(d):
    pts = generate_patients(seed=42)
    mp_ref = metrics_by_severity(simulate(copy.deepcopy(pts), "priority"))
    thresholds = [10, 20, 30, 45, 60, 90, 120]
    l1_avgs, l5_maxs = [], []
    for thr in thresholds:
        m = metrics_by_severity(simulate_aging(copy.deepcopy(pts), thr))
        l1_avgs.append(m[1]["avg"])
        l5_maxs.append(m[5]["max"])
    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax1.plot(thresholds, l1_avgs, "o-", color="#d32f2f", lw=2.5, ms=8)
    ax1.set_xlabel("Поріг aging (хв)")
    ax1.set_ylabel("Очікування критичних L1 (хв)", color="#d32f2f")
    ax1.tick_params(axis="y", labelcolor="#d32f2f")
    ax1.axhline(mp_ref[1]["avg"], color="#d32f2f", ls=":", alpha=0.6)
    ax1.text(122, mp_ref[1]["avg"], " ідеал\n (pure prio)", color="#d32f2f", fontsize=8, va="center")
    ax2 = ax1.twinx()
    ax2.plot(thresholds, l5_maxs, "s-", color="#43a047", lw=2.5, ms=8)
    ax2.set_ylabel("Макс. очікування легких L5 (хв)", color="#43a047")
    ax2.tick_params(axis="y", labelcolor="#43a047")
    ax1.axvline(45, color="gray", ls="--", alpha=0.7)
    ax1.text(46, ax1.get_ylim()[1] * 0.9, "обраний поріг = 45", fontsize=10, fontweight="bold")
    ax1.set_title("Компроміс aging: більший поріг → краще критичним,\nале гірше легким", fontweight="bold")
    fig.tight_layout()
    return fig


FIGURES = [
    ("04_heap_tree", fig_heap_tree_04),
    ("05_heap_sift_up", fig_heap_sift_up_05),
    ("06_heap_sift_down", fig_heap_sift_down_06),
    ("07_aging_priority_curve", fig_aging_priority_curve_07),
    ("08_aging_threshold_tradeoff", fig_aging_threshold_tradeoff_08),
]
