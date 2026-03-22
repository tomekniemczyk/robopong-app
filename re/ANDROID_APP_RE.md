# Reverse Engineering — Aplikacja Android Newgy Robopong 3050XL

Źródło: zdekompilowany kod C# z `/tmp/newgy_cs/` (Xamarin.Android, zdekompilowany narzędziem ILSpy lub podobnym).

---

## Sekcja 1: Architektura

### Diagram warstw

```
┌────────────────────────────────────────────────────────────┐
│                     UI (Xamarin.Forms)                     │
│  CalibrationPage, StandardModePage, PrecisionModePage,     │
│  RunDrillPage, EditDrillPage, RobotHomePage, ConnectPage   │
│  ControlCallibrate, ControlDrill, PrecisionBallControl     │
└────────────────────────┬───────────────────────────────────┘
                         │ IRobotService
┌────────────────────────▼───────────────────────────────────┐
│              Business Logic (Cross-Platform)               │
│  BaseRobotService — główna logika: setBall, runDrill,      │
│  ThrowBall, kalibracja, konwersja piłek                    │
│                                                            │
│  BallFactory → wybiera konwerter na podstawie typu piłki   │
│  AdvancedBallConverter / InterfaceBallConverter            │
│                    / RandomBallConverter                   │
└────────────────────────┬───────────────────────────────────┘
                         │ IRobotInterface
┌────────────────────────▼───────────────────────────────────┐
│              Android Platform Layer                        │
│  RobotInterface (BLE) / USBRobotInterface (USB)           │
│  BluetoothService — skanowanie, łączenie, zapis/odczyt    │
│  BluetoothLeService — Android Service, zarządza GATT      │
│  BGattCallback — obsługa callbacków GATT                  │
│  USBService — Hoho.Android.UsbSerial, port szeregowy      │
│  ConfigurationService — Android SharedPreferences         │
└────────────────────────┬───────────────────────────────────┘
                         │ fizyczna warstwa
┌────────────────────────▼───────────────────────────────────┐
│                   Robot Robopong 3050XL                     │
│           BLE (MLDP Microchip) / USB CDC Serial            │
└────────────────────────────────────────────────────────────┘
```

### Lista klas i odpowiedzialności

| Klasa | Namespace/Plik | Odpowiedzialność |
|-------|---------------|-----------------|
| `BaseRobotService` | Business.Services | Główna logika: setBall, runDrill, kalibracja, komendowanie robota |
| `RobotService` | Android.Services | Implementacja Android: zapis drilli (XML), pobieranie firmware, sieć |
| `BallFactory` | Business.Services | Wybiera odpowiedni konwerter (factory przez reflection) |
| `AdvancedBallConverter` | Converters | Konwertuje `AdvancedInterfaceBall` → `RobotBall` (wartości procentowe → raw) |
| `InterfaceBallConverter` | Converters | Konwertuje `InterfaceBall` (BallType+SpinSpeed+pozycja) → `RobotBall` |
| `RandomBallConverter` | Converters | Konwertuje `RandomInterfaceBall` → `RobotBall` (losowanie wartości) |
| `BallConverterFactory<T>` | Converters | Generic factory, mapuje typ piłki na konwerter |
| `RobotInterface` | Android.Services | Warstwa BLE dla robota: opakowuje BluetoothService |
| `USBRobotInterface` | Android.Services | Warstwa USB dla robota: opakowuje USBService |
| `BluetoothService` | Android.Services | Skanowanie BLE (filtr "NEWGY"/"NWGY"), połączenie GATT, write/read |
| `BluetoothLeService` | Android.Services | Android Service (foreground), trzyma BluetoothGatt |
| `BGattCallback` | Android.Services | Callbacki GATT: OnConnectionStateChange, OnServicesDiscovered, OnCharacteristicChanged |
| `USBService` | Android.Services | Hoho.Android.UsbSerial: otwarcie portu, zapis/odczyt, device "NEWGY3050" |
| `ConfigurationService` | Android.Services | SharedPreferences: klucze konfiguracji i defaults |
| `BaseConfigurationService` | Business.Services | Logika BallRanges (ładowanie z zasobów XML) |
| `AdvancedInterfaceBall` | Entities.Balls | Piłka w trybie zaawansowanym (wartości %) |
| `InterfaceBall` | Entities.Balls | Piłka w trybie standardowym (BallType, SpinSpeed, pozycja % na stole) |
| `RandomInterfaceBall` | Entities.Balls | Piłka losowa (zakresy Low/High dla każdego parametru) |
| `RobotBall` | Entities.Balls | Piłka gotowa do wysyłki (wartości raw dla silników i głowicy) |
| `HeadPosition` | Entities | Pozycja głowicy: Height, Oscillation, Rotation (raw) |
| `RandomHeadPosition` | Entities | Zakresy losowe dla pozycji głowicy |
| `BallRange` | Entities.Balls | Zakres parametrów dla danego BallType+SpinSpeed (zasoby XML) |
| `Drill` | Entities | Drill: Name, Balls[], Delay, Count, Duration |
| `CalibrationPage` | UI.Pages | Strona kalibracji prędkości: strzałki Up/Down (TopMotorSpeed ±1), Left/Right (Oscillation ±4) |
| `ControlCallibrate` | UI.Controls | Kontrolka kalibracji z pełnymi opcjami: Height, Rotation, Oscillation, TopMotorSpeed |
| `BaseRobotInterface` | Business.Services | Abstrakcja interfejsu komunikacji: zdarzenia, WriteCommand |

---

## Sekcja 2: Model danych piłki

### AdvancedInterfaceBall

Główny model używany w trybie "Advanced" (precyzyjne sterowanie procentami).

