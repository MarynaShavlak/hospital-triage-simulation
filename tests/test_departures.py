"""Регресійні інваріанти для моделей із ВИБУТТЯМ (reneging / deterioration).

На відміну від купної сім'ї, ці рушії не мають еталонної реалізації для
bit-у-біт звірки. Тож фіксуємо їхні структурні інваріанти — збереження
пацієнтів, хто саме може вибути, монотонність тяжкості, межі часу очікування.
Перевірки навмисно інваріантні (а не «золоті числа»), щоб не ламатися від
зміни версії NumPy чи параметрів.
"""
import copy
import math

import pytest

from triage_sim import (
    assign_deterioration,
    assign_patience,
    assign_patience_det,
    generate_patients,
    simulate_deter_reneg,
    simulate_deterioration,
    simulate_reneging,
)

DISCIPLINES = ["fifo", "priority", "aging"]


def _ids(patients):
    return {patient.id for patient in patients}


# ---------------------------------------------------------------------------
# Підготовка атрибутів (assign_*)
# ---------------------------------------------------------------------------

def test_assign_patience_l1_infinite_others_finite():
    pts = assign_patience(generate_patients(seed=1), seed=1)
    for patient in pts:
        if patient.severity == 1:
            assert patient.patience == math.inf            # критичні ніколи не йдуть
        else:
            assert 15.0 <= patient.patience < math.inf     # решта — скінченний поріг, не нижче підлоги


def test_assign_deterioration_schedule_shape():
    pts = assign_deterioration(generate_patients(seed=2), seed=2)
    for patient in pts:
        # рівно (orig_severity − 1) порогів погіршення, у зростаючому порядку
        assert len(patient.det_times) == patient.orig_severity - 1
        assert patient.det_times == sorted(patient.det_times)
        assert patient.orig_severity == patient.severity         # на старті ще не погіршився


# ---------------------------------------------------------------------------
# Reneging (LWBS)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("disc", DISCIPLINES)
@pytest.mark.parametrize("seed", range(8))
def test_reneging_conserves_patients(disc, seed):
    base = generate_patients(seed=seed)
    served, reneged = simulate_reneging(assign_patience(copy.deepcopy(base), seed=seed), disc)
    # кожен пацієнт — рівно раз: або обслужений, або пішов
    assert len(served) + len(reneged) == len(base)
    assert _ids(served).isdisjoint(_ids(reneged))
    assert _ids(served) | _ids(reneged) == _ids(base)


@pytest.mark.parametrize("disc", DISCIPLINES)
@pytest.mark.parametrize("seed", range(8))
def test_reneging_invariants(disc, seed):
    base = generate_patients(seed=seed)
    served, reneged = simulate_reneging(assign_patience(copy.deepcopy(base), seed=seed), disc)
    # критичні (L1) ніколи не йдуть
    assert all(patient.severity != 1 for patient in reneged)
    # хто пішов — мав скінченний поріг і пішов саме на ньому
    for patient in reneged:
        assert patient.patience < math.inf
        assert patient.leave_time == pytest.approx(patient.arrival_time + patient.patience)
    # обслужений дочекався В МЕЖАХ свого терпіння
    for patient in served:
        assert 0 <= patient.wait_time <= patient.patience


# ---------------------------------------------------------------------------
# Deterioration (погіршення + смерть)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("disc", DISCIPLINES)
@pytest.mark.parametrize("seed", range(8))
def test_deterioration_conserves_and_severity_bounded(disc, seed):
    base = generate_patients(seed=seed)
    served, died = simulate_deterioration(assign_deterioration(copy.deepcopy(base), seed=seed), disc)
    assert len(served) + len(died) == len(base)
    assert _ids(served).isdisjoint(_ids(died))
    assert _ids(served) | _ids(died) == _ids(base)
    # тяжкість лише зростає (severity не більша за початкову) і не виходить за [1, orig]
    for patient in served:
        assert 1 <= patient.severity <= patient.orig_severity
    # померли — лише ті, хто став критичним (L1); із проставленою відміткою часу смерті
    for patient in died:
        assert patient.severity == 1
        assert patient.death_time is not None


# ---------------------------------------------------------------------------
# Повна модель (погіршення + смерть + вихід легких)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("disc", DISCIPLINES)
@pytest.mark.parametrize("seed", range(8))
def test_deter_reneg_partitions_patients(disc, seed):
    base = generate_patients(seed=seed)
    pts = assign_patience_det(assign_deterioration(copy.deepcopy(base), seed=seed), seed=seed)
    served, died, left = simulate_deter_reneg(pts, disc)
    # три групи покривають усіх і не перетинаються (розбиття)
    assert len(served) + len(died) + len(left) == len(base)
    assert _ids(served) | _ids(died) | _ids(left) == _ids(base)
    # померли критичними (L1); пішли — лише некритичні (severity > 1)
    assert all(patient.severity == 1 for patient in died)
    assert all(patient.severity > 1 for patient in left)
