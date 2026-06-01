# Варіанти структури черги: bucket, лінива купа, aging на купі

> Розділ 05b · [↑ Зміст документації](README.md) · [↑ Головний README](../README.md)

[← Aging: третя дисципліна](05-aging.md)    [Фази 4–5. Запуск, метрики та головний результат →](06-metrics-and-results.md)

---

У розділі 05 aging реалізовано через список із пересортуванням. Тут показано три варіанти структури для тієї самої (і спорідненої) задачі: як покласти лінійний aging на купу за O(log n), як для кількох дискретних рівнів отримати O(1) через bucket-чергу, і як обробити нелінійне правило купою з лінивим видаленням. Наприкінці купну версію aging робимо основним рушієм для подальших фаз.

### Aging на купі: чому список не обов'язковий

Той списковий рушій пересортовував чергу щокроку, бо ефективний пріоритет `eff(p) = severity − (зараз − прибуття)/T` нібито змінюється щомиті. Але придивімося до **порівняння** двох пацієнтів. Розкриємо дужки:

`eff(p) = (severity + прибуття/T) − зараз/T`

Член `− зараз/T` **однаковий для всіх** пацієнтів у черзі цієї миті, тож при порівнянні p і q він скорочується:

`eff(p) − eff(q) = (severity_p + прибуття_p/T) − (severity_q + прибуття_q/T)`

Час зник. Отже відносний порядок **не залежить** від поточного моменту — його задає **статичний** ключ `severity + прибуття/T`. Старіння змінює абсолютні значення пріоритету, але не те, хто кого випереджає.

Висновок: для лінійного aging це той самий heap, лише з іншим ключем — O(log n) на операцію. Списковий варіант із пересортуванням щокроку дає **той самий результат**, але коштує O(n log n) на крок. Нижче перевіримо рівність біт-у-біт і виміряємо різницю.

```python
def simulate_aging_heap(patients, aging_threshold=45):
    """Лінійний aging на КУПІ за O(log n). Статичний ключ severity + arrival/T:
    член '−зараз/T' однаковий для всіх і скорочується при порівнянні,
    тож відносний порядок не залежить від часу — купа підходить."""
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0; waiting = []; now = 0.0; counter = 0; served = []
    while i < len(arrivals) or waiting:
        while i < len(arrivals) and arrivals[i].arrival_time <= now:
            patient = arrivals[i]
            key = (patient.severity + patient.arrival_time / aging_threshold, patient.arrival_time, counter)
            heapq.heappush(waiting, (key, patient)); counter += 1; i += 1
        if not waiting:
            now = arrivals[i].arrival_time; continue
        _, patient = heapq.heappop(waiting)
        patient.start_time = now; now += patient.service_duration; served.append(patient)
    return served

print("simulate_aging_heap готова")
```

> **Примітка щодо реалізації.** У пакеті `simulate_aging_heap` не дублює цикл, а використовує спільний драйвер: `run_single_server(patients, HeapPolicy(lambda patient: (patient.severity + patient.arrival_time/T, patient.arrival_time)))`. Тобто aging — це та сама купа, що й priority, лише з іншим ключем. Списковий варіант, bucket-черга та порогова ескалація реалізовані як інші **політики** над тим самим драйвером (див. `src/triage_sim/aging/` і `engines/`).


**Результат:**

```
simulate_aging_heap готова
```

```python
ok = True
for s in range(50):
    a = simulate_aging(copy.deepcopy(generate_patients(seed=s)), 45)        # список (еталон)
    b = simulate_aging_heap(copy.deepcopy(generate_patients(seed=s)), 45)   # купа
    if [patient.id for patient in a] != [patient.id for patient in b]: ok = False
    if any(abs(x.wait_time - y.wait_time) > 1e-9 for x, y in zip(a, b)): ok = False
print("simulate_aging_heap == simulate_aging на 50 seed:", "так, біт у біт" if ok else "ні")
```


**Результат:**

```
simulate_aging_heap == simulate_aging на 50 seed: так, біт у біт
```

```python
import time
print(f"{'n':>6} | {'список (пересорт)':>18} | {'купа O(log n)':>15}")
for n in (2000, 8000):
    pts = generate_patients(n=n, arrival_rate=0.30, seed=1)   # завал: черга росте
    t0 = time.perf_counter(); simulate_aging(copy.deepcopy(pts), 45);      tl = (time.perf_counter()-t0)*1000
    t0 = time.perf_counter(); simulate_aging_heap(copy.deepcopy(pts), 45); th = (time.perf_counter()-t0)*1000
    print(f"{n:>6} | {tl:>15.0f} мс | {th:>12.1f} мс  ({tl/th:.0f}x)")
```