| Pole | Typ | Zakres (UI) | Znaczenie |
|------|-----|------------|-----------|
| `TopMotorSpeed` | int | -100..100 | Prędkość górnego silnika (%) — ujemna = odwrotny kierunek |
| `BottomMotorSpeed` | int | -100..100 | Prędkość dolnego silnika (%) — ujemna = odwrotny kierunek |
| `HeadPosition.Height` | int | 0..100 | Wysokość głowicy (%) |
| `HeadPosition.Oscillation` | int | 0..100 | Oscylacja/kierunek poziomy (%) — 0=prawo, 50=środek, 100=lewo (dla praworęcznych) |
| `HeadPosition.Rotation` | int | -90..90 | Obrót głowicy w stopniach (ujemny = lewo, 0 = prosto, dodatni = prawo) |
| `WaitTime` | int | ms | Czas oczekiwania między piłkami |
| `NumberOfBalls` | int | 1..N | Ile razy wysłać tę piłkę w drilla |
| `BallNumber` | int | — | Numer porządkowy w drilla |
| `TableYPercent` | double | 0.0..1.0 | Procent stołu w osi Y (opcjonalne, dla podglądu) |

Serializacja XML (klucz Type="AdvancedInterfaceBall"):
```xml
<Ball Type="AdvancedInterfaceBall">
  <BallNumber>1</BallNumber>
  <NumberOfBalls>3</NumberOfBalls>
  <WaitTime>1500</WaitTime>
  <TopMotorSpeed>75</TopMotorSpeed>
  <BottomMotorSpeed>25</BottomMotorSpeed>
  <Height>60</Height>
  <Oscillation>50</Oscillation>
  <Rotation>0</Rotation>
</Ball>
```

### InterfaceBall (tryb standardowy)

| Pole | Typ | Wartości |
|------|-----|---------|
| `Type` | `BallType` | TopSpin, TopSpinServe, BackSpin, BackSpinServe, NoSpin |
| `SpinSpeed` | `SpinSpeed` | Lowest(0), Lower, Low, Middle, High, Higher, Highest(6) |
| `Rotation` | `Rotation` | None(0), Left(1), Right(2) |
| `RotationDegrees` | `RotationDegrees` | None(0), Fifteen, Thirty, FortyFive, Sixty, SeventyFive, Ninety |
| `TableXPercent` | double | 0.0=lewa, 0.5=środek, 1.0=prawa (oś pozioma stołu) |
| `TableYPercent` | double | 0.0=bliski koniec, 1.0=daleki koniec stołu |
| `WaitTime` | int | ms |
| `BallNumber`, `NumberOfBalls` | int | — |

### RobotBall (wartości raw wysyłane do robota)

| Pole | Typ | Zakres raw | Znaczenie |
|------|-----|-----------|-----------|
| `TopMotorSpeed` | int | 0..210 (lub ujemny) | Prędkość górnego silnika — wartość raw po konwersji |
| `BottomMotorSpeed` | int | 0..210 (lub ujemny) | Prędkość dolnego silnika — wartość raw po konwersji |
| `HeadPosition.Height` | int | 75..210 | Wysokość głowicy (raw) |
| `HeadPosition.Oscillation` | int | 127..173 | Oscylacja (raw) — 173=prawa, 127=lewa (odwrócone!) |
| `HeadPosition.Rotation` | int | 90..210 | Obrót (raw) — 150=prosto, 90=max lewo, 210=max prawo |
| `WaitTime` | int | ms | Czas oczekiwania |
| `isRandom` | bool | — | Czy to piłka losowa |
| `ballNumber` | int | — | Numer porządkowy |
| `RandomBall` | `RandomInterfaceBall` | — | Parametry losowe (używane tylko gdy isRandom=true) |
| `InterfaceBallLink` | `InterfaceBall` | — | Link do oryginalnej InterfaceBall |

### HeadPosition (w RobotBall — wartości raw)

```
Height:      75 = najniżej, 210 = najwyżej
             Wzór: 75 + round(135 * (height% / 100))
             Przykład: 50% → 75 + 67 = 142

Oscillation: 173 = skrajnie prawo (0%), 127 = skrajnie lewo (100%)
             Wzór: 173 - round(46 * (osc% / 100))
             Przykład: 50% → 173 - 23 = 150 (środek)
             UWAGA: dla lewej ręki wejście = 100 - osc%

Rotation:    150 = prosto, 90 = max lewo (-90 stopni), 210 = max prawo (+90 stopni)
             Wzór dla rot>0: 150 + round(60 * rot/90), max 210
             Wzór dla rot<0: 150 + round(60 * rot/90), min 90
             Wzór dla rot=0: 150
```

### RandomInterfaceBall

| Pole | Typ | Znaczenie |
|------|-----|-----------|
| `TopMotorLow/High` | int | Zakres % prędkości górnego silnika |
| `BottomMotorLow/High` | int | Zakres % prędkości dolnego silnika |
| `TopMotorType` | RandomType | Range(1)=losuj z zakresu, EitherOr(2)=jeden z dwóch, None(3) |
| `NumberOfBallsLow/High` | int | Zakres liczby piłek |
| `WaitTimeLow/High` | int | Zakres czasu oczekiwania (ms) |
| `HeadPosition` | RandomHeadPosition | Zakresy dla Height/Oscillation/Rotation |

---

## Sekcja 3: Algorytmy konwersji (AdvancedBallConverter)

### Konwersja prędkości silnika (`getMotorSpeed`)

