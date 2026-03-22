# Reverse Engineering — Aplikacja Windows Newgy Robopong 3050XL

Źródło: zdekompilowany kod C# z MSI `WindowsApp_3050XL.msi`, trzy assemblies:
- `Newgy.Robots.RoboPong3050.Business.dll` — logika biznesowa (współdzielona z Android)
- `Newgy.Robots.Business.Windows.dll` — warstwa platformowa Windows
- `Newgy.Robots.RoboPong3050.Windows.WPF.exe` — aplikacja WPF

Data kompilacji MSI (z cabinet): 2020-03-21

---

## Sekcja 1: Architektura

### Framework UI

**WPF (Windows Presentation Foundation)** — klasy dziedziczą po `System.Windows.Window`, XAML
ładowane przez `Application.LoadComponent(uri)`. Nie jest to MAUI ani WinForms.

Aplikacja używa **Autofac** jako IoC container (DI framework).

### Diagram warstw

```
┌────────────────────────────────────────────────────────────┐
│                     UI (WPF)                               │
│  MainWindow, MainInterfaceWindow, CalibrationWindow,       │
│  ConnectWindow, AdvancedInterfaceWindow, StandardModeWindow│
│  TrainingWindow, RunDrillWindow, DrillLibraryWindow,       │
│  HeightCalibrationWindow, RotationCalibrationWindow        │
└────────────────────────┬───────────────────────────────────┘
                         │ IRobotService
┌────────────────────────▼───────────────────────────────────┐
│              Business Logic (współdzielona z Android)      │
│  BaseRobotService — setBall, runDrill, ThrowBall,          │
│  FillRobot, SetSpeedCAL, kalibracja, konwersja piłek       │
│                                                            │
│  BallFactory → AdvancedBallConverter / InterfaceBallConverter│
│               / RandomBallConverter                        │
└────────────────────────┬───────────────────────────────────┘
                         │ IRobotInterface
┌────────────────────────▼───────────────────────────────────┐
│              Windows Platform Layer                        │
│  RobotInterface (FTD2XX — FTDI USB)                       │
│  ConfigurationService — plik XML w %LocalAppData%         │
│  RobotService — drille w plikach XML w %MyDocuments%      │
└────────────────────────┬───────────────────────────────────┘
                         │ FTD2XX_NET.dll
┌────────────────────────▼───────────────────────────────────┐
│                   Robot Robopong 3050XL                     │
│           USB (FTDI chip, opis urządzenia "NEWGY3050")     │
└────────────────────────────────────────────────────────────┘
```

### Klasy specyficzne dla Windows

| Klasa | Assembly | Odpowiedzialność |
|-------|----------|-----------------|
| `RobotInterface` | Business.Windows | FTDI USB: łączenie, wysyłanie komend, odczyt odpowiedzi |
| `RobotService` | Business.Windows | Zarządzanie drillami (pliki XML), implementacja Windows-only metod |
| `ConfigurationService` | Business.Windows | Konfiguracja w XML (`%LocalAppData%\Newgy3050\Configuration.xml`) |
| `RobotInterfaceModule` | Business.Windows | Autofac: rejestracja `RobotInterface` jako singleton |
| `RobotServiceModule` | Business.Windows | Autofac: rejestracja `RobotService` |

### Klasy WPF (okna)

| Okno | Odpowiedzialność |
|------|-----------------|
| `ConnectWindow` | Połączenie z robotem; max 20 prób; po sukcesie otwiera `RobotHomeWindow` |
| `MainInterfaceWindow` | Główny interfejs z tabelą, tryb standardowy, przyciski |
| `CalibrationWindow` | Kalibracja prędkości (Up/Down = TopMotorSpeed ±1, Left/Right = Oscillation ±2) |
| `HeightCalibrationWindow` | Kalibracja wysokości |
| `RotationCalibrationWindow` | Kalibracja rotacji |
| `AdvancedInterfaceWindow` | Tryb zaawansowany z listą `AdvancedBall` |
| `StandardModeWindow` | Tryb standardowy (BallType + pozycja na stole) |
| `TrainingWindow` | Treningi predefiniowane |
| `RunDrillWindow` | Widok uruchomionego drilla |
| `DrillLibraryWindow` | Biblioteka drilli |

