"""Графіки потоку пацієнтів (Фаза 1-2): прибуття, проміжки, розподіл тяжкості."""
from __future__ import annotations

import numpy as np

from triage_sim import SEV_COLORS, SEV_NAMES, generate_patients

from .helpers import plt


def fig_arrivals_poisson_vs_metronome_01(d):
    arrival_rate = 0.075
    rng = np.random.default_rng(42)
    inter = rng.exponential(1 / arrival_rate, size=180)
    arrival_times = np.cumsum(inter)
    mean_gap = 1 / arrival_rate
    n_show = 20
    poisson_arr = arrival_times[:n_show]
    metronome_arr = np.arange(1, n_show + 1) * mean_gap
    fig, axes = plt.subplots(2, 1, figsize=(13, 4.5), sharex=True)
    axes[0].vlines(metronome_arr, 0, 1, color="#5c6bc0", lw=2)
    axes[0].scatter(metronome_arr, [1] * n_show, color="#5c6bc0", s=60, zorder=3)
    axes[0].set_title('"Метроном" — рівно кожні 13.3 хв (НЕреалістично)', fontweight="bold", loc="left")
    axes[0].set_yticks([])
    axes[0].set_ylim(-0.6, 1.3)
    axes[1].vlines(poisson_arr, 0, 1, color="#e53935", lw=2)
    axes[1].scatter(poisson_arr, [1] * n_show, color="#e53935", s=60, zorder=3)
    axes[1].set_title("Процес Пуассона — реальні прибуття (скупчення + затишшя)", fontweight="bold", loc="left")
    axes[1].set_yticks([])
    axes[1].set_ylim(-0.6, 1.3)
    axes[1].set_xlabel("Час (хв)")
    cluster = poisson_arr[(poisson_arr >= 94) & (poisson_arr <= 101)]
    axes[1].annotate("скупчення: 3 за 5 хв", xy=(cluster.mean(), 0),
                     xytext=(cluster.mean() + 12, -0.45), color="darkred", fontsize=9,
                     fontweight="bold", ha="center",
                     arrowprops=dict(arrowstyle="->", color="darkred"))
    fig.tight_layout()
    return fig


def fig_interarrival_exponential_02(d):
    arrival_rate = 0.075
    rng = np.random.default_rng(42)
    inter = rng.exponential(1 / arrival_rate, size=180)
    mean_gap = 1 / arrival_rate
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.hist(inter, bins=30, density=True, color="#26a69a", edgecolor="black", alpha=0.7,
            label="Реальні проміжки (180 шт)")
    x = np.linspace(0, inter.max(), 200)
    ax.plot(x, arrival_rate * np.exp(-arrival_rate * x), "r-", lw=2.5,
            label=f"Теоретичний експоненційний\n(λ={arrival_rate}, середнє={mean_gap:.1f})")
    ax.axvline(mean_gap, color="blue", ls="--", lw=2, label=f"Середній проміжок = {mean_gap:.1f} хв")
    ax.set_xlabel("Проміжок між прибуттями (хв)")
    ax.set_ylabel("Щільність ймовірності")
    ax.set_title("Проміжки між прибуттями розподілені експоненційно", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    return fig


def fig_severity_and_arrivals_03(d):
    pts = generate_patients(seed=42)
    dist = {s: sum(1 for p in pts if p.severity == s) for s in range(1, 6)}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    levels = list(range(1, 6))
    axes[0].bar([SEV_NAMES[s] for s in levels], [dist[s] for s in levels],
                color=[SEV_COLORS[s] for s in levels], edgecolor="black")
    axes[0].set_title("Розподіл пацієнтів за тяжкістю", fontweight="bold")
    axes[0].set_ylabel("Кількість")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].hist([p.arrival_time for p in pts], bins=30, color="#5c6bc0", edgecolor="black")
    axes[1].set_title("Потік прибуттів у часі (процес Пуассона)", fontweight="bold")
    axes[1].set_xlabel("Час (хв)")
    axes[1].set_ylabel("Прибуттів")
    fig.tight_layout()
    return fig


FIGURES = [
    ("01_arrivals_poisson_vs_metronome", fig_arrivals_poisson_vs_metronome_01),
    ("02_interarrival_exponential", fig_interarrival_exponential_02),
    ("03_severity_and_arrivals", fig_severity_and_arrivals_03),
]