```csharp
protected int getMotorSpeed(int motorPercent, int minSpeed, int maxSpeed)
{
    if (motorPercent == 0) return 0;
    if (motorPercent <= 0)
        // ujemna prędkość — odwrotny obrót
        return Convert.ToInt32((decimal)maxSpeed * ((decimal)motorPercent / 100m));
    return Convert.ToInt32((decimal)minSpeed + (decimal)(maxSpeed - minSpeed) * ((decimal)motorPercent / 100m));
}
```

**Parametry dla silników głównych:** minSpeed=28, maxSpeed=210

Wzór dla wartości dodatnich: `raw = 28 + 182 * (percent / 100)`

Wzór dla wartości ujemnych: `raw = -(210 * |percent| / 100)`

| % wejście | raw output (dodatni) | raw output (ujemny) |
|-----------|---------------------|---------------------|
| 0% | 0 | 0 |
| 10% | 46 | -21 |
| 25% | 74 | -52 |
| 50% | 119 | -105 |
| 75% | 165 | -158 |
| 100% | 210 | -210 |

**Parametry SpinSpeed (dla BallRange lookup):** minSpeed=210, maxSpeed=210 (zawsze max)

### Konwersja wysokości (`getRobotHeightFromAdvancedBall`)

```csharp
protected int getRobotHeightFromAdvancedBall(int advancedInterfaceHeight)
{
    return 75 + Convert.ToInt32(135m * ((decimal)advancedInterfaceHeight / 100m));
}
```

Wzór: `raw = 75 + round(135 * percent/100)`

| % wejście | raw output |
|-----------|-----------|
| 0% | 75 |
| 25% | 109 |
| 50% | 142 |
| 75% | 176 |
| 100% | 210 |

### Konwersja oscylacji (`getRobotOscillationFromAdvancedBall`)

```csharp
protected int getRobotOscillationFromAdvancedBall(int advancedInterfaceOscillation, bool leftHanded)
{
    int num = (leftHanded ? (100 - advancedInterfaceOscillation) : advancedInterfaceOscillation);
    return 173 - Convert.ToInt32(46m * ((decimal)num / 100m));
}
```

Wzór (praworęczny): `raw = 173 - round(46 * percent/100)`
Wzór (leworęczny): `raw = 173 - round(46 * (100-percent)/100)` = odwrócony

| % wejście (praworęczny) | raw output | Znaczenie |
|------------------------|-----------|-----------|
| 0% | 173 | Skrajnie prawo |
| 25% | 161 | Prawo |
| 50% | 150 | Środek |
| 75% | 138 | Lewo |
| 100% | 127 | Skrajnie lewo |

**Uwaga:** Zakres raw 127–173 odpowiada zakresowi min/max oscylacji. Środek = 150.

### Konwersja rotacji (`getRobotRotationFromAdvancedBall`)

```csharp
protected int getRobotRotationFromAdvancedBall(int advancedInterfaceRotation)
{
    decimal num = (decimal)advancedInterfaceRotation / 90m;
    int num2 = 150;
    if (advancedInterfaceRotation > 0)
    {
        num2 = Convert.ToInt32(150m + 60m * num);  // max 210
    }
    else if (advancedInterfaceRotation < 0)
    {
        num2 = Convert.ToInt32(150m + 60m * num);  // min 90
    }
    return num2;
}
```

Wzór: `raw = 150 + round(60 * degrees/90)`, zakres [90, 210]

| Stopnie | raw output |
|---------|-----------|
| -90 | 90 |
| -45 | 120 |
| 0 | 150 |
| 45 | 180 |
| 90 | 210 |

### Obsługa lewej ręki

Dla `Oscillation`: wejście zastępowane przez `100 - percent` przed konwersją.
Efekt: piłki lewostronne lustrzanie odbijają oscylację.

Dla rotacji w komendzie P (random): `getLeftHanded()` podaje `100 - OscillationLow/High`.

### Obsługa ujemnych prędkości

Ujemna prędkość silnika = odwrotny obrót silnika (np. backspin przy pewnych konfiguracjach).

W komendzie B/A: bit kierunku wyodrębniany osobno:
```csharp
int num  = (ball.TopMotorSpeed    < 0) ? 1 : 0;  // bit kierunku top
int num2 = (ball.BottomMotorSpeed < 0) ? 1 : 0;  // bit kierunku bottom
```

Prędkość wysyłana jako wartość bezwzględna: `Math.Abs(value)`.

---

## Sekcja 4: Komunikacja BLE

### UUID serwisu i charakterystyk (Microchip MLDP)

```
Serwis:          00035b03-58e6-07dd-021a-08123a000300   (MLDP_PRIVATE_SERVICE)
Dane (write/notify): 00035b03-58e6-07dd-021a-08123a000301   (MLDP_DATA_PRIVATE_CHAR)
Kontrola:        00035b03-58e6-07dd-021a-08123a0003ff   (MLDP_CONTROL_PRIVATE_CHAR)
Notification descriptor: 00002902-0000-1000-8000-00805f9b34fb  (standard CCCD)
```

To jest standardowy Microchip MLDP (Microchip Low-energy Data Profile) — moduł BLE RN4020 lub podobny.

### Sekwencja połączenia BLE krok po kroku