### Porównanie z architekturą Android

| Aspekt | Android | Windows |
|--------|---------|---------|
| Framework UI | Xamarin.Forms | WPF |
| DI container | Autofac (ten sam) | Autofac (ten sam) |
| Warstwa platformowa | `Newgy.Robots.Business.Android.dll` | `Newgy.Robots.Business.Windows.dll` |
| Logika biznesowa | `Newgy.Robots.RoboPong3050.Business.dll` | **identyczna** DLL |
| Konwertery piłek | AdvancedBallConverter, InterfaceBallConverter, RandomBallConverter | **identyczne** |

---

## Sekcja 2: Model danych piłki

### AdvancedInterfaceBall — identyczny z Android

| Pole | Typ | Zakres (UI) | Znaczenie |
|------|-----|------------|-----------|
| `TopMotorSpeed` | int | -100..100 | Prędkość górnego silnika (%) — ujemna = odwrotny kierunek |
| `BottomMotorSpeed` | int | -100..100 | Prędkość dolnego silnika (%) |
| `HeadPosition.Height` | int | 0..100 | Wysokość głowicy (%) |
| `HeadPosition.Oscillation` | int | 0..100 | Oscylacja/kierunek poziomy (%) |
| `HeadPosition.Rotation` | int | -90..90 | Obrót głowicy w stopniach |
| `WaitTime` | int | ms | Czas oczekiwania |
| `NumberOfBalls` | int | 1..N | Ile razy wysłać w drilla |
| `BallNumber` | int | — | Numer porządkowy |
| `TableYPercent` | double | 0.0..1.0 | Procent stołu w osi Y (opcjonalne) |

Serializacja XML (identyczna z Android):
```xml
<Ball Type="AdvancedInterfaceBall">
  <BallNumber>1</BallNumber>
  <NumberOfBalls>1</NumberOfBalls>
  <WaitTime>1000</WaitTime>
  <TopMotorSpeed>50</TopMotorSpeed>
  <BottomMotorSpeed>30</BottomMotorSpeed>
  <Height>60</Height>
  <Oscillation>50</Oscillation>
  <Rotation>0</Rotation>
</Ball>
```

### Enumy (identyczne z Android)

```
enum BallType    { TopSpin, TopSpinServe, BackSpin, BackSpinServe, NoSpin }
enum SpinSpeed   { Lowest, Lower, Low, Middle, High, Higher, Highest }
enum Rotation    { None, Left, Right }
enum RotationDegrees { None, Fifteen, Thirty, FortyFive, Sixty, SeventyFive, Ninety }
```

### Walidacja drilla

Każda piłka musi mieć `TopMotorSpeed + BottomMotorSpeed >= 10`. Komunikat błędu po angielsku:
> "Every ball in the drill must have a minimum total motor speed of at least 10 (Top + Bottom)."

---

## Sekcja 3: Formuły konwersji

**Identyczne z Android** — ta sama klasa `AdvancedBallConverter` w tej samej DLL.

### getMotorSpeed(motorPercent, min=28, max=210)

```csharp
if (motorPercent == 0) return 0;
if (motorPercent < 0)  return (int)(210 * (motorPercent / 100.0));  // wartość ujemna
return (int)(28 + (210 - 28) * (motorPercent / 100.0));             // 28..210
```

Zakresy: min=28, max=210 — **identyczne z Android**.

### getRobotHeightFromAdvancedBall(h%)

```
robotHeight = 75 + (int)(135 * h / 100)
```
Zakres: 75..210

### getRobotOscillationFromAdvancedBall(osc%, leftHanded)

```
adjusted = leftHanded ? (100 - osc) : osc
robotOscillation = 173 - (int)(53 * adjusted / 100)
```
Zakres: 120..173 (środek = ~150)

### getRobotRotationFromAdvancedBall(rot°)

```
base = 150
if rot > 0: result = 150 + (int)(60 * rot / 90), max 210
if rot < 0: result = 150 + (int)(60 * rot / 90), min 90
if rot == 0: result = 150
```

