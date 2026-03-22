# Kompletna analiza logiki biznesowej — Newgy Robopong 3050XL

Źródło: zdekompilowany kod C# z aplikacji Android (APK), Windows (MSI), iOS (IPA).
Logika biznesowa jest **współdzielona** — ta sama DLL `Newgy.Robots.RoboPong3050.Business.dll` na wszystkich platformach.

---

## 1. Model danych

### Hierarchia klas piłek

```
IInterfaceBall (interfejs)
├── InterfaceBall         — tryb Standard (enumy: BallType, SpinSpeed, Rotation)
├── AdvancedInterfaceBall — tryb Advanced (surowe wartości: TopMotor%, BottomMotor%, HeadPosition)
└── RandomInterfaceBall   — tryb Random (zakresy Low/High z RandomType)

RobotBall                 — wewnętrzna reprezentacja (wartości raw wysyłane do robota)
├── HeadPosition          — {Height, Oscillation, Rotation} — neutralna = 128 (0-255)
├── RandomHeadPosition    — per-oś Low/High/Type
└── InterfaceBallLink     — link zwrotny do źródłowej InterfaceBall
```

### Enumy

| Enum | Wartości |
|------|---------|
| **BallType** | TopSpin=0, TopSpinServe=1, BackSpin=2, BackSpinServe=3, NoSpin=4 |
| **SpinSpeed** | Lowest=0, Lower=1, Low=2, Middle=3, High=4, Higher=5, Highest=6 (7 poziomów) |
| **Rotation** | None=0, Left=1, Right=2 |
| **RotationDegrees** | None=0, Fifteen=1, Thirty=2, FortyFive=3, Sixty=4, SeventyFive=5, Ninety=6 |
| **RobotVersion** | OriginalNewFirmware=0, Original=1, SecondRun=2 (Gen2) |
| **RandomType** | Range=1, EitherOr=2, None=3 (numeracja od 1!) |
| **LEDS** | None=0, OneBottom=1, TwoBottom=2, ThreeBottom=3, FourBottom=4, OneTop=5, TwoTop=6, ThreeTop=7, FourTop=8 |

### AdvancedInterfaceBall (pola)

| Pole | Typ | Opis |
|------|-----|------|
| TopMotorSpeed | int | Procent 0-100 (lub ujemny dla odwrotnego kierunku) |
| BottomMotorSpeed | int | Procent 0-100 |
| HeadPosition | HeadPosition | {Height, Oscillation, Rotation} jako procent 0-100 |
| TableYPercent | double | Pozycja na stole (oś Y) |
| WaitTime | int | Czas między rzutami (ms) |
| BallNumber | int | Numer piłki w drilu |
| NumberOfBalls | int | Ile piłek tego typu |

### RobotBall (wartości raw)

| Pole | Typ | Neutralna | Zakres |
|------|-----|-----------|--------|
| TopMotorSpeed | int | 0 | 0-210 (po konwersji z %) |
| BottomMotorSpeed | int | 0 | 0-210 |
| HeadPosition.Height | int | 128 | 75-210 (z konwertera Advanced) |
| HeadPosition.Oscillation | int | 128 | 127-173 (z konwertera Advanced) |
| HeadPosition.Rotation | int | 128 | 90-210 (z konwertera Advanced) |
| WaitTime | int | 1000 | ms |

### BallRange (lookup table)

Ładowane z `BallRangesV{robotVersion}.xml`. Mapowanie: `BallType + SpinSpeed → zakresy silników`.

| Pole | Opis |
|------|------|
| BallType | enum |
| SpinSpeed | enum |
| TopMotorMin / TopMotorMax | Zakres prędkości górnego silnika |
| BottomMotorMin / BottomMotorMax | Zakres prędkości dolnego silnika |
| HeightMin / HeightMax | Zakres wysokości głowicy |

---

## 2. Konwertery piłek

### AdvancedBallConverter (tryb Advanced → Robot)

**Stałe zakresów:**
- Motor: min=28, max=210
- Height: min=75, max=210
- Oscillation: min=127, max=173
- Rotation: min=90, max=210

**Formuły:**

```
Motor:       0%→0, >0%→ 28 + 182*(pct/100), <0%→ 210*(pct/100)
Height:      75 + 135*(pct/100)
Oscillation: 173 − 46*(pct/100)     [leftHanded: pct = 100-pct]
Rotation:    150 + 60*(deg/90)       [clamp 90-210]
```