```
1. BluetoothService.Connect(forBootLoader=false):
   - Pobiera BluetoothManager/Adapter
   - Tworzy ServiceManager (IServiceConnection)
   - BindService → BluetoothLeService

2. ServiceManagerOnServiceConnected():
   - Przeszukuje bondedDevices (sparowane) — filtr: name.Contains("NEWGY") lub "NWGY"
   - Jeśli znaleziono: DeviceAddress = robot.Address
   - Wywołuje connectService(binder)

3. connectService() [async]:
   - BluetoothLeService.Initialize() — ustawia BluetoothManager/Adapter
   - BluetoothLeService.Connect(DeviceAddress):
     * GetRemoteDevice(address)
     * device.ConnectGatt(..., BGattCallback, BluetoothTransports.LE=2)
     * RequestConnectionPriority(GattConnectionPriority.High=1)

4. BGattCallback.OnConnectionStateChange(ProfileState.Connected=2):
   - BroadcastUpdate(ACTION_GATT_CONNECTED)
   - mBluetoothGatt.DiscoverServices()

5. BGattCallback.OnServicesDiscovered():
   - BroadcastUpdate(ACTION_GATT_SERVICES_DISCOVERED)

6. ServiceManagerOnReceive(ACTION_GATT_CONNECTED):
   - Jeśli BondState == 10 (None) lub 12 (Bonded):
     findMldpGattService(GetSupportedGattServices())

7. findMldpGattService():
   - Szuka serwisu MLDP_PRIVATE_SERVICE
   - W nim szuka MLDP_DATA_PRIVATE_CHAR
   - Ustawia WriteCharacteristic
   - Jeśli właściwość NOTIFY (0x10): włącza notyfikacje + pisze CCCD descriptor (EnableIndicationValue)
   - Jeśli WriteCharacteristic != null → IsConnected = true

8. Sekwencja inicjalizacji robota (Task.Run):
   WriteCommand("Z")  ← reset/keep-alive
   Delay(100)
   WriteCommand("Z")
   Delay(100)
   WriteCommand("Z")
   Delay(100)
   WriteCommand("H")  ← reset position

   Czeka max 20 sek na odpowiedź (pętla: WriteCommand("Z"), Delay(1000))
   Jeśli odpowiedź: ConnectionMade event
   Jeśli nie: ConnectionFailed event

9. Dla bootloader (forBootLoader=true):
   WriteCommand("X")  ← wejście w tryb bootloadera
   Delay(100)
   WriteCommand("X")
   ConnectionMade event
```

### Chunking długich komend

BLE ma limit 20 bajtów na jedną charakterystykę. BluetoothService automatycznie dzieli:

```csharp
public bool WriteCommand(string command)
{
    string text = command.EndsWith("\r") ? command : command + "\r";
    if (text.Length <= 20)
    {
        writeCommand(text);
    }
    else
    {
        writeCommand(text.Substring(0, 20));
        // czeka na potwierdzenie write (max 200ms)
        writeCommand(text.Substring(20));
    }
}
```

Komendy dłuższe niż 20 znaków (np. Y i P) są dzielone na 2 części (20 + reszta).

### Format odpowiedzi robota

Odpowiedzi odbierane przez `BGattCallback.OnCharacteristicChanged()`:
- Wartość charakterystyki pobierana przez `GetStringValue(0)`
- Enqueue do `BluetoothLeService.QResponseReceived`

Rozpoznawanie odpowiedzi w `BaseRobotService._robotInterface_ResponseReceived()`:

| Odpowiedź kończy się | Znaczenie |
|---------------------|-----------|
| `K` | Sukces, piłka wyrzucona |
| `N` | Drill zakończony (DrillRunning = false) |
| `M` | Inna odpowiedź OK |
| 3-cyfrowa liczba (po komendzie F) | Wersja firmware |
| 1-cyfrowa liczba (po komendzie I) | Wersja robota (RobotVersion) |

### Obsługa błędów i reconnect

- `ServiceManagerOnServiceDisconnected`: `IsConnected = false`
- `ACTION_GATT_DISCONNECTED`: `BluetoothLeService.Close()`, `IsConnected = false`
- Reconnect: `BaseRobotService.ReconnectToDevice()` → `ConnectToDevice(_deviceName)`
- Po 20 sekundach bez odpowiedzi na "H" → `ConnectionFailed` event

---

## Sekcja 5: Komunikacja USB

### Parametry portu

```
Biblioteka: Hoho.Android.UsbSerial (CDC driver)
Device name: "NEWGY3050" (ProductName)
BaudRate:    9600 (pierwsza próba) → 115200 (docelowe)
DataBits:    8
StopBits:    1 (StopBits.One)
Parity:      0 (Parity.None)
Buffer:      4096 bajtów
```

### Sekwencja inicjalizacji USB krok po kroku

```
1. USBRobotInterface.OpenConnection():
   - Otwórz na 9600 baud:
     * USBService.OpenConnection(9600)
     * WriteCommand("Z")  ← keep-alive/reset
     * Czekaj 15 sekund (!!)  ← reset firmware robota

   - Zamknij połączenie: CloseConnection()

   - Otwórz na 115200 baud:
     * USBService.OpenConnection(115200)
     * WriteCommand("Z")
     * Thread.Sleep(250)
     * WriteCommand("H")  ← reset pozycji

   - Jeśli sukces → ConnectionMade("NEWGY3050")
   - Jeśli błąd → ConnectionFailed

2. USBService.OpenConnection(baudRate):
   - Pobiera UsbManager
   - Szuka urządzenia "NEWGY3050"
   - Sprawdza/prosi o uprawnienia
   - Tworzy SerialInputOutputManager (Hoho)
   - Ustawia parametry (BaudRate, DataBits, StopBits, Parity)
   - Rejestruje DataReceived handler
   - val3.Open(val, 4096)

3. Odbiór danych:
   - SerialInputOutputManager.DataReceived → UpdateReceivedData(byte[])
   - Dekodowanie ASCII → string → QResponseReceived.Enqueue()
```

### Zapis danych USB

```csharp
public void WriteCommand(string command)
{
    string text = command.EndsWith("\r") ? command : command + "\r";
    byte[] bytes = new UTF8Encoding().GetBytes(text);
    _port.Write(bytes, bytes.Length);
}
```

