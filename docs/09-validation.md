# Фаза 8.5. Валідація рушія (M/G/1, M/M/c)

> Розділ 09 · [↑ Зміст документації](README.md) · [↑ Головний README](../README.md)

[← Механіка черги (push/pop, deque)](08b-queue-mechanics.md)    [Фаза 9. Монте-Карло: наскільки надійні числа →](10-monte-carlo.md)

---

## Фаза 8.5: Валідація рушія — чи він фізично правильний?

Усі попередні висновки тримаються на припущенні, що рушій рахує **правильно**. Перевіримо це не на власних очікуваннях, а на **точній аналітичній формулі**. Для дисципліни FIFO середнє очікування в черзі описує формула Поллачека–Хінчина (M/G/1) для пуассонівських прибуттів і довільного розподілу часу обслуговування. Якщо симуляція збігається з нею — рушій коректний.

Два нюанси: формула працює **лише для FIFO** (priority/aging порушують її умови) і описує **усталений режим**, тому потрібен довгий прогін і відкидання розгінного періоду (warm-up).

> **Примітка щодо реалізації.** `service_moments` показано з inline-розподілом; у пакеті він бере ті самі семплери, що й `generate_patients` (**єдине джерело** `SEVERITY_PROBS`), тож валідація звіряється рівно з тим, що симулюється. `simulate_md` у пакеті спирається на спільний драйвер — поведінка ідентична.

```python
import math

def service_moments(n=2_000_000, seed=1):
    """Перший і другий моменти часу обслуговування — з того самого розподілу,
    що й у generate_patients."""
    rng = np.random.default_rng(seed)
    sev = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.05, 0.15, 0.35, 0.30, 0.15])
    base = {1: 25, 2: 18, 3: 12, 4: 8, 5: 5}
    means = np.array([base[severity] for severity in sev], dtype=float)
    dur = np.maximum(2, rng.normal(means, means * 0.25))
    return dur.mean(), (dur ** 2).mean()

def validate_mg1(arrival_rate=0.075, n=20000, warmup=2000, runs=20):
    ES, ES2 = service_moments()
    rho = arrival_rate * ES
    Wq = arrival_rate * ES2 / (2 * (1 - rho))               # Pollaczek–Khinchine
    run_means = [statistics.mean(patient.wait_time for patient in
          simulate(generate_patients(n=n, arrival_rate=arrival_rate, seed=seed), 'fifo')[warmup:])
          for seed in range(runs)]
    sim_mean = float(np.mean(run_means)); std_error = float(np.std(run_means, ddof=1)) / np.sqrt(runs)
    ci_low, ci_high = sim_mean - 1.96 * std_error, sim_mean + 1.96 * std_error
    print(f"rho = lam*E[S] = {rho:.3f}")
    print(f"Теорія (Pollaczek–Khinchine): Wq = {Wq:.2f} хв")
    print(f"Симуляція (FIFO):             Wq = {sim_mean:.2f} хв,  95% CI [{ci_low:.2f}; {ci_high:.2f}]")
    print("Вердикт:", "теорія всередині CI → рушій валідний" if ci_low <= Wq <= ci_high else "розбіжність")

validate_mg1()
```


**Результат:**

```
rho = lam*E[S] = 0.848
Теорія (Pollaczek–Khinchine): Wq = 40.30 хв
Симуляція (FIFO):             Wq = 39.90 хв,  95% CI [38.35; 41.45]
Вердикт: теорія всередині CI → рушій валідний
```

### Кілька лікарів (M/G/c) та валідація Erlang-C

Досі був один лікар. Додамо `n_doctors`: стан лікарів — купа їхніх часів звільнення, завжди беремо найранішого вільного. При `n_doctors = 1` це той самий рушій, що раніше (перевіримо). Багатосерверну логіку валідуємо точною формулою **Erlang-C** для M/M/c (на експоненційному лікуванні, де вона точна).

Цікавий висновок: **голодування — здебільшого хвороба одного лікаря**. Із запасом потужності черга майже не встигає набратися, і перевага priority над FIFO для критичних різко зменшується. Тобто priority критичний саме тоді, коли система впирається в потужність.

```python
def simulate_md(patients, discipline='priority', n_doctors=1):
    """Як simulate, але c лікарів. Стан лікарів — купа часів звільнення."""
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0; waiting = []; counter = 0; served = []
    servers = [0.0] * n_doctors; heapq.heapify(servers)
    while i < len(arrivals) or waiting:
        earliest_free = servers[0]                      # найраніше вільний лікар
        while i < len(arrivals) and arrivals[i].arrival_time <= earliest_free:
            patient = arrivals[i]
            key = (patient.severity, patient.arrival_time, counter) if discipline == 'priority' else (patient.arrival_time, counter)
            heapq.heappush(waiting, (key, patient)); counter += 1; i += 1
        if waiting:
            free = heapq.heappop(servers)
            _, patient = heapq.heappop(waiting)
            patient.start_time = free; served.append(patient)
            heapq.heappush(servers, free + patient.service_duration)
        elif i < len(arrivals):
            free = heapq.heappop(servers)
            heapq.heappush(servers, max(free, arrivals[i].arrival_time))
        else:
            break
    return served

print("simulate_md готова")
```