**Результат:**

```
     n |  список (пересорт) |   купа O(log n)
  2000 |             213 мс |         14.1 мс  (15x)
  8000 |            4744 мс |         59.8 мс  (79x)
```

> Час — **орієнтовний** (один прогін, залежить від машини): відтворюваний тут не точний мс чи ×, а **порядок** — список у тисячах мс проти десятків у купи, і зростання розриву з n.

## Bucket-черга: O(1) для дискретних рівнів

Купа дає O(log n). Але коли пріоритет — це лише кілька **цілих** рівнів (5 рівнів ESI/CTAS), сортувати взагалі не потрібно. Тримаємо по одній FIFO-черзі («скриньці») на кожен рівень:

- `push` кидає пацієнта у скриньку його рівня — O(1);
- `pop` бере переднього з першої непорожньої скриньки — теж O(1), бо кількість рівнів фіксована (перебір 5 скриньок — стала, не залежить від n).

Це реалізує **ту саму** дисципліну priority, що й купа (найтяжчий першим, серед рівних — за чергою прибуття), але без log n. Перевіримо, що результат збігається з купою біт-у-біт.

```python
from collections import deque

def simulate_bucket(patients, levels=5):
    """Priority через bucket-чергу: одне FIFO-відро на рівень. push/pop = O(1)."""
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0
    buckets = [deque() for _ in range(levels + 1)]   # індекс = severity (1..levels)
    n = 0; now = 0.0; served = []
    while i < len(arrivals) or n:
        while i < len(arrivals) and arrivals[i].arrival_time <= now:
            buckets[arrivals[i].severity].append(arrivals[i]); n += 1; i += 1   # push O(1)
        if not n:
            now = arrivals[i].arrival_time; continue
        for sev in range(1, len(buckets)):                                      # pop O(1)
            if buckets[sev]:
                patient = buckets[sev].popleft(); n -= 1; break
        patient.start_time = now; now += patient.service_duration; served.append(patient)
    return served

print("simulate_bucket готова")
```


**Результат:**

```
simulate_bucket готова
```

```python
ok = all([patient.id for patient in simulate_bucket(copy.deepcopy(generate_patients(seed=s)))]
         == [patient.id for patient in simulate(copy.deepcopy(generate_patients(seed=s)), 'priority')]
         for s in range(30))
print("simulate_bucket == simulate(priority) на 30 seed:", "так, біт у біт" if ok else "ні")
```


**Результат:**

```
simulate_bucket == simulate(priority) на 30 seed: так, біт у біт
```

Тепер виміряємо сам виграш. Беремо priority через купу (`simulate(..., 'priority')`) і через bucket (`simulate_bucket`) на дедалі більших потоках із завалом (`arrival_rate=0.30`, щоб черга справді росла), а копії робимо **наперед, поза заміром** — щоб міряти структуру, а не `deepcopy`.

```python
import time
print(f"{'n':>7} | {'купа O(log n)':>15} | {'bucket O(1)':>13}")
for n in (5000, 20000, 80000):
    pts = generate_patients(n=n, arrival_rate=0.30, seed=1)   # завал: черга росте
    heap_copy, bucket_copy = copy.deepcopy(pts), copy.deepcopy(pts)   # копії наперед, поза заміром
    t0 = time.perf_counter(); simulate(heap_copy, 'priority'); th = (time.perf_counter()-t0)*1000
    t0 = time.perf_counter(); simulate_bucket(bucket_copy);    tb = (time.perf_counter()-t0)*1000
    print(f"{n:>7} | {th:>12.1f} мс | {tb:>10.1f} мс  ({th/tb:.2f}x)")
```


**Результат:**

```
      n |   купа O(log n) |   bucket O(1)
   5000 |          6.9 мс |        3.7 мс  (1.85x)
  20000 |         37.3 мс |       18.8 мс  (1.98x)
  80000 |        262.4 мс |       80.7 мс  (3.25x)
```

Bucket стабільно швидший, і **перевага зростає з n** (≈1.8× → 3.2×): купа платить O(log n) на операцію — що глибша черга, то більше порівнянь, — а bucket робить сталий O(1) (push у скриньку + перебір 5 скриньок) незалежно від розміру черги. На 180 пацієнтах різниця неважлива, але механіку видно: для **малої дискретної** шкали пріоритетів відрова черга обганяє навіть C-реалізацію `heapq`.

> Час — **орієнтовний** (машинозалежний, один прогін): стабільні тут **магнітуди й тренд** (bucket швидший, × росте з n), а не точні мілісекунди чи конкретний коефіцієнт.