### Różnice USB vs BLE

| Aspekt | BLE | USB |
|--------|-----|-----|
| Terminator | `\r` (CR) | `\r` (CR) — identyczny |
| Chunking | Tak (20 bajtów) | Nie |
| Inicjalizacja | "ZZZ" + "H" + pętla Z/1s | 9600 baud + wait 15s → 115200 + "H" |
| Timeout połączenia | 20 sekund | ~15 sekund |
| Wykrywanie urządzenia | Paired devices filtr "NEWGY"/"NWGY" | ProductName == "NEWGY3050" |
| Tryb drill firmware >= 701 | Komenda END (asynchroniczny) | Komenda B (synchroniczny, USB_Mode=true) |
| SetUSBMode | Wysyła "USB\r" raz | — |

W `BaseRobotService`: gdy `USB_Mode == true`, używany jest zawsze stary protokół (komenda B, nie A), niezależnie od wersji firmware.

---

## Sekcja 6: Protokół komend

Wszystkie komendy kończone znakiem `\r` (carriage return, 0x0D).

### Tabela komend

| Komenda | Format | Odpowiedź | Znaczenie |
|---------|--------|-----------|-----------|
| `H` | `H\r` | K/M | Reset pozycji / keep-alive / clear ball |
| `V` | `V\r` | — | BeginCalibration — robot wchodzi w tryb kalibracji |
| `T` | `T\r` | K | Throw ball — wyrzuć piłkę |
| `F` | `F\r` | 3-cyfrowa liczba | Zapytanie o wersję firmware (3 znaki, np. "701") |
| `I` | `I\r` | 1 cyfra | Zapytanie o wersję robota (RobotVersion: 0=OriginalNewFirmware, 1=Original, 2=SecondRun) |
| `Z` | `Z\r` | — | Keep-alive / synchronizacja podczas połączenia |
| `X` | `X\r` | — | Wejście w tryb bootloadera |
| `USB` | `USB\r` | — | Sygnalizacja trybu USB (wysyłane raz przy inicjalizacji USB) |
| `J##` | `J{version:00}\r` | — | Ustaw wersję robota (np. `J02`) |
| `W###` | `W{ms:000}\r` | — | SetAdjustment — wait adjustment (obecnie zawsze W000) |
| `U###` | `U{height:000}\r` | — | Ustaw wysokość głowicy (raw, np. U142) |
| `O###` | `O{osc:000}\r` | — | Ustaw oscylację (raw, np. O150) |
| `R###` | `R{rot:000}\r` | — | Ustaw rotację (raw, np. R150) |
| `Q###` | `Q{offset:000}\r` | — | SpeedCAL offset (np. Q012) |
| `B...` | patrz niżej | K/M | Ustaw piłkę (firmware < 701 lub USB) |
| `wTA###` | `wTA{waitTime/10:000}\r` | K/M | Ustaw czas oczekiwania (firmware >= 701) |
| `A...` | patrz niżej | K/M | Ustaw piłkę (firmware >= 701, BLE) |
| `Y...` | patrz niżej | K/M | Ustaw losową piłkę — część 1 |
| `P...` | patrz niżej | K/M | Ustaw losową piłkę — część 2 |
| `END...` | patrz niżej | N | Zakończ drill (firmware >= 701) |

---

### Komenda B — format szczegółowy (firmware < 701 lub USB)

```
B{dirTop:0}{absTop:000}{dirBottom:0}{absBottom:000}{oscillation:000}{height:000}{rotation:000}{leds:0}
```

Przykład dla piłki: TopMotor=75%, Bottom=25%, Height=50%, Osc=50%, Rot=0, fw<701:

1. Konwersja: TopMotor: 28+182*0.75=164.5≈165; Bottom: 28+182*0.25=73.5≈74
2. Przeliczenie raw (×4.016): 165*4.016=662.6 → Math.Abs(662.6)≈663; 74*4.016=297.2≈297
3. Height: 75+135*0.5=142; Osc: 173-46*0.5=150; Rot: 150
4. LEDS: |165-74|=91; 91/360=0.253 → TwoTop(6)

```
B0663029700150142150 6
  ↑ dir top=0 (forward)
   ↑↑↑ top speed raw=663
      ↑ dir bottom=0 (forward)
       ↑↑↑ bottom speed raw=297
          ↑↑↑ oscillation=150
             ↑↑↑ height=142
                ↑↑↑ rotation=150
                   ↑ leds=6 (TwoTop)
```

**Przeliczenie prędkości w komendzie B/A:**
```csharp
double value  = (fw==206) ? (TopMotorSpeed+5) : TopMotorSpeed*4.016 + SpeedCAL;
double value2 = (fw==206) ? (BottomMotorSpeed+5) : BottomMotorSpeed*4.016 + SpeedCAL;
```

Gdzie `TopMotorSpeed` to już wartość raw z konwertera (np. 165).
Dla firmware 206: dodaje po 5.
Dla pozostałych: mnoży przez 4.016.

**Uwaga historyczna:** SpeedCAL był dawniej dodawany do prędkości (firmware < 221), ale w aktualnym kodzie jest jawnie zerowany (`num3 = 0`).

---

### Komenda A — format (firmware >= 701, BLE)

Format identyczny jak B, ale:
- Poprzedzana przez `wTA` (wait time)
- Używana tylko w trybie BLE, nie USB
- Robot potwierdza każdą komendę A przed kolejną

