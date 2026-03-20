# Reverse Engineering — Newgy Robopong 3050XL Protocol

Źródło: zdekompilowany Windows MSI (WindowsApp_3_22_2020_954p.msi)
Narzędzie: ILSpy (.NET assembly decompiler)

---

## Interfejsy komunikacji

### 1. BLE (Bluetooth Low Energy)
- Chip: Microchip RN4870 (MLDP profile)
- Service UUID: `00035b03-58e6-07dd-021a-08123a000300`
- Data char (write): `...0301`
- Control char: `...03ff`
- Terminator: `\r` (CR only)
- Max payload: 20 bajtów, przy dłuższych: split z 200ms delay

### 2. USB (FTDI UART bridge)
- Chip: FTDI (FTD2XX library)
- Device description: `NEWGY3050`
- Na Linuksie: `/dev/ttyUSB0` lub `/dev/ttyUSB1`
- Terminator: `\r\n` (CRLF)

#### Parametry portu USB:
- Baudrate: **115200** (docelowy)
- Databits: 8
- Parity: none (0)
- Stopbits: 1 (0)
- Flow control: none
- RTS: true, DTR: true
- Read timeout: 1000ms, Write timeout: 0

#### Sekwencja połączenia USB:
1. Otwórz @ **9600 baud**
2. Wyślij `Z\n` (bajt 90 + 10) x2 z 250ms opóźnieniem
3. Zamknij port
4. Otwórz @ **115200 baud**
5. Wyślij `Z\r\n`, czekaj na odpowiedź `K`/`N`/`M` (timeout 60s, retry co 3s)
6. Wyślij `H\r\n` (stop)
7. Połączenie gotowe

---

## Komendy ASCII (wspólne BLE i USB, różni terminator)

### Podstawowe
| Komenda | Opis | Odpowiedź |
|---------|------|-----------|
| `Z` | Ping/połącz | `K`, `N` lub `M` |
| `H` | Stop (zatrzymaj silniki) | `K` |
| `T` | Throw (wyrzuć piłkę) | `K`, `N` lub `M` |
| `F` | Firmware version (3 bajty) | string wersji |
| `I` | Robot version | string |
| `V` | Begin calibration (wywołaj 2x) | — |

### Konfiguracja piłki
```
B{TopSign}{TopSpeed:3}{BottomSign}{BottomSpeed:3}{Oscillation:3}{Height:3}{Rotation:3}{LEDs:1}
```

Pola:
- `TopSign`: `0` (dodatni) / `1` (ujemny)
- `TopSpeed`: 3 cyfry, wartość bezwzględna
- `BottomSign`: `0` / `1`
- `BottomSpeed`: 3 cyfry
- `Oscillation`: 000–255 (128 = środek, lewo/prawo)
- `Height`: 000–255 (128 = środek, góra/dół)
- `Rotation`: 000–255 (128 = środek, obrót głowicy)
- `LEDs`: 0–8 (wskaźnik rodzaju spinu)

Przeliczanie prędkości silnika (firmware >= 221):
```python
speed = motor_speed * 4.016 + speed_cal_offset
```

Firmware < 221:
```python
speed = motor_speed + 5
```

Przykład: `B0123004561281281280\r\n`

### Kalibracja i regulacja (advanced)
| Komenda | Format | Opis |
|---------|--------|------|
| `U{v}` | `U128` | Ustaw wysokość głowicy |
| `O{v}` | `O064` | Ustaw oscylację (bez lewej ręki) |
| `R{v}` | `R200` | Ustaw rotację |
| `Q{v:3}` | `Q025` | Speed CAL offset |
| `S{v}` | `S1` | Ustaw wersję robota |

### Odpowiedzi robota
| Odpowiedź | Znaczenie |
|-----------|-----------|
| `K` | OK / sukces |
| `N` | Brak piłki |
| `M` | ? (akceptowane jako sukces) |

---

## USB przez pyserial (Linux)

```python
import serial

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=115200,
    bytesize=8,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    rtscts=False,
    dsrdtr=False
)
ser.rts = True
ser.dtr = True

def send_cmd(cmd: str):
    ser.write((cmd + '\r\n').encode())
    return ser.read(1).decode()

# Inicjalizacja
send_cmd('Z')
send_cmd('H')

# Ustawienie piłki i rzut
send_cmd('B00150015012812812 80')
send_cmd('T')
```

Identyfikacja urządzenia FTDI:
```bash
lsusb | grep FTDI       # VID:PID zwykle 0403:6001
dmesg | grep ttyUSB     # numer portu
```
