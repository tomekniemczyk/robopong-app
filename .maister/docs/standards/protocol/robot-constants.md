## Robot Constants

Hardware constants and formulas for the Donic Robopong 3050XL robot. These values are derived from reverse engineering and live testing.

### Head Center Position

Robot head center is 150 for oscillation, rotation, and height. NOT 128.

- Oscillation: range 127-173, center 150
- Height: range 75-210
- Rotation: range 90-210, center 150

### Motor Speed Formula

Motor speed PWM value in B/A command: `raw * 4.016`. This converts the user-facing speed value to the hardware PWM value.

### LED Spin Indicator

LED spin indicator formula: `ratio = |top - bot| / 360`, values 0-8. Displays spin intensity based on the differential between top and bottom motor speeds.