### setBall — format komendy (firmware < 221 vs >= 221)

Firmware stary (< 221):
```
value = motorSpeed + 5
```
Firmware nowy (>= 221):
```
value = motorSpeed * 4.016 + SpeedCAL
```

Komenda B:
```
B{topDir:0}{|topValue|:000}{bottomDir:0}{|bottomValue|:000}{oscillation:000}{height:000}{rotation:000}{leds:0}
```

---

## Sekcja 4: Komunikacja USB (FTD2XX)

Windows używa **wyłącznie USB przez FTD2XX_NET** (biblioteka FTDI). Brak BLE w wersji Windows.

### Sekwencja inicjalizacji OpenConnection()

```
1. connectToRobot(9600)          ← najpierw wolny baudrate
   a. OpenByDescription("NEWGY3050")
   b. ResetDevice()
   c. Purge(3)
   d. SetBaudRate(9600)
   e. SetDataCharacteristics(8, 0, 0)  ← 8 data bits, no parity, 1 stop bit
   f. SetTimeouts(read=1000ms, write=0)
   g. SetFlowControl(0, 0, 0)          ← brak flow control
   h. SetRTS(true)
   i. SetDTR(true)

2. Wyślij bajt 90 (0x5A = 'Z' ASCII)
3. Sleep(250ms)
4. Wyślij bajt 90 ponownie
5. Sleep(250ms)
6. CloseConnection()

7. connectToRobot(115200)        ← właściwy baudrate
8. Purge(3)
9. writeCommand("Z", expectedReply=45, responseLength=1)
   - Czeka maks. 60 sekund na odpowiedź "K"/"N"/"M"
   - Ponawia co 3 sekundy jeśli brak odpowiedzi

10. Jeśli "Z" OK: WriteCommand("H")   ← inicjalizacja robota
```

### Parametry UART

| Parametr | Wartość |
|----------|---------|
| Baudrate init | 9600 |
| Baudrate główny | 115200 |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |
| Flow control | None |
| RTS | true |
| DTR | true |
| Read timeout | 1000 ms |
| Device description | "NEWGY3050" (konfigurowalne) |

### Terminator komendy

**CRLF (`\r\n`)** — jeśli komenda nie kończy się na `\r\n`, jest automatycznie dodawane:
```csharp
if (!text.EndsWith("\r\n"))
    text = command + "\r\n";
```

### Odpowiedzi robota

| Odpowiedź | Znaczenie |
|-----------|-----------|
| `K` | OK — komenda wykonana |
| `N` | Nok — błąd lub koniec sekwencji (zatrzymuje drill) |
| `M` | OK alternatywny |

### Specjalne przypadki

- Komenda `F` (firmware): `responseLength=3` zamiast 1, timeout `2000ms`
- Komendy `T`, `O`, `R`, `U`, `Z`: czekają na `K`/`N`/`M` przez maks. 1 sekundę
- Komenda `J`: czeka na odpowiedź zawierającą `K`
- Każde wywołanie `writeCommand` poprzedzone `Purge(3)` (czyści bufory RX i TX)

### Obsługa połączenia failed

`ConnectWindow` ponawia do **20 razy** (`_connectionAttempts < 20`) przed pokazaniem błędu.

---

## Sekcja 5: Komunikacja BLE

**Windows nie używa BLE.** Aplikacja Windows korzysta wyłącznie z FTDI USB.

Brak jakichkolwiek referencji do `Windows.Devices.Bluetooth`, `Windows.Devices.Enumeration`
ani żadnego innego BLE API w zdekompilowanych plikach.

---

## Sekcja 6: Protokół komend

**Identyczny z Android** — klasy `BaseRobotService` i `BaseRobotInterface` są współdzielone.

### Wszystkie komendy

