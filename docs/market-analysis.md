# AcePad — Analiza rynku i USP

Data: 2026-04-02

## Rynek robotów pingpongowych

- **Wielkość**: $60-330M (2024), prognoza $140M-1.36B do 2032
- **CAGR**: 3-12%
- **Lider**: Azja-Pacyfik (Chiny, Japonia, Korea)

## Konkurenci

| Robot | Cena | App | Główny problem |
|---|---|---|---|
| Butterfly Amicus Prime | ~€2,179 | BT, tablet w zestawie | App crashuje, 2+ lat bez naprawy prostych bugów |
| Power Pong Omega | ~€2,079 | BT, najlepszy soft w kategorii | Brak community marketplace |
| Newgy/Donic 3050XL | ~€2,000 | BT, crash-prone | "Robot kontrolowany przez soft który nie działa" |
| Pongbot Nova S Pro | ~€349 | WiFi, community drills | WiFi wymaga hotspotu, brak mirror/scatter |
| PongFox | ~€400-600 | BT, wbudowana kamera | Mała społeczność |

## Największe bóle użytkowników

1. **Software jest tragiczny** — główny pain point WSZYSTKICH robotów
2. **Bluetooth się rozłącza** — Newgy wymaga restartu robota
3. **Preset drille nie działają** — piłki lecą w siatkę
4. **Brak edycji zapisanych drilli** — Newgy nie pozwala edytować
5. **Zero feedbacku o postępie** — "czy się poprawiam?"
6. **Trening z robotem jest samotny** — brak community

## USP AcePad — co ŻADNA konkurencja nie ma

| Funkcja | AcePad | Amicus | Power Pong | Newgy | Pongbot |
|---|---|---|---|---|---|
| Dni treningowe (program) | 30-Day z progresją | Brak | Brak | Brak | Brak |
| Ćwiczenia fizyczne w treningu | 16 ćwiczeń | Brak | Brak | Brak | Brak |
| Rozgrzewka zintegrowana | Chińska 4-fazowa | Brak | Brak | Brak | Brak |
| Drille + ćwiczenia w jednej sesji | Tak | Tylko drille | Tylko drille | Tylko drille | Tylko drille |
| Cool-down po treningu | Tak | Brak | Brak | Brak | Brak |
| Nagrywanie per krok | Każdy drill osobno | Brak | Brak | Brak | Brak |
| Kalibracja wizard | 3-fazowa z feedbackiem | Brak | Brak | Brak | Brak |
| Historia + powtórzenie kroku | Re-run z nagrywaniem | Brak | Brak | Brak | Brak |
| Progresja tygodniowa | Auto 85%→100% | Brak | Brak | Brak | Brak |
| Multi-język | 5 (PL/EN/DE/FR/ZH) | 1-2 | 1 | 1-2 | 1-2 |
| Stabilne BLE | Auto-reconnect | Crashuje | OK | Restart robota | WiFi |

**Podsumowanie**: Wszystkie konkurencyjne aplikacje to "pilot do robota z listą drilli". AcePad to jedyna aplikacja która traktuje sesję z robotem jako **pełny trening** (rozgrzewka → drille → cool-down → analiza).

## Cennik — rekomendacja

### Add-on AcePad (dla właścicieli 3050XL)
- BOM: ~600-900 PLN (RPi + kamera + obudowa + kable)
- **Cena: 2 000 PLN (~€460)** — marża ~60%
- Wartość: zamienia crashujący Newgy soft w profesjonalną platformę treningową z kamerą

### Bundle Robot + AcePad
- Robot: ~8 000-9 000 PLN
- AcePad: +2 000 PLN
- **Razem: ~10 000 PLN (~€2 300)** — konkurencyjne z Amicus/Power Pong ale lepszy soft + kamera

### Subscription (przyszłość)
| Tier | Cena/mies | Zawartość |
|---|---|---|
| Free | 0 | Sterowanie, kalibracja, basic drills |
| Pro | 30-50 PLN | Analytics, voice coaching, cloud, premium programy |
| Coach/Klub | 100-200 PLN | Multi-player, async coaching, dashboard |

## Rekomendowane nowe funkcje (priorytet)

### Wysoki wpływ
- Voice coaching w trakcie drilli (73% retencji)
- Gamifikacja: streaki + badges (+25% retencja)
- Session analytics dashboard ("Strava for robot training")
- Smart drill adaptation (robot dostosowuje trudność)
- Community drill library z oceną

### Średni wpływ
- Coach-student async mode
- Mirror/Scatter/Clone drilli
- 52-week progression program
- Dead-time trimming nagrań
- Pilot zdalny /remote
- Club dashboard (B2B)

### Długoterminowe (moat)
- AI detekcja lądowania piłki z kamery
- AI analiza techniki z wideo
- Integracja z Spinsight/smart sensors
- Predykcja lądowania piłki (z danych eksploracji)

## Źródła
- Recenzje: Megaspin, PingSunday, Expert Table Tennis, Racket Insight
- Fora: TableTennisDaily, MyTableTennis.NET, Reddit r/tabletennis
- Technologia: SpinCoach, Spinsight, Stupa Analytics, SwingVision
- Market reports: Market Research Intellect, OpenPR
- Open source: Sucima (github.com/oliverchang/sucima)
