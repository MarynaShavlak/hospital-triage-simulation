"""Дозволяє запускати скрипти прямо з кореня репозиторію без встановлення пакета.

Кожен скрипт робить `import _bootstrap` першим рядком — це додає `../src` до
`sys.path`, якщо `triage_sim` ще не встановлено (`pip install -e .`).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
try:
    import triage_sim  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.abspath(_SRC))