| Komenda | Format | Opis |
|---------|--------|------|
| `B` | `B{td}{tv:000}{bd}{bv:000}{osc:000}{height:000}{rot:000}{leds:0}` | Ustaw piłkę (parametry silników i głowicy) |
| `T` | `T\r\n` | Rzuć piłkę (throw) |
| `H` | `H\r\n` | Powrót do stanu bazowego / reset |
| `Z` | `Z\r\n` | Inicjalizacja — robot musi odpowiedzieć "K" |
| `F` | `F\r\n` | Zapytanie o wersję firmware (odpowiedź: 3 cyfry ASCII, np. "221") |
| `I` | `I\r\n` | Zapytanie o wersję robota (odpowiedź: bajt >1 = SecondRun, <=1 = OriginalNewFirmware) |
| `V` | `V\r\n` | Begin calibration (wysyłane 2x z 500ms odstępem) |
| `W` | `W{ms:000}` | SetAdjustment — opóźnienie (dla Gen1 i Gen2: wartość 0) |
| `S` | `S{version:byte}` | SetVersion robota |
| `U` | `U{height:value}` | Adjust Height |
| `O` | `O{oscillation:value}` | Adjust Oscillation |
| `R` | `R{rotation:value}` | Adjust Rotation |
| `Q` | `Q{speedcal:000}` | SetSpeedCAL — wysyłane tylko jeśli `num > 0` |
| `J` | `J...` | Nieznana (czeka na "K" w odpowiedzi) |

### Format komendy B (szczegóły)

```
B [td:1] [|top_value|:3] [bd:1] [|bot_value|:3] [osc:3] [height:3] [rot:3] [leds:1]
```

Gdzie:
- `td` = 1 jeśli TopMotorSpeed < 0, inaczej 0
- `bd` = 1 jeśli BottomMotorSpeed < 0, inaczej 0
- Firmware < 221: `top_value = TopMotorSpeed + 5`
- Firmware >= 221: `top_value = TopMotorSpeed * 4.016 + SpeedCAL`

Przykład (firmware >= 221, SpeedCAL=0, TopMotor=50%, BottomMotor=30%, Osc=50%, Height=60%, Rot=0°):
```
TopMotorSpeed(raw) = 28 + 182*0.5 = 119  →  119*4.016 = 477?
```
*(Uwaga: wartości % są najpierw konwertowane przez getMotorSpeed() do raw 28..210,
potem dopiero mnożone przez 4.016 w setBall())*

### LED indicators

```csharp
diff = top - bottom
ratio = |diff| / 360
ratio <= 0.10 → OneBottom/OneTop
ratio <= 0.50 → TwoBottom/TwoTop
ratio <= 0.75 → ThreeBottom/ThreeTop
ratio > 0.75  → FourBottom/FourTop
```

---

## Sekcja 7: Kalibracja

### FillRobot — wartości startowe

```csharp
new RobotBall {
    BottomMotorSpeed = 0,
    TopMotorSpeed    = 80,    // wartość raw (nie %)
    WaitTime         = 1000,
    HeadPosition = {
        Height      = 128,
        Oscillation = 128,
        Rotation    = 128
    }
}
// Następnie 11x WriteCommand("T") z 1000ms odstępem
// Potem ClearBall()
```

### CalibrationWindow — wartości startowe

| Parametr | Gen1 (Original) | Gen2 (SecondRun) |
|----------|-----------------|-----------------|
| `TopMotorSpeed` (%) | 77 | 73 |
| `BottomMotorSpeed` (%) | 0 | 0 |
| `HeadPosition.Height` (%) | 80 | 80 |
| `HeadPosition.Oscillation` (%) | 50 | 50 |
| `HeadPosition.Rotation` (°) | 0 | 0 |

Sterowanie w `CalibrationWindow`:
- **Up** → `TopMotorSpeed--` (zmniejsza prędkość)
- **Down** → `TopMotorSpeed++` (zwiększa prędkość)
- **Left** → `Oscillation -= 2`
- **Right** → `Oscillation += 2`

### Zakończenie kalibracji (complete())

```csharp
_ball.HeadPosition.Height -= 30;  // obniża wysokość przed SetSpeedCAL
SetSpeedCAL(_ball);
_ball.TopMotorSpeed = 0;
_ball.BottomMotorSpeed = 0;
SetBall(_ball);
AdjustOscillation(_ball);  // x2
FinishCalibration();        // zapisuje IsCalibrated=true
```

