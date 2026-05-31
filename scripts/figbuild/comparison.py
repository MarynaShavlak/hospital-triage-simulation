"""Головне порівняння дисциплін (Фаза 5-7): середнє/максимум очікування,
таймлайни, голодування, повні розподіли та пропускна здатність."""
from __future__ import annotations

import numpy as np

from triage_sim import DANGER, SEV_COLORS, SEV_NAMES

from .constants import DISC_COLOR, DISC_LABEL, DISCS
from .helpers import label_bars, plt, timeline_panel


def fig_avg_wait_by_severity_09(d):
    m = d.seed42()["metrics"]
    levels = list(range(1, 6))
    x = np.arange(len(levels))
    w = 0.27
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(x - w, [m["fifo"][s]["avg"] for s in levels], w, label="FIFO", color="#5c6bc0")
    ax.bar(x, [m["priority"][s]["avg"] for s in levels], w, label="Priority", color="#26a69a")
    ax.bar(x + w, [m["aging"][s]["avg"] for s in levels], w, label="Priority + Aging", color="#ab47bc")
    ax.set_xticks(x)
    ax.set_xticklabels([SEV_NAMES[s] for s in levels], rotation=20, ha="right")
    ax.set_ylabel("Середній час очікування (хв)")
    ax.set_title("Середній час очікування за тяжкістю: FIFO vs Priority vs Aging", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def fig_timeline_10(d):
    fig, _ = timeline_panel(d.seed42()["served"])
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig


def fig_timeline_starving_11(d):
    served = d.seed42()["served"]
    row = 15
    fig, axes = timeline_panel(served, highlight_row=row)
    prio_subset = sorted(served["priority"], key=lambda p: p.arrival_time)[:25]
    fifo_subset = sorted(served["fifo"], key=lambda p: p.arrival_time)[:25]
    hp = prio_subset[row]
    hwait = hp.start_time - hp.arrival_time
    axes[1].annotate(
        f"Пацієнт L{hp.severity} чекав {hwait:.0f} хв!\n(під FIFO — лише {fifo_subset[row].wait_time:.0f} хв)",
        xy=(hp.arrival_time + hwait / 2, row),
        xytext=(hp.arrival_time + hwait / 2 - 50, row - 6),
        arrowprops=dict(arrowstyle="->", color="red", lw=2),
        color="red", fontweight="bold", fontsize=11, ha="center")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig


def fig_starvation_max_12(d):
    m = d.seed42()["metrics"]
    levels = list(range(1, 6))
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(levels, [m["fifo"][s]["max"] for s in levels], "o-", label="FIFO", color="#5c6bc0", lw=2, ms=8)
    ax.plot(levels, [m["priority"][s]["max"] for s in levels], "s-", label="Priority", color="#26a69a", lw=2, ms=8)
    ax.plot(levels, [m["aging"][s]["max"] for s in levels], "^-", label="Priority + Aging",
            color="#ab47bc", lw=2, ms=8)
    ax.set_xticks(levels)
    ax.set_xticklabels([SEV_NAMES[s] for s in levels], rotation=20, ha="right")
    ax.set_ylabel("МАКСИМАЛЬНИЙ час очікування (хв)")
    ax.set_title("Голодування легких випадків: max очікування за тяжкістю", fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)
    starve = m["priority"][5]["max"]
    ax.annotate(f"Голодування L5!\nдо {starve:.0f} хв під Priority", xy=(5, starve),
                xytext=(3.2, starve * 0.78), arrowprops=dict(arrowstyle="->", color="red"),
                color="red", fontweight="bold")
    fig.tight_layout()
    return fig


def fig_violin_distributions_13(d):
    s = d.seed42()
    served, pts = s["served"], s["pts"]
    counts = {sev: sum(1 for p in pts if p.severity == sev) for sev in range(1, 6)}
    fig, axes = plt.subplots(1, 5, figsize=(19, 5))
    for idx, sev in enumerate(range(1, 6)):
        ax = axes[idx]
        data, colors = [], []
        for disc in DISCS:
            w = [p.wait_time for p in served[disc] if p.severity == sev]
            data.append(w if w else [0])
            colors.append(DISC_COLOR[disc])
        parts = ax.violinplot(data, showmeans=True, showextrema=True, widths=0.8)
        for pc, col in zip(parts["bodies"], colors, strict=True):
            pc.set_facecolor(col)
            pc.set_alpha(0.6)
        ax.axhline(DANGER[sev], color="red", ls="--", lw=1, alpha=0.6)
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(["FIFO", "Priority", "Aging"], rotation=20, fontsize=8)
        ax.set_title(f"L{sev} (n={counts[sev]})\nпоріг {DANGER[sev]} хв", fontsize=10, fontweight="bold")
        if idx == 0:
            ax.set_ylabel("Очікування (хв)")
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Графік 4: повні розподіли очікувань за рівнями (один прогін, seed=42)",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


def fig_throughput_14(d):
    t = d.throughput()
    n = d.runs
    served_n, util, sumwait = t["served_n"], t["util"], t["sumwait"]
    totals = {disc: sum(sumwait[disc].values()) for disc in DISCS}
    labels = [DISC_LABEL[disc] for disc in DISCS]
    x = np.arange(3)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    ax = axes[0]
    served_avg = [served_n[disc] / n for disc in DISCS]
    util_avg = [np.mean(util[disc]) * 100 for disc in DISCS]
    ax.bar(x - 0.2, served_avg, 0.4, label="обслужено/зміну", color="#5c6bc0", edgecolor="black")
    ax2 = ax.twinx()
    ax2.bar(x + 0.2, util_avg, 0.4, label="завантаженість %", color="#26a69a", edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Обслужено за зміну")
    ax2.set_ylabel("Завантаженість (%)")
    ax.set_ylim(0, 200)
    ax2.set_ylim(0, 100)
    label_bars(ax, x - 0.2, served_avg, fmt="{:.0f}", dy=3)
    label_bars(ax2, x + 0.2, util_avg, fmt="{:.0f}%", dy=2)
    ax.set_title("Пропускна здатність ОДНАКОВА\nлікар не став швидшим", fontweight="bold")
    ax = axes[1]
    bottom = np.zeros(3)
    for sev in range(1, 6):
        vals = [sumwait[disc][sev] / n for disc in DISCS]
        ax.bar(x, vals, 0.55, bottom=bottom, label=f"L{sev}", color=SEV_COLORS[sev],
               edgecolor="white", linewidth=0.5)
        bottom += vals
    label_bars(ax, x, [totals[disc] / n for disc in DISCS], fmt="{:.0f}", dy=100)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Сумарне очікування за зміну (хв)")
    ax.set_title("Сумарне очікування РІЗНЕ\nі перерозподілене за тяжкістю", fontweight="bold")
    ax.legend(title="Рівень", fontsize=8, loc="upper left")
    fig.tight_layout()
    return fig


FIGURES = [
    ("09_graph1_avg_wait_by_severity", fig_avg_wait_by_severity_09),
    ("10_graph2_timeline", fig_timeline_10),
    ("11_graph2_timeline_starving", fig_timeline_starving_11),
    ("12_graph3_starvation_max", fig_starvation_max_12),
    ("13_graph4_violin_distributions", fig_violin_distributions_13),
    ("14_graph5_throughput", fig_throughput_14),
]
