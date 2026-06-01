# Карта коду

Покажчик по всіх файлах із кодом: які там функції/класи, для чого вони і в якій
**фазі** дослідження використовуються. Доповнює пофазовий наратив у [`docs/`](README.md):
тут — погляд «за модулями», а не «за історією».

**Архітектура одним реченням:** дані течуть `model → generation → engines (+aging) → metrics`,
а поверх спільного шару `experiments.py` сидять три споживачі тих самих чисел —
**тести** (інваріанти), **скрипти** (друк у консоль) і **figbuild** (графіки).

### Легенда фаз
| Фаза | Тема |
|---|---|
| 1 | Модель даних |
| 2 | Генерація пуассонівського потоку |
| 3 | Рушій симуляції: купа, aging, bucket, порогова ескалація |
| 4 | Запуск трьох сценаріїв (FIFO / Priority / Aging) |
| 5 | Метрики та аналіз |
| 6-7 | Візуалізація (графіки 1-5) |
| 8 | Валідація рушія теорією черг (M/G/1, M/M/c) |
| 9 | Монте-Карло (надійність чисел) |
| 10 | Чутливість до навантаження ρ |
| 11 | Метрика шкоди (CTAS-пороги) |
| 12 | Reneging / LWBS (вихід пацієнтів) |
| 13 | Динамічна тяжкість (погіршення + смерть) |

---

## 📦 Бібліотека `src/triage_sim/` — чиста логіка, без I/O

### `model.py` — модель даних і спільні константи · **Фаза 1**
- `Patient` (dataclass) — пацієнт: `id`, `arrival_time`, `severity`, `service_duration`, `start_time` + поля-розширення (`patience`, `leave_time`, `orig_severity`, `orig_duration`, `det_times`, `death_time`), які заповнюють моделі вибуття.
  - `wait_time` (property) — `start_time − arrival_time`.
- Константи: `SEVERITY_LEVELS`, `SEV_COLORS`, `SEV_NAMES`, `SEVERITY_PROBS`, `BASE_SERVICE`, `SERVICE_NOISE`, `MIN_SERVICE`, `DEFAULT_AGING_THRESHOLD`, `DISCIPLINES` — єдине джерело для всього проєкту.

### `generation.py` — пуассонівський потік пацієнтів · **Фаза 2**
- `sample_severities(rng, n)` — `n` тяжкостей із `SEVERITY_PROBS`.
- `sample_service_durations(rng, severities)` — час лікування (нормальний навколо `BASE_SERVICE`). **Спільне джерело розподілу** — ним же користується валідація.
- `generate_patients(n, arrival_rate, seed)` — повний потік (міжприбуття ~ експоненційні). Основа кожного прогону.

### `engines/drivers.py` — узагальнені драйвери симуляції · **Фаза 3** (база), **12-13** (вибуття)
- `QueuePolicy` (Protocol) — інтерфейс черги (`push`/`pop`/`__len__`).
- `run_single_server(patients, policy)` — єдиний цикл «один лікар + черга»; уся механіка часу — тут, незалежно від дисципліни.
- `run_with_departures(patients, sort_key, review)` — той самий цикл + хук `review` для моделей, де пацієнти вибувають (LWBS/смерть).

### `engines/policies.py` — політики черги + фабрики ключів · **Фаза 3**
- `heap_key(discipline)` — статичний ключ купи (`priority`/`fifo`).
- `HeapPolicy` — черга з пріоритетами на `heapq`.
- `FifoDequePolicy` — FIFO на `deque` за O(1) (доказ «дисципліна ≠ структура»).
- `discipline_sort_key(discipline, aging_threshold)` — динамічний ключ списку (`priority`/`fifo`/`aging`) для драйвера з вибуттям.

### `engines/__init__.py` — публічні рушії · **Фаза 3-4**, **8**
- `simulate(patients, discipline)` — один лікар, `fifo`/`priority` (головний рушій).
- `simulate_fifo_deque(patients)` — FIFO на deque (та сама дисципліна, інша структура).
- `simulate_md(patients, discipline, n_doctors)` — `c` лікарів (M/M/c); валідується Erlang-C.