### SetSpeedCAL — algorytm

```csharp
robotBall = GetRobotBall(ball);  // konwertuje % → raw

// Gen1 (OriginalNewFirmware i Original):
SpeedCAL = robotBall.TopMotorSpeed - 170

// Gen2 (SecondRun):
SpeedCAL = robotBall.TopMotorSpeed - 161

// Zapisuje w konfiguracji jako "SpeedCAL"
// Jeśli SpeedCAL > 0: wysyła komendę Q{SpeedCAL:000}
```

Interpretacja: `SpeedCAL` to różnica między zmierzoną prędkością robota
a wartością docelową (170 dla Gen1, 161 dla Gen2).

### Porównanie kalibracji Android vs Windows

| Aspekt | Android (CalibrationPage) | Windows (CalibrationWindow) |
|--------|--------------------------|----------------------------|
| TopMotorSpeed start Gen1 | 77 | 77 |
| TopMotorSpeed start Gen2 | 73 | 73 |
| Krok Up/Down | ±1 | ±1 |
| Krok Left/Right (Oscillation) | ±4 | ±2 |
| Height obniżenie przed SetSpeedCAL | -30 | -30 |
| Target Gen1 | 170 | 170 |
| Target Gen2 | 161 | 161 |

**Różnica:** krok oscylacji — Android ±4, Windows ±2.

---

## Sekcja 8: Konfiguracja

### Lokalizacja pliku

`%LocalAppData%\Newgy3050\Configuration.xml`

Ścieżka: `Environment.GetFolderPath(SpecialFolder.LocalApplicationData) + "\Newgy3050\Configuration.xml"`
(`SpecialFolder = 28` = `LocalApplicationData`)

**Brak rejestru Windows** — wyłącznie XML.

### Struktura pliku Configuration.xml

```xml
<Configuration>
  <IsCalibrated>false</IsCalibrated>
  <IsLeftHanded>false</IsLeftHanded>
  <RobotDescription>NEWGY3050</RobotDescription>
  <SpeedCAL>0</SpeedCAL>
  <CurrentCount>60</CurrentCount>
  <Language>0</Language>
  <BallType>...</BallType>
</Configuration>
```

### Wszystkie klucze konfiguracji

| Klucz | Typ | Default | Znaczenie |
|-------|-----|---------|-----------|
| `IsCalibrated` | bool | `false` | Czy robot był kalibrowany |
| `IsLeftHanded` | bool | `false` | Tryb leworęczny (odwraca oscylację) |
| `RobotDescription` | string | `"NEWGY3050"` | Opis FTDI urządzenia (dla `OpenByDescription`) |
| `SpeedCAL` | int | `0` | Kalibracja prędkości — offset do firmware >=221 |
| `CurrentCount` | int | `60` | Bieżąca liczba piłek |
| `Language` | int | `0` | Język interfejsu |
| `BallType` | string | `""` | Ostatni wybrany typ piłki |

### Drille i ulubione

Ścieżka: `%MyDocuments%\Newgy3050\Drills\*.xml` i `%MyDocuments%\Drills\Favorites\*.xml`

(`SpecialFolder = 5` = `MyDocuments`)

Nazwy plików: z nazwy drilla usuwane są znaki spoza `[a-zA-Z0-9 -]`.

Format XML drilla:
```xml
<Drill Name="..." Description="..." Delay="2.5" Count="30">
  <Ball Type="AdvancedInterfaceBall">
    ...
  </Ball>
</Drill>
```

### Porównanie z Androidem

| Aspekt | Android | Windows |
|--------|---------|---------|
| Mechanizm | SharedPreferences | XML plik |
| Lokalizacja | /data/data/com.newgy/... | %LocalAppData%\Newgy3050\ |
| Klucze | identyczne | identyczne |
| Defaults | identyczne | identyczne |
| Drille | pliki XML w `/storage/...` | pliki XML w %MyDocuments% |

---

## Sekcja 9: Porównanie Android vs Windows

### Tabela kluczowych różnic