**Tabela przeliczeniowa Motor (%)→raw:**

| % | Raw | B-PWM (×4.016) |
|---|-----|-----------------|
| 0 | 0 | 0 |
| 25 | 73 | 293 |
| 50 | 119 | 478 |
| 73 | 161 | 647 ← Gen2 kalibracja |
| 77 | 168 | 675 ← Gen1 kalibracja |
| 100 | 210 | 843 |

**Tabela Height (%)→raw:**

| % | Raw |
|---|-----|
| 0 | 75 |
| 50 | 142 |
| 80 | 183 ← kalibracja default |
| 100 | 210 |

**Tabela Oscillation (%)→raw:**

| % | Raw |
|---|-----|
| 0 | 173 (full left) |
| 50 | 150 ← centrum |
| 100 | 127 (full right) |

**Tabela Rotation (deg)→raw:**

| Deg | Raw |
|-----|-----|
| -90 | 90 |
| 0 | 150 ← centrum |
| +90 | 210 |

**Określanie BallType z AdvancedInterfaceBall:**
- top == bottom → NoSpin
- top > bottom, height >= 50 → TopSpin, else TopSpinServe
- bottom > top, height >= 50 → BackSpin, else BackSpinServe

### InterfaceBallConverter (tryb Standard → Robot)

Bardziej złożony — konwertuje enumy (BallType, SpinSpeed) na wartości silników za pomocą `BallRange` lookup table.

**Stałe:**
- Oscillation: min=122, max=178, farOffset=7
- Rotation: min=90, max=210
- Height: min=75, max=225
- MaxMotorSpeed=210, motorSpeedOscCorrection=4

**Formuły motorów:**
```
base = BallRange.MotorMin
range = (MotorMax - MotorMin) * tableYPercent
xOffset = |tableXPercent - 0.5| / 0.5
yOffset = |tableYPercent - 0.5| / 0.5
correction = {TopSpin: 4.0, NoSpin: 2.0, BackSpin bot: 2.0, BackSpin top: 0.0}
result = base + range + correction * yOffset * xOffset
```

**Formuła Oscillation (bez rotacji):**
```
farFactor = max(0, (tableY - 0.5) / 0.5)
xFactor = (tableX - 0.5) / 0.5
farOffset = 7 * farFactor * xFactor
maxOsc = 178 + farOffset
minOsc = 122 + farOffset
result = maxOsc - (maxOsc - minOsc) * tableXPercent
```

**Formuła Rotation:**
- None → 150
- Left/Right → `150 ± (10 * RotationDegrees_enum_value)`

**Formuła Height (z korekciami):**
```
range = |HeightMin - HeightMax|
correction = (NoSpin ? 4 : 10) * |0.5-tableX|/0.5 - (NoSpin ? 2 : 7) * |0.5-tableX|/0.5
result = HeightMin + range * tableYPercent + correction
if rotation: result +/- 1.5 * rotationDegrees
```

### RandomBallConverter

Dziedziczy z `AdvancedBallConverter`. Tworzy `RobotBall` z `isRandom=true`.

**Losowanie:**
- `RandomType.Range` → `random.Next(low, high+1)`
- `RandomType.EitherOr` → 50/50 między low i high (`random.Next(1,3)`)
- `RandomType.None` → wartość stała

### BallConverterFactory

Mapowanie runtime:
- `"AdvancedInterfaceBall"` → `AdvancedBallConverter`
- `"InterfaceBall"` → `InterfaceBallConverter`
- `"RandomInterfaceBall"` → `RandomBallConverter`

---

## 3. BaseRobotService — główna klasa komunikacji

### Kluczowe pola

| Pole | Typ | Opis |
|------|-----|------|
| `_installedFirmwareVersion` | int | Wersja firmware (np. 206, 221, 701) |
| `_robotVersion` | RobotVersion | OriginalNewFirmware/Original/SecondRun |
| `_currentBall` | RobotBall | Ostatnio ustawiona piłka (cache) |
| `BallThrown` | bool | Czy piłka została wyrzucona |
| `DrillRunning` | static bool | Czy drill jest aktywny |
| `USB_Mode` | bool | Czy połączenie USB (vs BLE) |
| `USBMode_Set` | static bool | Czy komenda "USB" została wysłana |

### Kompletna tabela komend