### `aging/linear.py` — лінійний aging · **Фаза 3**
- `ListAgingPolicy` — наївний список із пересортуванням (прозорий еталон).
- `simulate_aging_list` / `simulate_aging_heap` — список O(n log n)/крок vs купа O(log n), той самий результат.
- `simulate_aging` — псевдонім купної версії (основний рушій aging).

### `aging/bucket.py` — bucket-черга · **Фаза 3**
- `BucketPolicy` / `simulate_bucket` — priority за O(1) (одне FIFO-відро на рівень).

### `aging/step.py` — нелінійна порогова ескалація · **Фаза 3**
- `escalated_level(patient, now, esc, floor)` — поточний ескальований рівень зі стелею безпеки `SAFETY_FLOOR`.
- `StepLazyHeap` / `simulate_step_aging` — порогове правило на купі з лінивим видаленням (O(log n) аморт.).
- `ListStepPolicy` / `simulate_step_aging_ref` — брутфорс-еталон (O(n)/крок) для звірки.

### `metrics.py` — метрики аналізу · **Фаза 5** і **11**
- `metrics_by_severity(served)` — `avg`/`max`/`count` очікування за рівнями (основа всіх таблиць і графіків). **Фаза 5**.
- `count_in_danger(served, danger)` + `DANGER` — скільки перевищили клінічний поріг (CTAS) — метрика шкоди. **Фаза 11**.

### `validation.py` — звірка рушія з теорією черг · **Фаза 8**
- `service_moments` — 1-й/2-й моменти часу обслуговування (зі спільних семплерів).
- `validate_mg1` — FIFO vs формула Pollaczek–Khinchine (M/G/1).
- `erlang_c` / `mmc_wq` — точний розв'язок M/M/c.
- `gen_exponential` — тестовий потік з експоненційним лікуванням.
- `validate_mmc` — `simulate_md` vs Erlang-C.

### `experiments.py` — спільні Монте-Карло-експерименти · **Фази 9-13**
> Шар «бібліотека рахує → скрипти друкують, figbuild малює». Усуває дубль петель між `run_*.py` і `figbuild/data.py`.
- `_three_metrics(patients, aging_threshold)` *(приватний)* — метрики 3 дисциплін на копіях одного набору.
- `monte_carlo(runs, …)` — N прогонів + опорна точка `s42`. **Фаза 9**.
- `load_sweep(seeds_per_rho, …)` — sweep по навантаженню ρ. **Фаза 10**.
- `reneging_stats(runs, …)` — LWBS загалом і за рівнями. **Фаза 12**.
- `reneging_valve(runs, …)` — ефект «клапана» (max очікування L5). **Фаза 12**.
- `deterioration_stats(runs, …)` — наївна + реалістична смертність. **Фаза 13**.
- `deterioration_sensitivity(runs, rates, …)` — чутливість смертності до темпу. **Фаза 13**.

### `reneging.py` — відхід пацієнтів (LWBS) · **Фаза 12**
- `_sample_patience(rng, mean)` *(приватний)* — поріг терпіння (спільна формула).
- `assign_patience(patients, seed)` — присвоїти кожному терпіння (L1 = ∞).
- `simulate_reneging(patients, discipline, aging_threshold)` → `(served, reneged)`; внутр. `review` відсіює тих, хто пішов.

### `deterioration.py` — динамічна тяжкість · **Фаза 13**
- `_rate_for`, `_assign_schedule`, `_current_severity`, `_deteriorate` *(приватні)* — темп/розклад погіршення та оновлення стану.
- `assign_deterioration` / `assign_det_rate` — розклад падіння тяжкості (стандартний / налаштовуваний темп).
- `assign_patience_det` — терпіння за **початковою** тяжкістю.
- `simulate_deterioration` → `(served, died)` — погіршення + смерть (без виходу).
- `simulate_deter_reneg` → `(served, died, left)` — повна модель (+ вихід легких).