```csharp
writeCommand($"wTA{ball.WaitTime / 10:000}");
// czeka na odpowiedź...
writeCommand($"A{num:0}{Math.Abs(value):000}{num2:0}{Math.Abs(value2):000}" +
             $"{ball.HeadPosition.Oscillation:000}{ball.HeadPosition.Height:000}" +
             $"{ball.HeadPosition.Rotation:000}{getLEDS(...):0}");
```

Sekwencja dla firmware >= 701 (BLE):
```
wTA150\r    ← WaitTime=1500ms, wysyłane jako 150 (÷10)
     ↓ czeka na K/M
A0663029700150142150 6\r   ← identyczne pola jak B
     ↓ czeka na K/M
```

---

### Komenda Q — SpeedCAL offset

```
Q{offset:000}\r
```

Przykład: `Q012\r` — ustawia offset prędkości na 12.

Kiedy wysyłana: tylko gdy `num > 0`:
```csharp
num = (robotVersion == SecondRun) ? (TopMotorSpeed - 161) : (TopMotorSpeed - 170);
if (num > 0) writeCommand($"Q{num:000}", 500);
```

Wartości startowe kalibracji:
- Gen1 (Original): TopMotorSpeed=77%, raw=28+182*0.77=168 → offset = 168-170 = -2 (< 0, nie wysyłane)
- Gen2 (SecondRun): TopMotorSpeed=73%, raw=28+182*0.73=161 → offset = 161-161 = 0 (nie wysyłane)

---

### Komenda wTA — wait time (firmware >= 701)

```
wTA{waitTime/10:000}\r
```

WaitTime w ms dzielony przez 10.
Przykład: WaitTime=1500ms → `wTA150\r`

---

### Komendy Y i P — random ball

Komenda Y (część 1):
```
Y{numBallsLow:00}{numBallsHigh:00}{numBallsType:0}
 {topMotorLow:00}{topMotorHigh:00}{topMotorType:0}
 {bottomMotorLow:00}{bottomMotorHigh:00}{bottomMotorType:0}
 {heightLow:000}{heightHigh:000}
```

Komenda P (część 2):
```
P{heightType:0}{oscLow:00}{oscHigh:00}
 {oscType:0}{rotLow:00}{rotHigh:00}
 {rotType:0}{waitTimeHigh/10:000}{waitTimeLow/10:000}
 {waitTimeType:0}{dirTopHigh:0}{dirTopLow:0}
 {dirBottomHigh:0}{dirTopLow:0}{dirRotHigh:0}
 {dirRotLow:0}
```

Gdzie `dirX` = 1 jeśli wartość < 0, else 0.
Dla lewej ręki: OscillationLow/High zastępowane przez `100 - wartość`.

`RandomType`: Range=1, EitherOr=2, None=3 (mapowanie przez `getRandomType()`).

Uwaga: wartości 100 są obcinane do 99:
```csharp
if (ball.RandomBall.TopMotorHigh == 100) ball.RandomBall.TopMotorHigh = 99;
```

---

### Komenda END — zakończenie drilla (firmware >= 701)

```
END{count:000}{randomSeed:000}{delay*10:000}\r
```

Przykład: 10 piłek, ziarno losowe 42, delay 5 sekund:
```
END010042050\r
```

Gdzie:
- `count` — liczba piłek do wyrzucenia
- `randomSeed` — random.Next(1, 255), losowy identyfikator sesji
- `delay*10` — przerwa między cyklami (sekundy × 10)

Po wysłaniu END, robot samodzielnie wyrzuca piłki i odpowiada N gdy skończy.

---

### Komenda FillRobot (specjalna sekwencja)

Sekwencja wypełniania robota piłkami:
```
setBall(TopMotor=80, Bottom=0, Height=128, Osc=128, Rot=128, WaitTime=1000, forceBall=true)
T\r  ← 11 razy z wait 1000ms
H\r  ← reset
```

---

## Sekcja 7: Kalibracja (SpeedCAL)

### Startowe wartości piłki kalibracyjnej

W `CalibrationPage.setup()` i `ControlCallibrate.load_config_ball()`:

| Wersja robota | TopMotorSpeed | BottomMotorSpeed | Height | Oscillation | Rotation |
|---------------|--------------|-----------------|--------|-------------|---------|
| SecondRun (Gen2, value=2) | 73% | 0% | 80% | 50% | 0 |
| Original/OriginalNewFirmware (Gen1) | 77% | 0% | 80% | 50% | 0 |

### Jak użytkownik dostosowuje (CalibrationPage)

| Strzałka | Zmiana |
|----------|--------|
| Up (↑) | `TopMotorSpeed -= 1` (wolniej = piłka idzie niżej) |
| Down (↓) | `TopMotorSpeed += 1` (szybciej = piłka idzie wyżej) |
| Left (←) | `Oscillation -= 4` |
| Right (→) | `Oscillation += 4` |

Po każdej zmianie: `SetBall(ball, forceBall=true, isCAL=true)` → wysyła komendę B (tryb kalibracji).

### Jak dostosowuje ControlCallibrate (pełna kalibracja)

| Przycisk | Zmiana |
|----------|--------|
| Up | `TopMotorSpeed -= 1` |
| Down | `TopMotorSpeed += 1` |
| Left | `Oscillation -= 2` |
| Right | `Oscillation += 2` |
| UpRbt | `Height += 1` |
| DownRbt | `Height -= 1` |
| LeftRte | `Rotation += 1 lub 2` (zależnie od kierunku) |
| RightRte | `Rotation -= 1 lub 2` |

Wyświetlany podgląd: Height, Rotation, Oscillation, TopMotorSpeed.

### Jak obliczany jest SpeedCAL (`SetSpeedCAL`)

