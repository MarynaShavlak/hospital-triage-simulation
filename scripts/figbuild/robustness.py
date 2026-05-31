"""Надійність висновків (Фаза 9-10): Монте-Карло на 300 прогонах, seed=42 на тлі
розподілу та чутливість переваги Priority до навантаження ρ."""
from __future__ import annotations

import numpy as np

from .constants import DISC_COLOR
from .helpers import plt, style_boxplot


def fig_montecarlo_boxplots_17(d):
    res = d.monte()["res"]
    colors = list(DISC_COLOR.values())
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    bp = axes[0].boxplot([res["f_L1"], res["p_L1"], res["a_L1"]], patch_artist=True, showfliers=False)
    axes[0].set_xticklabels(["FIFO", "Priority", "Aging"])
    style_boxplot(bp, colors)
    axes[0].set_ylabel("Середнє очікування (хв)")
    axes[0].set_title("Критичні (L1): середнє очікування\nза 300 прогонів", fontweight="bold")
    axes[0].grid(axis="y", alpha=0.3)
    bp = axes[1].boxplot([res["f_L5"], res["p_L5"], res["a_L5"]], patch_artist=True, showfliers=False)
    axes[1].set_xticklabels(["FIFO", "Priority", "Aging"])
    style_boxplot(bp, colors)
    axes[1].set_ylabel("Максимальне очікування (хв)")
    axes[1].set_title("Легкі (L5): максимальне очікування\nза 300 прогонів", fontweight="bold")
    axes[1].grid(axis="y", alpha=0.3)
    sp = np.array(res["speedup"])
    axes[2].hist(sp, bins=30, color="#26a69a", alpha=0.7, edgecolor="black")
    axes[2].axvline(sp.mean(), color="red", lw=2, label=f"середнє = {sp.mean():.1f}×")
    axes[2].axvline(np.median(sp), color="darkblue", lw=2, ls="--", label=f"медіана = {np.median(sp):.1f}×")
    axes[2].axvline(11, color="orange", lw=2, ls=":", label="seed=42: 11× (викид!)")
    axes[2].set_xlabel("Прискорення критичних (FIFO / Priority)")
    axes[2].set_ylabel("Кількість прогонів")
    axes[2].set_title("Розподіл прискорення\nкритичних пацієнтів", fontweight="bold")
    axes[2].legend(fontsize=9)
    fig.tight_layout()
    return fig


def fig_seed42_vs_montecarlo_18(d):
    m = d.monte()
    res, s42 = m["res"], m["s42"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    panels = [("f_L1", "FIFO: критичні (середнє)", s42["f_L1"], "#5c6bc0"),
              ("p_L5", "Priority: легкі (максимум)", s42["p_L5"], "#26a69a"),
              ("speedup", "Прискорення критичних (×)", s42["speedup"], "#ab47bc")]
    for ax, (k, title, val, color) in zip(axes, panels, strict=True):
        arr = np.array(res[k])
        ax.hist(arr, bins=30, color=color, alpha=0.6, edgecolor="black")
        ax.axvline(np.median(arr), color="darkblue", lw=2, ls="--", label=f"медіана = {np.median(arr):.1f}")
        ax.axvline(val, color="red", lw=2.5, label=f"seed=42 = {val:.0f}")
        pr = (arr < val).mean() * 100
        ax.set_title(f"{title}\nseed=42 — на рівні {pr:.0f}-го процентиля", fontweight="bold", fontsize=11)
        ax.legend(fontsize=9)
        ax.set_ylabel("Кількість прогонів")
    fig.tight_layout()
    return fig


def fig_load_sweep_19(d):
    data = d.sweep()
    rho = data["rho"]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.3))
    ax = axes[0]
    ax.plot(rho, data["fifo_L1"], "o-", color="#5c6bc0", lw=2.5, ms=7, label="FIFO")
    ax.plot(rho, data["prio_L1"], "s-", color="#26a69a", lw=2.5, ms=7, label="Priority")
    ax.plot(rho, data["aging_L1"], "^-", color="#ab47bc", lw=2.5, ms=7, label="Aging")
    ax.set_xlabel("Завантаженість лікаря ρ")
    ax.set_ylabel("Критичні: середнє очікування (хв)")
    ax.set_title("Критичні пацієнти:\nFIFO вибухає, Priority тримається", fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.axvline(0.85, color="gray", ls=":", alpha=0.6)
    ax = axes[1]
    ax.plot(rho, data["speedup"], "o-", color="#d32f2f", lw=3, ms=8)
    ax.fill_between(rho, 1, data["speedup"], alpha=0.12, color="#d32f2f")
    ax.axhline(1, color="black", ls="--", lw=1, alpha=0.6, label="немає переваги (1×)")
    ax.set_xlabel("Завантаженість лікаря ρ")
    ax.set_ylabel("Перевага Priority (у скільки разів швидше)")
    ax.set_title("ГОЛОВНЕ: перевага Priority\nРОСТЕ із завантаженням", fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    for xv, yv in [(rho[0], data["speedup"][0]), (rho[-1], data["speedup"][-1])]:
        ax.annotate(f"{yv:.1f}×", xy=(xv, yv), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontweight="bold", fontsize=10)
    ax = axes[2]
    ax.plot(rho, data["prio_L5max"], "D-", color="#43a047", lw=2.5, ms=7)
    ax.fill_between(rho, 0, data["prio_L5max"], alpha=0.12, color="#43a047")
    ax.set_xlabel("Завантаженість лікаря ρ")
    ax.set_ylabel("Голодування L5 під Priority: max (хв)")
    ax.set_title("Зворотний бік: голодування легких\nтеж росте із завантаженням", fontweight="bold")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


FIGURES = [
    ("17_montecarlo_boxplots", fig_montecarlo_boxplots_17),
    ("18_seed42_vs_montecarlo", fig_seed42_vs_montecarlo_18),
    ("19_load_sweep", fig_load_sweep_19),
]
