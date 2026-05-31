"""Спільні плот-хелпери: усе, що повторювалося між графіками.

Цей модуль — єдине місце, що налаштовує matplotlib (headless-бекенд `Agg`) і
імпортує `pyplot`; решта модулів беруть `plt` саме звідси, тож бекенд гарантовано
обрано до першого створення фігури.

Винесено сюди (раніше дублювалося в кожному графіку):
* `save_fig`           — запис у `figures/NN.png` + закриття;
* `severity_legend`    — легенда «колір = рівень тяжкості» (L1..L5);
* `label_bars`         — підписи значень над стовпчиками;
* `grouped_level_bars` — групові стовпчики за рівнями L1..L5 × 3 дисципліни;
* `style_boxplot`      — фарбування boxplot + чорні медіани;
* `queue_box`          — «коробка пацієнта» (рамка + рівень + #id) у візуалізації черги;
* `timeline_panel`     — дві панелі-таймлайни FIFO vs Priority.
"""
from __future__ import annotations

import matplotlib
import numpy as np
from matplotlib.patches import FancyBboxPatch, Patch

from triage_sim import SEV_COLORS, SEV_NAMES

from .constants import DISC_COLOR, DISC_LABEL, DISCS

matplotlib.use("Agg")              # headless: лише запис у файли, без GUI
import matplotlib.pyplot as plt  # noqa: E402  (після вибору бекенду)


def save_fig(fig, name, out_dir):
    """Зберігає фігуру у `out_dir/name.png` (150 dpi, обрізані поля) і закриває її."""
    fig.savefig(out_dir / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def severity_legend(short=False, extra=None):
    """Хендли легенди «колір = рівень тяжкості» (L1..L5).

    `short=True` дає короткі підписи `L1..L5`, інакше повні назви рівнів.
    `extra` — додаткові хендли (напр., позначки push/pop), що дописуються в кінець.
    """
    handles = [Patch(facecolor=SEV_COLORS[s], label=f"L{s}" if short else SEV_NAMES[s])
               for s in range(1, 6)]
    return handles + list(extra) if extra else handles


def label_bars(ax, xs, values, fmt="{:.0f}%", dy=0.0, **text_kw):
    """Підписує `values` над позиціями `xs` (центри стовпчиків). За замовч. — жирним."""
    kw = {"ha": "center", "fontweight": "bold", **text_kw}
    for x, v in zip(xs, values, strict=True):
        ax.text(x, v + dy, fmt.format(v), **kw)


def bar_centers(bars):
    """Горизонтальні центри стовпчиків `bars` (для `label_bars`)."""
    return [b.get_x() + b.get_width() / 2 for b in bars]


def grouped_level_bars(ax, values_by_disc, width=0.26):
    """Групові стовпчики за рівнями L1..L5 для трьох дисциплін; виставляє підписи осі X."""
    x = np.arange(5)
    for j, disc in enumerate(DISCS):
        ax.bar(x + (j - 1) * width, values_by_disc[disc], width, label=DISC_LABEL[disc],
               color=DISC_COLOR[disc], alpha=0.8, edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(["L1", "L2", "L3", "L4", "L5"])


def style_boxplot(bp, colors):
    """Фарбує коробки boxplot за `colors` (alpha 0.6) і робить медіани чорними."""
    for patch, color in zip(bp["boxes"], colors, strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black")
        med.set_linewidth(2)


def queue_box(ax, x, severity, pid, ec="black", lw=1.5, ls="-"):
    """«Коробка пацієнта» у черзі: кольорова рамка тяжкості + рівень + #id у позиції `x`."""
    ax.add_patch(FancyBboxPatch((x, 0), 0.85, 1, boxstyle="round,pad=0.02",
                                fc=SEV_COLORS[severity], ec=ec, lw=lw, ls=ls, zorder=2))
    ax.text(x + 0.42, 0.60, f"L{severity}", ha="center", fontsize=11, fontweight="bold")
    ax.text(x + 0.42, 0.30, f"#{pid}", ha="center", fontsize=8)


def timeline_panel(served_map, highlight_row=None):
    """Дві панелі-таймлайни (FIFO vs Priority): сіре = очікування, колір = лікування.

    Повертає `(fig, axes)`, щоб викликач міг додати анотацію (графіки 10, 11).
    `highlight_row` обводить вказаний рядок червоним (пацієнт, що голодує).
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), sharey=True)
    for ax, (disc, title) in zip(axes, [("fifo", "FIFO"), ("priority", "Priority")], strict=True):
        subset = sorted(served_map[disc], key=lambda p: p.arrival_time)[:25]
        for row, p in enumerate(subset):
            edge = "red" if row == highlight_row else "gray"
            lw = 2.5 if row == highlight_row else 1
            ax.barh(row, p.start_time - p.arrival_time, left=p.arrival_time,
                    color="lightgray", edgecolor=edge, linewidth=lw, height=0.6)
            ax.barh(row, p.service_duration, left=p.start_time,
                    color=SEV_COLORS[p.severity], edgecolor="black", height=0.6)
        ax.set_title(f"{title}\n(сіре = очікування, колір = лікування)", fontweight="bold")
        ax.set_xlabel("Час (хв)")
        ax.invert_yaxis()
    axes[0].set_ylabel("Пацієнти (за порядком прибуття)")
    fig.legend(handles=severity_legend(), loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.02))
    return fig, axes