| Komenda | Format | Timeout | Cel | Odpowiedź |
|---------|--------|---------|-----|-----------|
| `Z` | `Z\r` | 60s | Ping/init | K/N/M |
| `H` | `H\r` | 5s | Stop (homing) | K |
| `T` | `T\r` | 7s | Throw (rzut piłki) | K/N/M |
| `F` | `F\r` | 2s | Firmware version | 3 bajty string |
| `I` | `I\r` | 300ms | Robot version | 1 bajt (0/1/2) |
| `V` | `V\r` | 1s | Begin calibration (x2) | — |
| `B...` | `B{d}{sss}{d}{sss}{ooo}{hhh}{rrr}{L}` | 500ms | Set ball (fw < 701) | K |
| `wTA...` | `wTA{www}` | 5s | Wait time (fw >= 701) | K |
| `A...` | `A{d}{sss}{d}{sss}{ooo}{hhh}{rrr}{L}` | 5s | Set ball (fw >= 701) | K |
| `Y...` | `Y{nn}{nn}{t}{ss}{ss}{t}{ss}{ss}{t}{hhh}{hhh}` | 5s | Random ball cz.1 | K |
| `P...` | `P{t}{oo}{oo}{t}{rr}{rr}{t}{www}{www}{t}{dddddd}` | 5s | Random ball cz.2 | K |
| `END...` | `END{ccc}{rrr}{ddd}` | — | Koniec drilla (fw >= 701) | K per piłka |
| `U{hhh}` | `U183` | 1s | Adjust height | K |
| `O{ooo}` | `O150` | 1s | Adjust oscillation | K |
| `R{rrr}` | `R150` | 1s | Adjust rotation | K |
| `Q{sss}` | `Q025` | 500ms | SpeedCAL offset | K |
| `W{mmm}` | `W000` | 1s | Set adjustment | K |
| `J{vv}` | `J02` | 1s | Set robot version | K |
| `USB` | `USB\r` | 300ms | Switch to USB mode | K |
| `X` | `X\r` | — | Bootloader mode | — |

### setBall — pełna logika (KRYTYCZNE)

```
Wejście: RobotBall ball, bool forceBall, bool isCAL

Warunek: skip jeśli !forceBall && _currentBall.ballNumber == ball.ballNumber

1. Oblicz kierunki:
   dir_top = (ball.TopMotorSpeed < 0) ? 1 : 0
   dir_bot = (ball.BottomMotorSpeed < 0) ? 1 : 0

2. SpeedCAL (MARTWY KOD):
   num3 = (fw < 221) ? config.GetInt("SpeedCAL") : 0
   num3 = 0  ← ZAWSZE nadpisane na 0!

3. Oblicz PWM:
   Firmware 206:  value = motor + 5
   Inne:          value = motor * 4.016 + num3

4A. Ścieżka B (fw < 701 LUB isCAL LUB USB_Mode):
    writeCommand("B{d}{|v|:3}{d}{|v2|:3}{osc:3}{h:3}{rot:3}{leds}", 500)

4B. Ścieżka A (fw >= 701, nie random, nie USB):
    writeCommand("wTA{wait/10:3}")
    wait for response (max 5s) + wait(500ms)
    writeCommand("A{d}{|v|:3}{d}{|v2|:3}{osc:3}{h:3}{rot:3}{leds}", 500)
    wait for response (max 5s)

4C. Ścieżka Random (fw >= 701, random, nie USB):
    Clamp High values: 100→99 (BUG: BottomMotorLow sprawdza High!)
    writeCommand("Y{...}", 500) → wait response
    writeCommand("P{...}", 500) → wait response
    BUG: W komendzie P, kierunek BottomMotorLow używa TopMotorLow!

5. _currentBall.ballNumber = ball.ballNumber
```

### getLEDS — logika LED

```
diff = topMotorSpeed - bottomMotorSpeed
ratio = |diff| / 360.0

ratio == 0   → None(0)
ratio ≤ 0.10 → diff > 0 ? OneTop(5)   : OneBottom(1)
ratio ≤ 0.50 → diff > 0 ? TwoTop(6)   : TwoBottom(2)
ratio ≤ 0.75 → diff > 0 ? ThreeTop(7) : ThreeBottom(3)
ratio > 0.75 → diff > 0 ? FourTop(8)  : FourBottom(4)
```

### runDrill — pełna logika

