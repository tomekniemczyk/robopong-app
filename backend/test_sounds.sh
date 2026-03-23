#!/bin/bash
# Test wszystkich dźwięków treningowych
DIR="$(dirname "$0")/sounds"

for f in beep beep_high tick countdown_beeps start end training_ended; do
    echo "▶ $f.wav"
    aplay -q "$DIR/$f.wav"
    sleep 0.5
done

echo "✅ Gotowe"
