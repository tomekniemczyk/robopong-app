## Communication

Transport-level communication standards for BLE and USB connections to the Robopong 3050XL.

### Transport Terminators

BLE commands terminate with `\r` (carriage return). USB commands terminate with `\r\n` (CR+LF). These must never be confused -- mixing terminators causes command parsing failures on the robot.

### USB Initialization

USB init sends byte `0x5A` twice at 9600 baud. It is NOT the string `Z\r\n`. The raw byte value must be sent without any text encoding or line terminator.

### BLE Payload Limit

Maximum 20 bytes per BLE write. Longer commands must be split into 2 parts with 200ms delay between them.

### Firmware Command Selection

Firmware >= 701: use command `A` with `wTA` prefix instead of command `B`. Check firmware version after connection handshake to determine which command format to use.
