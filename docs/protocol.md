# Protokół komunikacji — Donic Robopong 3050XL

> Odkryty przez reverse engineering APK Newgy 3.0.5 (com.newgy.newgyapp)

## Transport

- **Technologia:** Bluetooth Low Energy (BLE)
- **Profil:** MLDP — Microchip Low-energy Data Profile (emulacja UART przez BLE)
- **Moduł BT w robocie:** prawdopodobnie Microchip RN4870 lub RN4020

## UUIDs (BLE GATT)

| Rola | UUID |
|------|------|
| Serwis MLDP | `00035b03-58e6-07dd-021a-08123a000300` |
| Charakterystyka danych (write/notify) | `00035b03-58e6-07dd-021a-08123a000301` |
| Charakterystyka kontrolna | `00035b03-58e6-07dd-021a-08123a0003ff` |
| CCCD (notification descriptor) | `00002902-0000-1000-8000-00805f9b34fb` |

## Parametry połączenia

- Komendy to **ciągi ASCII** zakończone `\r`
- Maks. 20 bajtów per zapis BLE — dłuższe komendy dzielone na 2 części z 200ms opóźnieniem
- Robot skanowany po nazwie urządzenia BLE (scan callback)

## Sekwencja inicjalizacji (połączenie)

```
→ Z\r        # ping/reset (wysyłane 3×)
→ H\r        # stop / clear ball
← odpowiedź  # robot potwierdza obecność
→ Z\r        # kolejne pingi co 1s do otrzymania odpowiedzi (timeout 20s)
```

Po połączeniu:
```
→ F\r        # zapytanie o wersję firmware (odpowiedź: liczba np. "701")
→ Jxx\r      # ustawienie wersji robota (J01 = Original, J02 = Gen2)
```

## Komendy sterowania

### H — zatrzymaj / wyczyść piłkę
```
H\r
```

### T — wyrzuć piłkę
```
T\r
```

### B — ustaw piłkę (stary firmware < 701 lub tryb USB)
```
B<dir_top><speed_top><dir_bot><speed_bot><oscillation><height><rotation><leds>\r
```
| Pole | Format | Opis |
|------|--------|------|
| dir_top | `0`/`1` | Kierunek górnego silnika (0=forward, 1=reverse) |
| speed_top | `000`–`999` | Prędkość górnego silnika (speed × 4.016) |
| dir_bot | `0`/`1` | Kierunek dolnego silnika |
| speed_bot | `000`–`999` | Prędkość dolnego silnika (speed × 4.016) |
| oscillation | `000`–`255` | Oscylacja głowicy (128 = środek) |
| height | `000`–`255` | Wysokość głowicy (128 = środek) |
| rotation | `000`–`255` | Obrót głowicy (128 = środek) |
| leds | `0`–`9` | Wskaźniki LED spinu |

Przykład: `B0200020001280128012800\r`

### A — ustaw piłkę (nowy firmware ≥ 701, tryb BLE)
Identyczny format jak `B`, ale poprzedzony komendą `wTA`:
```
wTA<wait_time/10>\r   # ustaw czas oczekiwania (np. wTA015 = 150ms)
A<...>                # jak B — parametry piłki
```

### W — ustaw czas opóźnienia (adjustment)
```
W<milliseconds>\r     # np. W000
```

### Y — piłka losowa (część 1)
```
Y<n_low><n_high><n_type><top_low><top_high><top_type><bot_low><bot_high><bot_type><h_low><h_high>\r
```

### P — piłka losowa (część 2)
```
P<h_type><osc_low><osc_high><osc_type><rot_low><rot_high><rot_type><wait_high><wait_low><wait_type><dir...>\r
```

### F — zapytaj o wersję firmware
```
F\r
← <numer>   # np. "701"
```

### J — ustaw wersję robota
```
J<version>\r   # J01 = Original, J02 = Gen2
```

### X — wejście w tryb bootloadera
```
X\r
X\r
```

### Z — ping / reset
```
Z\r
```

## Przeliczanie prędkości silników

```
raw_speed = motor_speed × 4.016
```

Zakres `motor_speed`: 0–99 (wartości wyższe obcinane)
Kierunek: wartość ujemna → dir=1 (rewers)

## Głowica — pozycje (HeadPosition)

| Parametr | Środek | Min | Max |
|----------|--------|-----|-----|
| Oscillation | 128 | 0 | 255 |
| Height | 128 | 0 | 255 |
| Rotation | 128 | 0 | 255 |

## Klasy w aplikacji Newgy (Xamarin .NET)

| Klasa | Rola |
|-------|------|
| `BluetoothService` | scan BLE, connect, write via MLDP |
| `BluetoothLeService` | Android BLE GATT service |
| `BGattCallback` | obsługa zdarzeń GATT |
| `RobotInterface` | Android implementacja IRobotInterface |
| `BaseRobotService` | logika biznesowa — setBall, runDrill, ThrowBall |
| `BallFactory` | konwersja InterfaceBall → RobotBall |

## Dalsze kroki RE

1. Podłączyć się do robota i zaobserwować nazwę BLE (nRF Connect)
2. Zweryfikować UUIDs serwisu MLDP
3. Sniff HCI log z Androida podczas sterowania przez Newgy