```csharp
public void SetSpeedCAL(AdvancedInterfaceBall ball)
{
    RobotBall robotBall = _ballFactory.GetRobotBall(ball, IsLeftHanded);
    // robotBall.TopMotorSpeed to wartość raw (28..210)
    int num;
    if (_robotVersion == RobotVersion.SecondRun)
        num = robotBall.TopMotorSpeed - 161;  // Gen2: baseline = 161
    else
        num = robotBall.TopMotorSpeed - 170;  // Gen1: baseline = 170

    _configurationService.SetValue("SpeedCAL", num);
    if (num > 0)
        writeCommand($"Q{num:000}", 500);
}
```

Baseline:
- Gen2 (SecondRun): 73% → raw=28+182*0.73=161 → baseline=161
- Gen1 (Original): 77% → raw=28+182*0.77=168 → baseline=170

Offset zapisywany do konfiguracji jako "SpeedCAL".

### Sekwencja zakończenia kalibracji (`CalibrationPage.complete`)

```
1. IsLeftHanded = _isLeftHanded  (przywróć oryginalne ustawienie)
2. _ball.HeadPosition.Height -= 30  (obniż o 30 punktów % dla pozycji bazowej)
3. SetSpeedCAL(_ball)  → oblicz offset, wyślij Q
4. _ball.TopMotorSpeed = 0
5. _ball.BottomMotorSpeed = 0
6. SetBall(_ball, forceBall=true, isCAL=true)  → wyślij B z zerową prędkością
7. Task.Delay(500)
8. AdjustOscillation(_ball)  → wyślij O{osc:000}, zapisz OscCAL
9. FinishCalibration():
   - SetValue("IsCalibrated", true)
   - ClearBall()  → writeCommand("H"), SetAdjustment()
```

### Sekwencja ControlCallibrate `write_config_ball`

```
1. _ball.HeadPosition.Height -= 30
2. SetSpeedCAL(_ball)    → Q komenda
3. AdjustHeight(_ball)   → U komenda, zapisz HeightCAL = raw - 150
4. AdjustRotation(_ball) → R komenda, zapisz RotCAL = raw - 150
5. AdjustOscillation(_ball) → O komenda, zapisz OscCAL = raw - 150
6. Zapis do cfgHsh: Height, Rotation, TopMotorSpeed, Oscillation
7. cfgHsh.SaveToDisk("currentconfig.xml")
8. _ball.TopMotorSpeed = 0, _ball.BottomMotorSpeed = 0
9. SetBall(_ball, false, false)
10. Task.Delay(200)
11. FinishCalibration()
```

### Co zapisywane do konfiguracji (SharedPreferences)

| Klucz | Jak obliczany | Opis |
|-------|--------------|------|
| `SpeedCAL` | TopMotorSpeed_raw - baseline | Offset prędkości (int, może być 0 lub ujemny) |
| `HeightCAL` | Height_raw - 150 | Offset wysokości |
| `RotCAL` | Rotation_raw - 150 | Offset rotacji |
| `OscCAL` | Oscillation_raw - 150 | Offset oscylacji |
| `IsCalibrated` | true | Flaga czy kalibracja wykonana |

Dodatkowy plik `currentconfig.xml` (na dysku): Height, Rotation, TopMotorSpeed, Oscillation.

---

## Sekcja 8: Drill/Scenariusz

### Budowa Drill

```xml
<Drill Name="nazwa" Description="opis" Delay="5.0" Count="50">
  <Ball Type="AdvancedInterfaceBall">
    <BallNumber>1</BallNumber>
    <NumberOfBalls>3</NumberOfBalls>
    <WaitTime>1500</WaitTime>
    <TopMotorSpeed>75</TopMotorSpeed>
    <BottomMotorSpeed>0</BottomMotorSpeed>
    <Height>60</Height>
    <Oscillation>30</Oscillation>
    <Rotation>0</Rotation>
  </Ball>
  <Ball Type="AdvancedInterfaceBall">
    ...kolejna piłka...
  </Ball>
</Drill>
```

Parametry drilla:
- `Count` — liczba cykli (ile razy powtórzyć całą sekwencję piłek)
- `Delay` — przerwa w sekundach między cyklami (czas na zebranie piłek)
- `Duration` — czas trwania w minutach (alternatywa dla Count, 0 = używaj Count)
- `Balls` — lista piłek (posortowana po BallNumber)

### Sekwencja wykonania drilla (firmware < 701 lub USB)

```
SetupDrill():
  1. ClearBall() (H\r), wait 200ms
  2. ClearBall() (H\r), wait 1000ms
  3. [fw < 701]: setBall(firstBall, force=true), wait 300ms, setBall(firstBall, force=true), wait 1500ms

RunDrill():
  loop (DrillRunning && count < Count):
    for each RobotBall in RobotBalls:
      setBall(ball, force=true)  → B komenda
      wait_till(now + WaitTime)
      ThrowBall()  → T\r, czeka na K
      count++

    if Delay > 0:
      setBall(firstBall)
      wait_till(now + Delay*1000)

  ClearBall()
```

### Sekwencja wykonania drilla (firmware >= 701, BLE)

```
SetupDrill():
  1-3. Identycznie, ale setBall() używa wTA+A zamiast B

RunDrill():
  for each RobotBall:
    setBall(ball, force=true)  → wTA + A komenda

  // Po ustawieniu WSZYSTKICH piłek:
  writeCommand($"END{Count:000}{random:000}{Delay*10:000}")

  // Czeka na N (DrillRunning = false gdy N odebrane)
```

Robot firmware >= 701 zarządza samodzielnie kolejnością i timingiem piłek po odebraniu END.

### Komenda END — szczegóły

