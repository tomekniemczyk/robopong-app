# Session 2 — Newgy calibration & drill capture (2026-04-22 ~01:03 CEST)

## Setup
- Telefon: Huawei P10 (CMR-AL09), Android 9 / EMUI 9.1.0.343
- Robot MAC: `FC:0F:E7:6D:01:B9`
- Newgy package: `com.newgy.newgyapp`
- HCI snoop + logcat capture aktywny

## Sekwencja kalibracji w Newgy (live)
1. Connection made → calibration successful
2. Alignment głowicy — LED-y w pionie (step 1 "Done")
3. Height throw angle — pominięty (komunikat Newgy: "STOP! skip this step unless you see balls in the net or off the table")
4. Test throw — **piłki lądowały ~40-50 cm ZA końcem stołu** (overshoot)

## Obserwacja protokołowa
Default kalibracja Newgy daje **przerzut ~40-50 cm za stołem**.
User hipoteza: "kalibracja w oryginale opiera się na przyspieszeniu silnikami jako bazę żeby rzucić piłki dalej" — czyli Newgy ustawia wysoki baseline PWM silników, żeby każdy drill dodający speed zachował margin. Dla standardowego stołu to już overshoot.

Implikacje dla AcePad:
- Nasza default kalibracja (top=160, bot=0, h=183) może być zbyt agresywna tak samo
- Warto dodać **"soft default"** wariant kalibracji dla standardowego stołu gdzie baseline jest niższy
- Test: porównać landing z AcePad vs Newgy przy tych samych parametrach drilla