| Aspekt | Android | Windows | Identyczne? |
|--------|---------|---------|-------------|
| **Framework UI** | Xamarin.Forms | WPF | NIE |
| **Warstwa komunikacji** | BLE (MLDP) + USB (CDC) | USB tylko (FTD2XX/FTDI) | NIE |
| **BLE** | Tak (BluetoothLeService, GATT) | **Brak** | NIE |
| **USB driver** | Hoho.Android.UsbSerial | FTD2XX_NET.dll | NIE |
| **Konfiguracja** | SharedPreferences | XML w %LocalAppData% | NIE |
| **Klucze konfiguracji** | IsCalibrated, IsLeftHanded, RobotDescription, SpeedCAL, CurrentCount, Language, BallType | identyczne | TAK |
| **Logika biznesowa** | BaseRobotService | **ta sama DLL** | TAK |
| **Formuła motorSpeed** | min=28, max=210 | min=28, max=210 | TAK |
| **Formuła Height** | 75 + 135*(h/100) | 75 + 135*(h/100) | TAK |
| **Formuła Oscillation** | 173 - 53*(osc/100) | 173 - 53*(osc/100) | TAK |
| **Formuła Rotation** | 150 ± 60*(rot/90) | 150 ± 60*(rot/90) | TAK |
| **FillRobot** | Top=80, Bottom=0, H=128, Osc=128, Rot=128, 11x T | identyczny | TAK |
| **SetSpeedCAL target Gen1** | 170 | 170 | TAK |
| **SetSpeedCAL target Gen2** | 161 | 161 | TAK |
| **Krok oscylacji kalibracja** | ±4 | **±2** | **NIE** |
| **Protokół komend (ASCII)** | identyczny | identyczny | TAK |
| **Terminator CRLF** | `\r\n` | `\r\n` | TAK |
| **Firmware threshold** | 221 | 221 | TAK |
| **Enumy BallType** | identyczne | identyczne | TAK |
| **Serializacja XML piłek** | identyczna | identyczna | TAK |
| **Autofac DI** | Tak | Tak | TAK |
| **Inicjalizacja USB** | CDC Serial: 115200, 8N1 | FTDI: 9600→115200, 8N1, RTS+DTR | NIE |
| **Max prób połączenia** | nie ustalono | 20 | - |
| **Wersja kompilacji** | ~2020 | 2020-03-21 | ~TAK |

### Kluczowe wnioski

1. **Logika biznesowa jest w 100% identyczna** — ta sama `Newgy.Robots.RoboPong3050.Business.dll`
   z tymi samymi konwerterami, formułami i protokołem.

2. **Windows używa wyłącznie FTDI USB** — brak jakiegokolwiek BLE. Robot identyfikowany
   przez opis urządzenia FTDI: `"NEWGY3050"` (zmienialne w konfiguracji).

3. **Sekwencja inicjalizacji USB jest specyficzna dla Windows**: najpierw 9600 baud,
   wysłanie bajtu `0x5A` dwukrotnie (bootloader wake-up?), potem restart do 115200.

4. **Jedyna różnica w kalibracji**: krok oscylacji ±2 (Windows) vs ±4 (Android).
   Obie wersje używają tych samych wartości startowych i algorytmu SetSpeedCAL.

5. **Konfiguracja**: zamiast Android SharedPreferences — plik XML. Klucze identyczne.

---

## Appendix: Zasoby wbudowane w Business DLL

Business DLL zawiera embedded XML resources:
- `BallRangesV0.xml`, `BallRangesV1.xml`, `BallRangesV2.xml` — zakresy dla każdej wersji robota
- Drille: `Resources.Drills.*` — predefiniowane drille (Beginner, Intermediate, Advanced, Bonus)
- Treningi: `Resources.Training.AdvancedV0.xml`, `AdvancedV2.xml`, itd.

Format numerowania wersji robota (komenda `I`):
- wartość <= 1 → `RobotVersion.OriginalNewFirmware` (Gen1)
- wartość > 1  → `RobotVersion.SecondRun` (Gen2)

`SetupRanges()` ładuje plik `BallRangesV{n}.xml` gdzie `n` = byte wersji robota.