## Нелінійне правило та купа з лінивим видаленням

А якщо правило старіння нелінійне? Наприклад, **порогова ескалація зі стелею безпеки**: чекав понад 30 хв → +1 рівень терміновості, понад 60 хв → +2, але **ніколи вище рівня 2** — щоб ескальований легкий пацієнт ніколи не випередив справжнього критичного (L1). Це клінічно осмислено й виражає компроміс, недосяжний лінійним aging.

Чому статичний ключ тут **не** працює. При лінійному aging член «−зараз/T» скорочувався при порівнянні, тож порядок не залежав від часу. При нелінійному правилі ескалація стрибкоподібна, і відносний порядок пацієнтів **змінюється з часом** — статичний ключ більше не годиться.

Але ключ міняється лише в **дискретні моменти** — коли пацієнт перетинає поріг очікування (30 і 60 хв). Це ідеальний випадок для **купи з лінивим видаленням (lazy deletion)**:

1. при перетині порога кладемо в купу **новий** запис із оновленим ключем;
2. старий запис лишаємо «протухати»;
3. при вийманні **пропускаємо протухлі** записи (для кожного пацієнта пам'ятаємо, який запис актуальний — за `id`).

Кожен пацієнт перевставляється не більше ніж (кількість порогів + 1) разів, тож складність лишається O(log n) амортизовано. Перевіримо коректність брутфорсом (перерахунок щокроку) і подивимося, що дає це правило.

```python
ESCALATION   = ((30, 1), (60, 2))   # >30 хв: +1 рівень; >60 хв: +2
SAFETY_FLOOR = 2                    # ескальований легкий не дотягнеться до L1

def escalated_level(patient, now, esc=ESCALATION, floor=SAFETY_FLOOR):
    """Поточний (ескальований) рівень: тяжчає з очікуванням, але не нижче floor
    і не легше за початковий рівень."""
    waited = now - patient.arrival_time
    bump = max((bump for thr, bump in esc if waited >= thr), default=0)
    return min(patient.severity, max(floor, patient.severity - bump))

class StepLazyHeap:
    """Нелінійне (порогове) правило на купі з лінивим видаленням."""
    def __init__(self, esc=ESCALATION, floor=SAFETY_FLOOR):
        self.esc = esc; self.floor = floor
        self._h = []; self._cross = []; self._live = {}; self._seq = 0; self._cseq = 0
    def _key(self, patient, bump):
        return (min(patient.severity, max(self.floor, patient.severity - bump)), patient.arrival_time)
    def push(self, patient):
        heapq.heappush(self._h, (self._key(patient, 0), self._seq, patient))
        self._live[patient.id] = self._seq; self._seq += 1
        for thr, bump in self.esc:                                # розклад перетинів порогів
            heapq.heappush(self._cross, (patient.arrival_time + thr, self._cseq, bump, patient)); self._cseq += 1
    def pop(self, now):
        while self._cross and self._cross[0][0] <= now:           # застосувати перетини до 'now'
            crossing_time, _, bump, patient = heapq.heappop(self._cross)
            if patient.id in self._live:                                # ще чекає → новий запис, старий протухне
                heapq.heappush(self._h, (self._key(patient, bump), self._seq, patient)); self._live[patient.id] = self._seq; self._seq += 1
        while True:                                               # виймаємо, пропускаючи протухлі
            key, seq, patient = heapq.heappop(self._h)
            if self._live.get(patient.id) == seq:
                del self._live[patient.id]; return patient
    def __len__(self): return len(self._live)

print("StepLazyHeap готова")
```


**Результат:**

```
StepLazyHeap готова
```

```python
def simulate_step_aging(patients, esc=ESCALATION, floor=SAFETY_FLOOR):
    """Порогова ескалація на купі з лінивим видаленням — O(log n) амортизовано."""
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0; queue = StepLazyHeap(esc, floor); now = 0.0; served = []
    while i < len(arrivals) or len(queue):
        while i < len(arrivals) and arrivals[i].arrival_time <= now:
            queue.push(arrivals[i]); i += 1
        if not len(queue):
            now = arrivals[i].arrival_time; continue
        patient = queue.pop(now)
        patient.start_time = now; now += patient.service_duration; served.append(patient)
    return served

def simulate_step_aging_ref(patients, esc=ESCALATION, floor=SAFETY_FLOOR):
    """Брутфорс-еталон: щокроку перебираємо всіх за ПОТОЧНИМ ескальованим рівнем (O(n) на крок)."""
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0; waiting = []; now = 0.0; served = []
    while i < len(arrivals) or waiting:
        while i < len(arrivals) and arrivals[i].arrival_time <= now:
            waiting.append(arrivals[i]); i += 1
        if not waiting:
            now = arrivals[i].arrival_time; continue
        patient = min(waiting, key=lambda candidate: (escalated_level(candidate, now, esc, floor), candidate.arrival_time))
        waiting.remove(patient)
        patient.start_time = now; now += patient.service_duration; served.append(patient)
    return served

print("simulate_step_aging + еталон готові")
```


**Результат:**

```
simulate_step_aging + еталон готові
```

```python
# 1) коректність: купа з лінивим видаленням == брутфорс
ok = all([p.id for p in simulate_step_aging(copy.deepcopy(generate_patients(n=300, seed=s)))]
         == [p.id for p in simulate_step_aging_ref(copy.deepcopy(generate_patients(n=300, seed=s)))]
         for s in range(30))
print("simulate_step_aging == брутфорс на 30 seed:", "так, біт у біт" if ok else "ні")

# 2) що дає це правило проти чистого priority і лінійного aging (трохи завищене навантаження)
A = {'p': [], 'a': [], 's': []}; A5 = {'p': [], 'a': [], 's': []}
for seed in range(200):
    pp = generate_patients(n=180, arrival_rate=0.09, seed=seed)
    mp = metrics_by_severity(simulate(copy.deepcopy(pp), 'priority'))
    ma = metrics_by_severity(simulate_aging_heap(copy.deepcopy(pp)))
    ms = metrics_by_severity(simulate_step_aging(copy.deepcopy(pp)))
    if not all(1 in d and 5 in d for d in (mp, ma, ms)): continue
    A['p'].append(mp[1]['avg']); A['a'].append(ma[1]['avg']); A['s'].append(ms[1]['avg'])
    A5['p'].append(mp[5]['max']); A5['a'].append(ma[5]['max']); A5['s'].append(ms[5]['max'])

print(f"\n{'дисципліна':<26}{'L1 крит.(avg)':>14}{'L5 легкі(max)':>15}")
for k, l in [('p', 'чистий priority'), ('a', 'лінійний aging'), ('s', 'порогова ескалація+стеля')]:
    print(f"{l:<26}{np.mean(A[k]):>11.1f} хв{np.mean(A5[k]):>12.0f} хв")
```


**Результат:**

```
simulate_step_aging == брутфорс на 30 seed: так, біт у біт

дисципліна                 L1 крит.(avg)  L5 легкі(max)
чистий priority                   7.7 хв        1072 хв
лінійний aging                   32.3 хв         287 хв
порогова ескалація+стеля          7.5 хв         942 хв
```

### Що це додає

Дві структури показують, що вибір реалізації пріоритетної черги залежить від форми правила:

- **Bucket-черга** — для кількох дискретних рівнів дає O(1) замість O(log n), і це **та сама** дисципліна priority (звірено біт-у-біт).
- **Купа з лінивим видаленням** — для **нелінійних** правил, де порядок змінюється з часом і статичний ключ уже не годиться. Перевставлення лише в моменти перетину порогів тримає O(log n) амортизовано (звірено з брутфорсом біт-у-біт).

Порівняльна таблиця показує два **різні** компроміси:
- **лінійний aging** рятує легких, жертвуючи критичними (L1 росте до ~32 хв);
- **порогова ескалація зі стелею** навпаки — захищає критичних абсолютно (L1 ~7 хв, як у чистого priority), але легким дає лише обмежене полегшення (стеля безпеки не дає їм випередити справжні L1).

Тобто це не «краще/гірше», а **інша політика**: кого саме захищати в першу чергу. Числа ілюстративні — цінність у тому, як структура й правило формують поведінку системи.

```python
# --- Робимо купну версію ОСНОВНИМ рушієм aging ---
# Вище доведено: купна версія дає ТІ САМІ результати, що список,
# але працює за O(log n). Тож відтепер увесь основний аналіз
# (Фаза 4 і далі) рахує aging на купі. Наївний список лишаємо як еталон.
simulate_aging_list = simulate_aging        # зберігаємо наївний список під цією назвою
simulate_aging      = simulate_aging_heap   # головний рушій aging — тепер купа

print("simulate_aging → купна версія (O(log n)); наївний список доступний як simulate_aging_list")
```


**Результат:**

```
simulate_aging → купна версія (O(log n)); наївний список доступний як simulate_aging_list
```

---

[← Aging: третя дисципліна](05-aging.md)    [Фази 4–5. Запуск, метрики та головний результат →](06-metrics-and-results.md)
