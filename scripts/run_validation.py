#!/usr/bin/env python3
"""Валідація рушія проти точних формул теорії черг (Фаза 8).

Доводить, що симуляція фізично коректна, а не «просто гарна картинка»:

* **M/G/1** — середнє очікування FIFO звіряється з формулою
  Pollaczek–Khinchine (загальний розподіл часу обслуговування).
* **M/M/c** — багатосерверна логіка `simulate_md` звіряється з точним
  розв'язком Erlang-C на експоненційному обслуговуванні.

Бібліотека (`triage_sim.validation`) лише рахує й повертає числа; усе
форматування звіту — тут, у скрипті.
"""
import _bootstrap  # noqa: F401  (додає ../src у sys.path за потреби)

from triage_sim import validate_mg1, validate_mmc


def main():
    print("=" * 60)
    print("ВАЛІДАЦІЯ 1 — M/G/1 (Pollaczek–Khinchine)")
    print("=" * 60)
    result = validate_mg1()
    ci_low, ci_high = result["ci"]
    print(f"rho = lam*E[S] = {result['rho']:.3f}")
    print(f"Теорія (Pollaczek–Khinchine): Wq = {result['Wq_theory']:.2f} хв")
    print(f"Симуляція (FIFO):             Wq = {result['Wq_sim']:.2f} хв,  95% CI [{ci_low:.2f}; {ci_high:.2f}]")
    print("Вердикт:", "теорія всередині CI → рушій валідний" if result["ok"] else "розбіжність")

    print("\n" + "=" * 60)
    print("ВАЛІДАЦІЯ 2 — M/M/c (Erlang-C)")
    print("=" * 60)
    print("Валідація M/M/c (Erlang-C, експоненційне лікування):")
    for result in validate_mmc():
        ci_low, ci_high = result["ci"]
        print(f"  c={result['c']}, rho={result['rho']}: Erlang-C = {result['Wq_theory']:5.2f} хв | "
              f"сим = {result['Wq_sim']:5.2f} хв, 95% CI [{ci_low:.2f}; {ci_high:.2f}]  "
              f"{'OK' if result['ok'] else 'РОЗБІЖНІСТЬ'}")

    print("\nЯкщо теорія потрапляє всередину 95% довірчого інтервалу симуляції —")
    print("рушій відтворює класичні результати теорії черг і є валідним.")


if __name__ == "__main__":
    main()
