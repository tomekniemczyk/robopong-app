# Analiza logów Newgy — porównanie z AcePad

**Data sesji:** 2026-04-22, Huawei P10 (CMR-AL09), robot MAC `FC:0F:E7:6D:01:B9`

---

## Sekwencja Newgy przy połączeniu

Z `session1_initial/logcat_full.txt` i `re/ANDROID_APP_RE.md`:

```
1. Z×3 + H + F + I + J02        ← handshake (standardowy)
2. [brak U/O/R po connect]       ← Newgy liczyła na firmware persistence
                                    (3050XL NIE persystuje po power-cycle!)
```

## Sekwencja Newgy przy wejściu w kalibrację

```
1. V          ← BeginCalibration (raz, choć protokół mówi 2×)
2. B z wartościami:
   Gen2: top=161 (73%), bot=0, h=183 (80%), osc=150 (50%), rot=150 (0°)
   wait=1000ms
   Firmware po V: U=150 (neutral) → effective_h = 183 + (150−150) = 183 ✓
3. Użytkownik reguluje top_speed (±1) i osc (±4), robi rzuty (T)
4. Po zakończeniu (CalibrationPage.complete):
   a. height −= 30%  → h = 80% − 30% = 50% = raw 150
   b. SetSpeedCAL: Q{top_raw − 161}  (tylko jeśli > 0)
   c. SetBall z zerową prędkością (B z top=0, bot=0)
   d. Task.Delay(500)
   e. AdjustOscillation → O{osc_raw}   (OscCAL = raw − 150)
   f. FinishCalibration: H + W000
```

**Uwaga:** CalibrationPage (Android, uproszczona) nie wysyła U ani R.
ControlCallibrate (pełna kalibracja) wysyła U i R po zakończeniu:
```
   AdjustHeight → U{h_raw_after_minus30}   (HeightCAL = raw − 150)
   AdjustRotation → R{rot_raw}             (RotCAL = raw − 150)
   AdjustOscillation → O{osc_raw}          (OscCAL = raw − 150)
```

---

## Bug w AcePad (naprawiony 2026-04-23)

### Problem

Przed naprawą `begin_calibration` wywoływał `_apply_calibration_with_reset(cal)`,
co po V×2 przywracało U/O/R z poprzedniej kalibracji:

```
V×2  →  U=183 (z DEFAULT_CAL lub saved cal)
                          +
set_ball wizard z h=183  →  B command h=183
                          =
effective_h = 183 + (183 − 150) = 216  ← POZA ZAKRESEM (max=210)!
```

Efekt: głowica biła w górny stop, piłki leciały za wysoko lub robot zgłaszał błąd.

### Dlaczego Newgy tego unika

Newgy po V nie wysyła U/O/R — V resetuje firmware do U=O=R=150 (neutral).
Kalibracyjny set_ball z h=183 → effective = 183 ✓.
U/O/R są wysyłane DOPIERO po zakończeniu kalibracji.

### Naprawka

`begin_calibration` wysyła tylko V×2. Nie wywołuje `apply_calibration`.
U/O/R są przywracane po commitcie kalibracji (`apply_calibration` / `commit_calibration`).

---

## Kalibracyjne wartości domyślne (gen. dla całego projektu)

| Parametr | Wartość raw | Wartość % | Źródło |
|----------|------------|-----------|--------|
| top_speed | 161 | 73% | Gen2 (SecondRun) |
| bot_speed | 0   | 0%  | Gen2 |
| height    | 183 | 80% | Gen2 |
| oscillation | 150 | 50% | centrum (praworęczni) |
| rotation  | 150 | 0°  | prosto |
| wait_ms   | 1000 | — | Gen2 |

Formuły konwersji:
- height raw = 75 + 135 × (pct / 100)
- top_speed raw = 28 + 182 × (pct / 100)
- oscillation raw: 173=0% (prawo), 127=100% (lewo), 150=50% (środek)
- rotation raw: 150=0°, 90=−90°(lewo), 210=+90°(prawo)

---

## Obserwacje z live testu (2026-04-22)

- Newgy domyślna kalibracja rzuca ~40–50 cm ZA stół — celowe (baseline wysoki,
  drille mogą dodać prędkość i mają margines)
- Nasz DEFAULT_CAL (top=161, h=183) jest identyczny z Newgy Gen2 defaults
- Step kalibracji wysokości w Newgy pomijany domyślnie ("skip unless balls in net")
- BLE cache bug Newgy: pierwsze ~10–15 prób connect → `findMldpGattService found no MLDP service`
  → retry co 2s aż cache się odświeży

---

## Pliki w tym katalogu

```
newgy-capture/
├── ANALYSIS.md                          ← ten plik
├── logcat_full.txt                      ← logcat Android z session2 (calibration + drill)
├── session1_initial/
│   ├── logcat_full.txt                  ← logcat Android z session1 (pierwsze połączenia)
│   ├── btsnoop_hci.log                  ← surowy HCI snoop (binarny, z Android developer options)
│   ├── btsnoop_hci_decoded.log          ← częściowo zdekodowany HCI
│   ├── btsnoop_base64.txt               ← btsnoop zakodowany base64
│   ├── btsnooz_raw.bin                  ← btsnooz bin
│   ├── btsnooz.py                       ← skrypt dekodujący btsnooz
│   └── bugreport-CMR-AL09-*.txt/.zip   ← pełny Android bugreport (źródło HCI + logcat)
└── session2_notes.md                    ← notatki z session2
```