### `heap_demo.py` — навчальна купа й візуалізація · **Фаза 3-4** (діаграми)
- `MyHeap` — купа «з нуля» (sift-up/sift-down вручну), доводить O(log n).
- `sift_up_steps` / `sift_down_steps` — кадри для анімації push/pop (графіки 05-06).
- `draw_heap(ax, …)` — малює купу як бінарне дерево (графік 04).

---

## ⚙️ Скрипти `scripts/` — лише друк у консоль

- **`_bootstrap.py`** — додає `../src` у `sys.path` (запуск без встановлення пакета).
- **`_common.py`** — `served_by_discipline` (FIFO/Priority/Aging на копіях одного набору) для `run_main_comparison`. **Фази 4-5**.
- **`run_main_comparison.py`** `main` — головна таблиця FIFO/Priority/Aging (seed=42) + звірка «дисципліна ≠ структура». **Фази 4-6**.
- **`run_monte_carlo.py`** `main`(+`summary`) — друк `monte_carlo`. **Фаза 9**.
- **`run_load_sweep.py`** `main` — друк `load_sweep`. **Фаза 10**.
- **`run_validation.py`** `main` — друк `validate_mg1`/`validate_mmc`. **Фаза 8**.
- **`run_reneging.py`** `main` — друк `reneging_stats` + `reneging_valve`. **Фаза 12**.
- **`run_deterioration.py`** `print_naive`/`print_realistic`/`print_sensitivity`/`main` — друк `deterioration_stats` + `deterioration_sensitivity`. **Фаза 13**.
- **`save_figures.py`** `main` — CLI: будує всі 23 графіки у `figures/` (`--only`, `--runs`, `--out`).

---

## 🖼️ Пакет графіків `scripts/figbuild/`

- **`constants.py`** — `DISC_COLOR`/`DISC_LABEL`/`DISCS`/`AGING_THR` (без matplotlib).
- **`helpers.py`** — спільні плот-утиліти: `save_fig`, `severity_legend`, `label_bars`, `bar_centers`, `grouped_level_bars`, `style_boxplot`, `queue_box`, `timeline_panel`; єдине місце налаштування бекенда matplotlib.
- **`data.py`** `Data` — лінива підготовка даних: `seed42`/`throughput`/`harm` (реальна логіка, суто-графічна), а `monte`/`sweep`/`reneging`/`deter` — тонкі обгортки над `experiments.py`.
- **`flow.py`** — графіки 01-03 (прибуття, проміжки, тяжкість). **Фаза 2**.
- **`structure.py`** — 04-08 (купа, sift-up/down, крива aging, поріг). **Фаза 3**.
- **`comparison.py`** — 09-14 (середнє/макс очікування, таймлайни, голодування, violin, throughput). **Фази 5-7**.
- **`queue_trace.py`** — 15-16 (черга наживо) + `_trace_priority`. **Бонус**.
- **`robustness.py`** — 17-19 (Монте-Карло boxplots, seed42 vs розподіл, навантаження). **Фази 9-10**.
- **`outcomes.py`** — 20-23 (harm-чутливість, harm за дисципліною, LWBS, смертність). **Фази 11-13**.

> Імена функцій графіків самодокументовані: `fig_<опис>_NN`, напр. `fig_avg_wait_by_severity_09`.

---

## ✅ Тести `tests/`

- **`test_equivalence.py`** (14) — біт-у-біт еквівалентність усіх реалізацій рушія + поведінкові гарантії (aging обмежує L5, `SAFETY_FLOOR`) + валідація теорії черг. **Фази 3, 5, 8**.
- **`test_departures.py`** (6) — інваріанти моделей вибуття (збереження пацієнтів, L1 не йде, монотонність тяжкості). **Фази 12-13**.
- **`test_metrics.py`** (3) — `metrics_by_severity` + `count_in_danger` (строга межа порога). **Фази 5, 11**.
- **`test_experiments.py`** (7) — контракти спільних експериментів. **Фази 9-13**.
