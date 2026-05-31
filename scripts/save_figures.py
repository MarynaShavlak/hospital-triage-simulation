#!/usr/bin/env python3
"""Регенерує всі 23 графіки дослідження у `figures/NN_*.png`.

Раніше графіки існували лише як інлайн-виводи ноутбука (`plt.show()`), тож НЕ
відтворювалися з коду. Цей скрипт будує їх тим самим кодом побудови, але бере
дані й алгоритми з публічного API `triage_sim`, і пише у файли.

Сам код побудови живе в пакеті `figbuild/` (по модулю на фазу дослідження);
тут — лише тонкий CLI поверх реєстру `figbuild.FIGURES`.

Запуск:
    python scripts/save_figures.py                 # усі графіки у <repo>/figures
    python scripts/save_figures.py --only 01,09,23  # лише вибрані (за номером)
    python scripts/save_figures.py --runs 60        # швидше (менше прогонів Монте-Карло)
    python scripts/save_figures.py --out /tmp/fig   # в інший каталог

Монте-Карло / harm / reneging / deterioration типово рахуються на 300 прогонах
(як у ноутбуці), тож повний прогін триває ~хвилину.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401  (додає ../src у sys.path за потреби)
from figbuild import FIGURES, Data, save_fig


def main():
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Регенерує всі графіки дослідження у figures/NN_*.png.")
    parser.add_argument("--out", type=Path, default=repo_root / "figures",
                        help="каталог для збереження (типово: <repo>/figures)")
    parser.add_argument("--runs", type=int, default=300,
                        help="к-ть прогонів Монте-Карло/harm/reneging/deter (типово 300, як у ноутбуці)")
    parser.add_argument("--only", default="",
                        help="через кому номери графіків, напр. 01,09,23 (типово — усі)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    only = {token.strip().zfill(2) for token in args.only.split(",") if token.strip()}

    data = Data(args.runs)
    selected = [(name, fn) for name, fn in FIGURES if not only or name[:2] in only]
    print(f"Будуємо {len(selected)} графік(ів) → {args.out}  (runs={args.runs})")
    for name, fn in selected:
        save_fig(fn(data), name, args.out)
        print(f"  ✓ {name}.png")
    print("Готово.")


if __name__ == "__main__":
    main()