**Результат:**

```
simulate_md готова
```

```python
# При n_doctors=1 новий рушій збігається зі старим simulate
same = all([patient.id for patient in simulate_md(copy.deepcopy(generate_patients(seed=seed)), 'priority', 1)]
           == [patient.id for patient in simulate(copy.deepcopy(generate_patients(seed=seed)), 'priority')]
           for seed in range(20))
print("simulate_md(n_doctors=1) == simulate:", same, "\n")

pts = generate_patients(seed=42)
print("Лікарі → очікування критичних і голодування легких (priority, seed=42):")
for c in (1, 2, 3):
    metrics = metrics_by_severity(simulate_md(copy.deepcopy(pts), 'priority', c))
    print(f"  {c} лікар(і): L1 avg = {metrics[1]['avg']:5.1f} хв | L5 max = {metrics[5]['max']:5.0f} хв")
```


**Результат:**

```
simulate_md(n_doctors=1) == simulate: True 

Лікарі → очікування критичних і голодування легких (priority, seed=42):
  1 лікар(і): L1 avg =   7.4 хв | L5 max =   703 хв
  2 лікар(і): L1 avg =   1.1 хв | L5 max =    68 хв
  3 лікар(і): L1 avg =   0.0 хв | L5 max =    11 хв
```

```python
# --- Валідація багатосерверної логіки: точна формула Erlang-C (M/M/c) ---
# На експоненційному лікуванні M/M/c має точний розв'язок. Якщо simulate_md
# збігається з ним — багатосерверна логіка фізично правильна (а не лише при c=1).

def erlang_c(c, a):
    """Ймовірність очікування (формула Erlang-C). a = пропонована загрузка lam*E[S]."""
    rho = a / c
    head = sum(a**k / math.factorial(k) for k in range(c))
    tail = a**c / math.factorial(c) / (1 - rho)
    return tail / (head + tail)

def mmc_wq(lam, ES, c):
    """Середнє очікування в черзі для M/M/c."""
    return erlang_c(c, lam * ES) / (c / ES - lam)

def gen_exponential(n, lam, ES, seed):
    """Тестовий потік: Пуассон + ЕКСПОНЕНЦІЙНЕ лікування (там Erlang-C точна)."""
    rng = np.random.default_rng(seed)
    arr = np.cumsum(rng.exponential(1 / lam, size=n))
    dur = rng.exponential(ES, size=n)
    return [Patient(j, float(arr[j]), 3, float(dur[j])) for j in range(n)]

ES, _ = service_moments()        # середній час лікування (~11.3 хв), щоб режим був реалістичним
print("Валідація M/M/c (Erlang-C, експоненційне лікування):")
for c, rho in [(2, 0.85), (3, 0.80)]:
    a = rho * c; lam = a / ES
    Wq_theory = mmc_wq(lam, ES, c)
    run_means = [statistics.mean(patient.wait_time for patient in
          simulate_md(gen_exponential(20000, lam, ES, seed), 'fifo', c)[2000:])   # warmup 2000
          for seed in range(20)]
    sim_mean = float(np.mean(run_means)); std_error = float(np.std(run_means, ddof=1)) / np.sqrt(len(run_means))
    ci_low, ci_high = sim_mean - 1.96 * std_error, sim_mean + 1.96 * std_error
    ok = ci_low <= Wq_theory <= ci_high
    print(f"  c={c}, rho={rho}: Erlang-C = {Wq_theory:5.2f} хв | "
          f"сим = {sim_mean:5.2f} хв, 95% CI [{ci_low:.2f}; {ci_high:.2f}]  {'OK' if ok else 'РОЗБІЖНІСТЬ'}")
```


**Результат:**

```
Валідація M/M/c (Erlang-C, експоненційне лікування):
  c=2, rho=0.85: Erlang-C = 29.45 хв | сим = 29.19 хв, 95% CI [27.78; 30.61]  OK
  c=3, rho=0.8: Erlang-C = 12.20 хв | сим = 12.16 хв, 95% CI [11.67; 12.65]  OK
```

### Висновки Фази 8.5

1. **Рушій валідовано аналітично.** Для FIFO симуляція збігається з формулою Поллачека–Хінчина (M/G/1) у межах довірчого інтервалу, а багатосерверна логіка — з Erlang-C (M/M/c). Це підтверджує, що рушій фізично правильний, а не просто «щось рахує».
2. **Голодування — переважно проблема дефіциту потужності.** Із 2–3 лікарями очікування критичних і максимум для легких різко падають: перевага priority майже зникає, бо черга не встигає набратися.
3. **Практичний сенс:** priority/aging критичні саме у завантаженій системі (один-два лікарі під пік), а не самі по собі.


---

[← Механіка черги (push/pop, deque)](08b-queue-mechanics.md)    [Фаза 9. Монте-Карло: наскільки надійні числа →](10-monte-carlo.md)