```
Firmware < 701 lub USB_Mode (tryb STARY):
  for each ball in drill:
    1. setBall(robotBall, forceBall: true)
    2. wait(waitTime ms)
    3. ThrowBall() → writeCommand("T", 7000)
    4. Kompensacja opóźnienia:
       jeśli ThrowBall trwało > 625ms:
         nadmiar = (czas - 0.625) * 1000
         następny wait *= (0.000125 * waitTime + 0.5625)

Firmware >= 701, nie USB (tryb NOWY):
  for each ball in drill:
    1. setBall(robotBall, forceBall: true)
    2. wait(250ms) ← tylko 250ms!
  Po wszystkich piłkach:
    3. writeCommand("END{count:3}{random(1,255):3}{delay*10:3}")
    4. Robot sam zarządza rzutami — odpowiada:
       "K" → piłka wyrzucona, DrillBallCount--
       "N" → drill zatrzymany
```

### Kalibracja — kompletna sekwencja

**Sekwencja 3 okien (Windows WPF, w tej kolejności):**

**Krok 1: RotationCalibrationWindow**
```
1. BeginCalibration() → wysyła "V"
2. Tworzy piłkę: Height=50%, Osc=50%, Rot=0, TopMotor=0, BotMotor=0
3. SetBall(forceBall: true)
4. User reguluje Rotation strzałkami:
   - Kontynuacja kierunku: ±1
   - Zmiana kierunku: ±2 (przyspieszenie)
5. Done → AdjustRotation(ball)
   → konwertuje do raw → zapisuje RotCAL = raw - 150
   → wysyła "R{raw}"
```

**Krok 2: HeightCalibrationWindow**
```
1. Tworzy piłkę: Height=50%, Osc=50%, Rot=0, TopMotor=0, BotMotor=0
2. User reguluje Height strzałkami: ±1
3. Done → AdjustHeight(ball)
   → konwertuje do raw → zapisuje HeightCAL = raw - 150
   → wysyła "U{raw}"
```

**Krok 3: CalibrationWindow (oscylacja + prędkość)**
```
1. Wymusza IsLeftHanded = false
2. Tworzy piłkę kalibracyjną:
   SecondRun: TopMotor=73%, Bot=0%, Height=80%, Osc=50%, Rot=0
   Inne:      TopMotor=77%, Bot=0%, Height=80%, Osc=50%, Rot=0
   WaitTime=1000
3. SetBall → robot zaczyna kręcić silnikiem
4. User reguluje:
   - Oscylacja: ±2 (Windows) / ±4 (Android/iOS)
   - Prędkość: TopMotorSpeed ±1
5. ThrowBall → testowy rzut
6. Done → complete():
   a. Height -= 30 (odejmuje offset!)
   b. SetSpeedCAL(ball):
      → raw = konwersja TopMotor% do raw motor speed
      → SecondRun: offset = raw - 161
      → Inne:      offset = raw - 170
      → config["SpeedCAL"] = offset
      → jeśli offset > 0: wysyła "Q{offset:3}"
   c. Zeruje oba motory (TopMotor=0, BotMotor=0)
   d. SetBall(zerowa piłka)
   e. AdjustOscillation × 2 (z 500ms przerwą)
      → zapisuje OscCAL = raw - 150
      → wysyła "O{raw}"
   f. FinishCalibration()
      → config["IsCalibrated"] = true
      → ClearBall() → "H" + "W000"
```

### FillRobot — napełnianie podajnika

```
1. setBall: TopMotor=80, BotMotor=0, H=128, Osc=128, Rot=128, Wait=1000
   (UWAGA: używa wartości raw, nie procent!)
2. 11 × { writeCommand("T") + wait(1000) }
3. ClearBall()
```

### InitializeRobot

```
1. GetFirmwareVersion() → wysyła "F", parsuje 3-cyfrowy string
2. getRobotVersion() → wysyła "I", parsuje 1 bajt
3. config.SetupRanges(robotVersion) → ładuje BallRangesV{v}.xml
4. ClearBall() → wysyła "H" + "W000"
```

### writeCommand — niskopoziomowe wysyłanie

```
1. _lastCommand = command
2. _responseReceived = false
3. Dodaj "\r" jeśli brak
4. RobotInterface.WriteCommand(command) → BLE/USB
5. Busy-wait do responseWait ms:
   - Sprawdza QResponseReceived (kolejka)
   - Jeśli jest odpowiedź → parsuj (K/N/M/firmware)
   - Jeśli nie → sleep(10ms)
```

