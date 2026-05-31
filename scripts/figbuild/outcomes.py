"""Від хвилин до життів (Фаза 11-13): метрика шкоди, відхід пацієнтів (LWBS) і
смертність за динамічної тяжкості."""
from __future__ import annotations

import numpy as np

from .constants import DISC_COLOR, DISC_LABEL, DISCS
from .helpers import bar_centers, grouped_level_bars, label_bars, plt


def fig_harm_threshold_sensitivity_20(d):
    h = d.harm()
    thresholds, sens = h["thresholds"], h["sens"]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for disc in DISCS:
        ax.plot(thresholds, sens[disc], "o-", color=DISC_COLOR[disc], lw=2.5, ms=8, label=DISC_LABEL[disc])
    ax.axvline(15, color="gray", ls=":", alpha=0.7)
    ax.annotate("CTAS L2\n(15 хв)", xy=(15, 70), fontsize=8, color="gray", ha="center")
    ax.set_xlabel("Поріг небезпеки для критичних (хв)")
    ax.set_ylabel("% критичних у небезпеці")
    ax.set_title("Чутливість: FIFO найгірший за БУДЬ-ЯКОГО порога", fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def fig_harm_by_discipline_21(d):
    acc = d.harm()["acc"]
    frac = {disc: [100 * np.sum(acc[disc][s]["danger"]) / np.sum(acc[disc][s]["total"]) for s in range(1, 6)]
            for disc in DISCS}
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    ax = axes[0]
    crit = [frac[disc][0] for disc in DISCS]
    bars = ax.bar([DISC_LABEL[disc] for disc in DISCS], crit,
                  color=[DISC_COLOR[disc] for disc in DISCS], alpha=0.8, edgecolor="black")
    label_bars(ax, bar_centers(bars), crit, fmt="{:.0f}%", dy=1.5, fontsize=13)
    ax.set_ylabel("% критичних (L1), що чекали > 10 хв")
    ax.set_title("ГОЛОВНЕ: критичні пацієнти в небезпеці\n(поріг 10 хв)", fontweight="bold")
    ax.set_ylim(0, 80)
    ax.grid(axis="y", alpha=0.3)
    ax = axes[1]
    grouped_level_bars(ax, frac)
    ax.set_ylabel("% пацієнтів за порогом небезпеки")
    ax.set_xlabel("Рівень тяжкості")
    ax.set_title("Повна картина: хто в небезпеці\nза кожної дисципліни", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def fig_reneging_lwbs_22(d):
    r = d.reneging()
    overall, lwbs = r["overall"], r["lwbs"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    ax = axes[0]
    vals = [100 * overall[disc]["left"] / overall[disc]["total"] for disc in DISCS]
    bars = ax.bar([DISC_LABEL[disc] for disc in DISCS], vals,
                  color=[DISC_COLOR[disc] for disc in DISCS], alpha=0.8, edgecolor="black")
    label_bars(ax, bar_centers(bars), vals, fmt="{:.1f}%", dy=0.15, fontsize=13)
    ax.axhline(5, color="red", ls="--", alpha=0.6, label="бажаний рівень <5%")
    ax.set_ylabel("% пацієнтів, що пішли (LWBS)")
    ax.set_title("Загальний рівень LWBS\nPriority виганяє вчетверо більше", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax = axes[1]
    rates = {disc: [100 * lwbs[disc][s]["left"] / lwbs[disc][s]["total"] if lwbs[disc][s]["total"] else 0
                    for s in range(1, 6)] for disc in DISCS}
    grouped_level_bars(ax, rates)
    ax.set_ylabel("% що пішли (LWBS)")
    ax.set_xlabel("Рівень тяжкості")
    ax.set_title("Хто йде: майже всі — легкі (L5)\nпід Priority — 23%", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def fig_deterioration_mortality_23(d):
    dd = d.deter()
    arrived_l1, arrived_l1_died, results = dd["arrived_l1"], dd["arrived_l1_died"], dd["R"]
    labels = [DISC_LABEL[disc] for disc in DISCS]
    naive_l1 = [100 * arrived_l1_died[disc] / arrived_l1 for disc in DISCS]
    real_l1 = [100 * results[disc]["l1_died"] / arrived_l1 for disc in DISCS]
    x = np.arange(3)
    w = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    ax = axes[0]
    ax.bar(x - w / 2, naive_l1, w, label="без клапана (reneging)", color="#b0b0b0", edgecolor="black")
    ax.bar(x + w / 2, real_l1, w, label="з клапаном (reneging)",
           color=[DISC_COLOR[disc] for disc in DISCS], edgecolor="black")
    label_bars(ax, x - w / 2, naive_l1, fmt="{:.0f}%", dy=1, fontweight="normal", fontsize=10)
    label_bars(ax, x + w / 2, real_l1, fmt="{:.0f}%", dy=1, fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("% прибулих критичних (L1), що померли")
    ax.set_title("Смертність критичних: роль клапана\nбез нього навіть Priority не рятує", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax = axes[1]
    died = [100 * results[disc]["died"] / results[disc]["total"] for disc in DISCS]
    left = [100 * results[disc]["left"] / results[disc]["total"] for disc in DISCS]
    ax.bar(x - w / 2, died, w, label="померли", color="#c62828", edgecolor="black")
    ax.bar(x + w / 2, left, w, label="пішли (LWBS)", color="#f9a825", edgecolor="black")
    label_bars(ax, x - w / 2, died, fmt="{:.1f}%", dy=0.2, fontsize=10)
    label_bars(ax, x + w / 2, left, fmt="{:.1f}%", dy=0.2, fontweight="normal", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("% пацієнтів")
    ax.set_title("Реалістична модель: компроміс\nPriority — найменше смертей, найбільше LWBS", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


FIGURES = [
    ("20_harm_threshold_sensitivity", fig_harm_threshold_sensitivity_20),
    ("21_harm_by_discipline", fig_harm_by_discipline_21),
    ("22_reneging_lwbs", fig_reneging_lwbs_22),
    ("23_deterioration_mortality", fig_deterioration_mortality_23),
]
