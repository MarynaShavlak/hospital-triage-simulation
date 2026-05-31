"""Візуалізація черги наживо (бонус): одна черга — три порядки, і трасування
push/pop на справжньому завантаженому моменті симуляції."""
from __future__ import annotations

import copy

import numpy as np
from matplotlib.patches import Patch

from triage_sim import Patient

from .constants import AGING_THR
from .helpers import plt, queue_box, severity_legend


def _trace_priority(patients, min_queue=4, want_steps=5):
    """Записує знімки Priority-черги лише коли вона завантажена (>= `min_queue`)."""
    arr = sorted(patients, key=lambda p: p.arrival_time)
    i = 0
    waiting: list[Patient] = []
    free = 0.0
    snapshots: list[dict] = []
    while i < len(arr) or waiting:
        newly = []
        while i < len(arr) and arr[i].arrival_time <= free:
            waiting.append(arr[i])
            newly.append(arr[i].id)
            i += 1
        if not waiting:
            free = arr[i].arrival_time
            while i < len(arr) and arr[i].arrival_time <= free:
                waiting.append(arr[i])
                newly.append(arr[i].id)
                i += 1
        waiting.sort(key=lambda p: (p.severity, p.arrival_time))
        picked = waiting[0]
        if len(waiting) >= min_queue and len(snapshots) < want_steps:
            snapshots.append({"time": free, "waiting": list(waiting),
                              "picked_id": picked.id, "newly": list(newly)})
        waiting.pop(0)
        picked.start_time = free
        free += picked.service_duration
    return snapshots


def fig_one_queue_three_orders_15(d):
    frozen = [
        Patient(id=11, arrival_time=0, severity=5, service_duration=5),
        Patient(id=12, arrival_time=20, severity=3, service_duration=12),
        Patient(id=13, arrival_time=35, severity=2, service_duration=18),
        Patient(id=14, arrival_time=40, severity=5, service_duration=5),
        Patient(id=15, arrival_time=50, severity=1, service_duration=25),
        Patient(id=16, arrival_time=55, severity=4, service_duration=8),
    ]
    now = 60

    def order_for(discipline):
        pts = list(frozen)
        if discipline == "fifo":
            return sorted(pts, key=lambda p: p.arrival_time)
        if discipline == "priority":
            return sorted(pts, key=lambda p: (p.severity, p.arrival_time))
        return sorted(pts, key=lambda p: (p.severity - (now - p.arrival_time) / AGING_THR, p.arrival_time))

    fig, axes = plt.subplots(4, 1, figsize=(13, 9))
    ax = axes[0]
    for idx, p in enumerate(frozen):
        queue_box(ax, idx, p.severity, p.id)
        ax.text(idx + 0.42, 0.08, f"чек.{now - p.arrival_time:.0f}хв", ha="center", fontsize=6.5)
    ax.set_xlim(-0.3, 6.3)
    ax.set_ylim(-0.2, 1.2)
    ax.axis("off")
    ax.set_title(f"СТАРТОВА ЧЕРГА: 6 пацієнтів у залі (поточний час t={now} хв)",
                 fontweight="bold", loc="left", fontsize=11)
    rows = [("fifo", "FIFO — за часом прибуття"), ("priority", "Priority — за тяжкістю"),
            ("aging", "Aging — за ефективним пріоритетом")]
    for r, (disc, dname) in enumerate(rows, start=1):
        ax = axes[r]
        for pos, p in enumerate(order_for(disc)):
            queue_box(ax, pos, p.severity, p.id)
            ax.text(pos + 0.42, 1.12, f"{pos + 1}", ha="center", fontsize=9, fontweight="bold", color="darkblue")
            if pos < 5:
                ax.annotate("", xy=(pos + 0.95, 0.5), xytext=(pos + 0.85, 0.5),
                            arrowprops=dict(arrowstyle="->", color="gray"))
        ax.set_xlim(-0.3, 6.3)
        ax.set_ylim(-0.2, 1.4)
        ax.axis("off")
        ax.set_title(f"{dname}  (порядок обслуговування →)", fontweight="bold", loc="left", fontsize=10)
    fig.legend(handles=severity_legend(short=True), loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Одна черга — три способи її розгребти", fontsize=14, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    return fig


def fig_priority_push_pop_trace_16(d):
    snaps = _trace_priority(copy.deepcopy(d.seed42()["pts"]), min_queue=4, want_steps=5)
    fig, axes = plt.subplots(len(snaps), 1, figsize=(13, len(snaps) * 1.5))
    axes = np.atleast_1d(axes)
    for r, snap in enumerate(snaps):
        ax = axes[r]
        wsorted = sorted(snap["waiting"], key=lambda p: (p.severity, p.arrival_time))
        for idx, p in enumerate(wsorted):
            if p.id == snap["picked_id"]:
                ec, lw, ls = "red", 3.0, "-"
            elif p.id in snap["newly"]:
                ec, lw, ls = "green", 2.5, "--"
            else:
                ec, lw, ls = "black", 1.0, "-"
            queue_box(ax, idx, p.severity, p.id, ec=ec, lw=lw, ls=ls)
            if p.id == snap["picked_id"]:
                ax.text(idx + 0.42, 1.15, "↑ беремо", ha="center", fontsize=8, color="red", fontweight="bold")
        ax.set_xlim(-0.3, len(wsorted) + 0.3)
        ax.set_ylim(-0.2, 1.5)
        ax.axis("off")
        ax.set_title(f"Крок {r + 1}: t={snap['time']:.0f}хв | у черзі {len(wsorted)} | "
                     f"+{len(snap['newly'])} нових (push) | беремо найтяжчого (pop)",
                     fontweight="bold", loc="left", fontsize=9)
    extra = [Patch(facecolor="white", edgecolor="red", lw=3, label="беремо (pop)"),
             Patch(facecolor="white", edgecolor="green", lw=2.5, ls="--", label="щойно прибув (push)")]
    fig.legend(handles=severity_legend(short=True, extra=extra), loc="lower center", ncol=7,
               bbox_to_anchor=(0.5, -0.03), fontsize=9)
    fig.suptitle("Priority-черга в завантажений момент: push (нові) + pop (найтяжчий)",
                 fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    return fig


FIGURES = [
    ("15_one_queue_three_orders", fig_one_queue_three_orders_15),
    ("16_priority_push_pop_trace", fig_priority_push_pop_trace_16),
]