### Parsowanie odpowiedzi

```
Odpowiedź kończąca się na "K" → _responseReceived = true, BallThrown = true
Odpowiedź kończąca się na "N" → DrillRunning = false (stop drill)
Odpowiedź kończąca się na "M" → _responseReceived = true
Komenda "I" → parsuj bajt jako RobotVersion
Komenda "F" → buduj 3-cyfrowy string char po charze → parsuj int
```

---

## 4. Komunikacja — różnice między platformami

### BLE (Android + iOS)

| Parametr | Wartość |
|----------|---------|
| Service UUID | `00035b03-58e6-07dd-021a-08123a000300` |
| Data Characteristic | `00035b03-58e6-07dd-021a-08123a000301` |
| Control Characteristic | `00035b03-58e6-07dd-021a-08123a0003ff` |
| Terminator | `\r` (CR only) |
| Max payload | 20 bajtów (MTU) |
| Chunking | split na 2 części, wait for callback |
| Init sequence | "Z" × 3 + "H", wait 20s na K |
| Scan | Android: bonded devices, iOS: active scan |

### USB FTDI (Windows)

| Parametr | Wartość |
|----------|---------|
| Device description | `"NEWGY3050"` |
| Terminator | `\r\n` (CRLF) |
| Init baud | 9600 → 0x5A × 2 → close |
| Work baud | 115200 |
| Data bits | 8 |
| Stop bits | 1 |
| Parity | none |
| Flow control | none |
| RTS/DTR | true/true |
| Read timeout | 1000ms |
| Init sequence | "Z" (wait 60s) + "H" |
| Library | FTD2XX_NET.dll |

### USB Android

| Parametr | Wartość |
|----------|---------|
| ProductName | `"NEWGY3050"` |
| Terminator | `\r` (CR, jak BLE!) |
| Library | Hoho.Android.UsbSerial |
| Bufor | 4096 bajtów |

---

## 5. Konfiguracja — klucze i defaults

### Android (SharedPreferences)

| Klucz | Default | Opis |
|-------|---------|------|
| IsCalibrated | false | Czy kalibracja wykonana |
| BallFeedOffset | 15 | Offset podajnika piłek |
| BallFeedMotor | 10 | Prędkość silnika podajnika |
| CurrentCount | 60 | Domyślna liczba piłek |
| SpeedCAL | 0 | Offset kalibracji prędkości |
| HeightCAL | 0 | Offset kalibracji wysokości |
| OscCAL | 0 | Offset kalibracji oscylacji |
| RotCAL | 0 | Offset kalibracji rotacji |
| Generation | 2 | Generacja robota (default Gen2) |

### Windows (XML: `%LocalAppData%\Newgy3050\Configuration.xml`)

| Klucz | Default | Opis |
|-------|---------|------|
| IsCalibrated | false | |
| IsLeftHanded | false | |
| RobotDescription | NEWGY3050 | Nazwa FTDI device |
| SpeedCAL | 0 | |
| CurrentCount | 60 | |
| Language | 0 | |

**Brak w Windows:** HeightCAL, OscCAL, RotCAL, BallFeedOffset, BallFeedMotor, Generation

### iOS (NSUserDefaults)

Identyczne klucze jak Android.

---

## 6. Firmware versions — logika rozgałęzień

| Warunek | Zachowanie |
|---------|-----------|
| `== 206` | Stary firmware: `speed = motor + 5` (bez ×4.016) |
| `< 221` | SpeedCAL z konfiguracji (ale nadpisane na 0!) |
| `< 701` | Komenda `B`, synchroniczny drill z ThrowBall |
| `>= 701` | Komenda `A` + `wTA`, async drill z `END`, random `Y`+`P` |
| `>= 220` | RobotVersion detection (czeka na odpowiedź "I") |

### RobotVersion

| Wartość | Opis | SpeedCAL target |
|---------|------|-----------------|
| OriginalNewFirmware (0) | Stary HW, nowy FW | 170 |
| Original (1) | Oryginalny | 170 |
| SecondRun (2) | Gen2 (najnowszy) | 161 |

---

## 7. Znalezione bugi w oryginalnym kodzie

