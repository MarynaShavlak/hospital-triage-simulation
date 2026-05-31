"""Смоук-тест фігурного шару: усі 23 графіки будуються без помилок.

Раніше `scripts/figbuild` перевіряв лише `ruff` — регресія в будь-якому графіку
(зламаний хелпер, перейменоване поле даних, помилка matplotlib) проходила б CI
зеленою. Тут кожна функція графіка викликається на малому `runs` і зберігається
у тимчасову теку; виняток = зламаний графік. Пакет `figbuild` живе в `scripts/`,
тож він на pytest-path (див. `pyproject.toml`).

Це смоук-тест (будується / не падає), а не звірка пікселів — числові результати
графіків і так покриті `test_experiments.py` та byte-baseline-звіркою вручну.
"""
import pytest
from figbuild import FIGURES, Data, save_fig

FIGURE_IDS = [name for name, _ in FIGURES]


@pytest.fixture(scope="module")
def data():
    # Малий runs: перевіряємо побудову, не точні числа. Білдери Data кешуються,
    # тож важкі прогони (МК/sweep/reneging/deter) виконуються один раз на весь модуль.
    return Data(runs=5)


def test_registry_has_23_unique_figures():
    assert len(FIGURES) == 23
    assert len(set(FIGURE_IDS)) == 23                 # імена вихідних файлів унікальні


@pytest.mark.parametrize(("name", "fn"), FIGURES, ids=FIGURE_IDS)
def test_figure_builds_and_saves(name, fn, data, tmp_path):
    save_fig(fn(data), name, tmp_path)
    assert (tmp_path / f"{name}.png").stat().st_size > 0
