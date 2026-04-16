## Connection Sequences

Standard sequences for robot connection, calibration, and health monitoring.

### Connection Handshake

Handshake sequence after establishing transport:

1. `Z` -- ping/reset (sent 3 times)
2. `H` -- stop motors
3. `F` -- firmware version query
4. `I` -- unknown (required by protocol)
5. `J02` -- set Gen2 mode

Health monitor pings every 10 seconds to detect disconnection.

### Calibration Throw Sequence

Calibration throw sequence with required timing:

1. `set_ball` -- configure ball parameters
2. Wait 300ms
3. `T` -- throw single ball
4. Wait 1500ms
5. `H` -- stop motors

Motors MUST stop after calibration throw. No auto motor warmup when entering calibration mode.

### Per-Device Calibration

Calibration is stored per-device in the SQLite `calibration` table, keyed by BLE/USB address (PK). A row with empty address (`addr=''`) serves as the default fallback when no device-specific entry exists. The robot firmware does not persist calibration -- it MUST be sent after every connection.

Default calibration values (Android Gen2):

- top=160, bot=0
- osc=150, h=183, rot=150
- wait=1000