```
END{count:000}{seed:000}{delay*10:000}\r
```

Przykład drilla: 50 piłek, delay 8 sekund, ziarno=127:
```
END050127080\r
```

Robot odpowiada `N` gdy drill się zakończy.

---

## Sekcja 9: Konfiguracja (ConfigurationService)

### Android SharedPreferences — wszystkie klucze

| Klucz | Typ | Default | Opis |
|-------|-----|---------|------|
| `HeightAdjustment` | int | 0 | Regulacja wysokości (przestarzałe?) |
| `OscillationAdjustment` | int | 0 | Regulacja oscylacji (przestarzałe?) |
| `RotationAdjustment` | int | 0 | Regulacja rotacji (przestarzałe?) |
| `IsCalibrated` | bool | false | Czy kalibracja była wykonana |
| `BallFeedOffset` | int | 15 | Offset podajnika piłek |
| `BallFeedMotor` | int | 10 | Prędkość silnika podajnika |
| `CurrentCount` | int | 60 | Aktualna liczba piłek w sesji |
| `SpeedCAL` | int | 0 | Offset kalibracji prędkości |
| `Generation` | int | 2 | Wersja robota (0=OriginalNewFW, 1=Original, 2=SecondRun) |
| `RotCAL` | int | 0 | Offset kalibracji rotacji |
| `OscCAL` | int | 0 | Offset kalibracji oscylacji |
| `HeightCAL` | int | 0 | Offset kalibracji wysokości |
| `IsLeftHanded` | bool | false | Tryb dla leworęcznych |
| `BallsPerMinute` | int | — | Piłki na minutę |
| `Language` | int | — | Język interfejsu |

### Jak przechowywane

Android: `PreferenceManager.GetDefaultSharedPreferences(context)` — plik XML w `shared_prefs/`.

Drille: pliki XML w `Environment.SpecialFolder.Personal` (app's documents folder).
- Nazwy plików: GUID + ".xml" (nie nazwa drilla!)
- Ulubione: podfolder `/Favorites/`
- Eksport: `/sdcard/Newgy3050Export/`

Konfiguracja kalibracji: `currentconfig.xml` przez `HashtablezBaseCase.SaveToDisk()`.

### Zasoby embedded XML

- `BallRangesV0.xml`, `BallRangesV1.xml`, `BallRangesV2.xml` — zakresy parametrów per RobotVersion
- `Resources.Training.*.xml` — treningi wbudowane

---

## Sekcja 10: Wersje firmware

### Odczyt wersji firmware

Komenda: `F\r` → robot odpowiada 3-cyfrową liczbą (np. "701").

Logika składania odpowiedzi (firmware = bajt po bajcie, dopóki długość < 3):
```csharp
if (Response != prevResponse) _receivedFirmware += Response;
prevResponse = _receivedFirmware;
if (_receivedFirmware.Length == 3)
    _installedFirmwareVersion = int.Parse(_receivedFirmware);
```

### Odczyt wersji robota

Komenda: `I\r` → robot odpowiada 1-cyfrową liczbą (0, 1, lub 2).

```csharp
public enum RobotVersion : byte
{
    OriginalNewFirmware = 0,  // wartość "0" z komendy I
    Original = 1,             // wartość "1"
    SecondRun = 2             // wartość "2"
}
```

W konfiguracji zapisane jako int ("Generation"): 0, 1 lub 2.
Domyślna wartość: 2 (SecondRun).

### Co zmienia się między wersjami firmware

| Warunek | Zachowanie |
|---------|-----------|
| `fw == 206` | Prędkość: `raw + 5` (zamiast `raw * 4.016`). Specjalna stara wersja. |
| `fw < 221` | SpeedCAL offset był dodawany do prędkości (dziś nie jest — `num3=0`) |
| `fw < 701 && fw > 0` | Komenda B (synchroniczna), pilot wyrzuca T po każdej piłce |
| `fw >= 701` | Komenda A + wTA (asynchroniczna), komenda END dla całego drilla |
| `USB_Mode == true` | Zawsze tryb < 701 (komenda B), niezależnie od firmware |

### Co zmienia się między RobotVersion

| Wersja | SpeedCAL baseline | TopMotorSpeed startowy (kalibracja) |
|--------|------------------|--------------------------------------|
| OriginalNewFirmware (0) | 170 | 77% |
| Original (1) | 170 | 77% |
| SecondRun (2) | 161 | 73% |

Rozkład numerów wersji wysyłanych przez `J` komendę:
```csharp
writeCommand($"J{Convert.ToInt32(robotVersion):00}");
// J00, J01, lub J02
```

### BallRanges per RobotVersion

- `BallRangesV0.xml` — dla OriginalNewFirmware (byte 0)
- `BallRangesV1.xml` — dla Original (byte 1)
- `BallRangesV2.xml` — dla SecondRun (byte 2)

Ładowane przez `BaseConfigurationService.SetupRanges(byte robotVersion)`.

---

## Podsumowanie kluczowych wzorów

```
TopMotor raw (%) = 28 + 182 * percent/100        (dla % > 0)
TopMotor raw (%) = -210 * |percent|/100           (dla % < 0 — odwrót)
Height raw       = 75 + round(135 * percent/100)
Oscillation raw  = 173 - round(46 * percent/100)  (praworęczny)
Rotation raw     = 150 + round(60 * degrees/90)   (zakres 90–210)

W komendzie B/A:
value  = TopMotor_raw * 4.016    (dla fw != 206)
value2 = Bottom_raw  * 4.016

SpeedCAL offset:
Gen2: TopMotor_raw_podczas_kalibracji - 161
Gen1: TopMotor_raw_podczas_kalibracji - 170
```