### BUG 1: SpeedCAL martwy kod (BaseRobotService.cs:809-810)
```csharp
int num3 = (_installedFirmwareVersion < 221) ? config.GetIntValue("SpeedCAL") : 0;
num3 = 0;  // ← ZAWSZE nadpisane!
```
SpeedCAL offset nigdy nie jest dodawany do B-komendy. Wysyłany jest tylko jako komenda `Q{offset}` do firmware.

### BUG 2: Random ball — BottomMotorLow clamp (BaseRobotService.cs:845-848)
```csharp
if (ball.RandomBall.BottomMotorHigh == 100) ball.RandomBall.BottomMotorHigh = 99;
if (ball.RandomBall.BottomMotorHigh == 100) ball.RandomBall.BottomMotorLow = 99;
//                   ↑ powinno być BottomMotorLow!
```
Warunek `BottomMotorHigh == 100` jest sprawdzany dwa razy zamiast `BottomMotorLow`.

### BUG 3: Random ball — kierunek P-komendy (BaseRobotService.cs:854)
```csharp
$"{getDirection(ball.RandomBall.TopMotorLow):0}"  // ← powinno być BottomMotorLow
```
W komendzie `P`, kierunek `BottomMotorLow` używa `TopMotorLow`.

### BUG 4: RobotBall.Equals — ignoruje WaitTime
```csharp
// Equals() porównuje: Top, Bottom, Height, Oscillation, Rotation
// NIE porównuje: WaitTime
```
Dwie piłki z różnym WaitTime są uznawane za identyczne.

---

## 8. Drill / Training

### Drill (plik XML)

```xml
<Drill Name="..." Description="..." Delay="2" Count="60">
  <AdvancedInterfaceBall TopMotorSpeed="73" BottomMotorSpeed="0" ...>
    <HeadPosition Height="80" Oscillation="50" Rotation="0"/>
  </AdvancedInterfaceBall>
</Drill>
```

| Pole | Typ | Default |
|------|-----|---------|
| Name | string | |
| Description | string | |
| Duration | double | 0.0 |
| Delay | double | z XML |
| Count | int | z XML |
| YouTubeVideoID | string | |
| Balls | ICollection\<IInterfaceBall\> | Może mieszać typy! |

### Training

```
Training
  └── TrainingDrill[]
        └── Drill
              └── IInterfaceBall[] (polimorficzna)
```

Kategorie: Introductory, Beginner, Intermediate, Advanced, Bonus.

### Ograniczenia Frequency (tryb Standard)

| Warunki | Max balls/min |
|---------|--------------|
| 1 piłka | 120 |
| >1 piłka | 90 |
| Side spin ≥60° i ≥2 piłki | 75 |
| Side spin 90° i ≥2 piłki | 60 |

Formuła: `WaitTime = 60 / Frequency * 1000` (ms)

### Walidacja drilla (tryb Advanced)

- `TopMotorSpeed + BottomMotorSpeed >= 10` dla każdej piłki
- MinWaitTime: 500ms (1 piłka), 750ms (>1 piłka)

---

## 9. Porównanie platform

| Cecha | Android | iOS | Windows |
|-------|---------|-----|---------|
| **Framework UI** | Xamarin.Forms | Xamarin.iOS | WPF |
| **BLE** | ✅ bonded scan | ✅ active scan | ❌ |
| **USB** | ✅ Hoho Serial | ❌ | ✅ FTDI FTD2XX |
| **Terminator BLE** | `\r` | `\r` | — |
| **Terminator USB** | `\r` | — | `\r\n` |
| **Init Z count** | 3× | 3× | 2× |
| **Krok oscylacji (cal)** | ±4 | ±4 | ±2 |
| **Konfiguracja** | SharedPreferences | NSUserDefaults | XML LocalAppData |
| **Drille ścieżka** | Personal/*.xml | Personal/*.xml | Documents/Newgy3050/Drills/*.xml |
| **Export drilli** | ✅ External Storage | ❌ | ❌ |
| **iCloud sync** | ❌ | ✅ | ❌ |
| **Firmware update** | ✅ (newgy.com check) | ❌ | ❌ (NotImplemented) |
| **Duplikat favorites** | sprawdza | sprawdza | nie sprawdza |
| **Logika biznesowa** | wspólna DLL | wspólna DLL (AOT) | wspólna DLL |
| **HeightCAL/OscCAL/RotCAL** | ✅ | ✅ | ❌ (brak kluczy) |
| **Generation default** | 2 (Gen2) | 2 (Gen2) | brak (inferred) |
