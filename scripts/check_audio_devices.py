#!/usr/bin/env python3
"""List audio devices and verify BlackHole is available."""

import sounddevice as sd


def main():
    print("=== Available Audio Devices ===\n")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        direction = []
        if dev["max_input_channels"] > 0:
            direction.append("IN")
        if dev["max_output_channels"] > 0:
            direction.append("OUT")
        print(f"  [{i}] {dev['name']} ({'/'.join(direction)}) - {int(dev['default_samplerate'])}Hz")

    print()

    # Check for BlackHole
    blackhole_found = False
    for i, dev in enumerate(devices):
        if "blackhole" in dev["name"].lower() and dev["max_input_channels"] > 0:
            blackhole_found = True
            print(f"✅ BlackHole found: [{i}] {dev['name']}")

    if not blackhole_found:
        print("❌ BlackHole not found as input device.")
        print()
        print("Setup instructions:")
        print("  1. Install BlackHole: brew install blackhole-2ch")
        print("  2. Open 'Audio MIDI Setup' (audio MIDI設定)")
        print("  3. Click '+' -> 'Create Multi-Output Device' (複数出力デバイスを作成)")
        print("  4. Check both your speakers/headphones AND 'BlackHole 2ch'")
        print("  5. Set this multi-output device as your system output")

    # Check default mic
    default_input = sd.query_devices(kind="input")
    print(f"\n🎙️  Default input: {default_input['name']}")


if __name__ == "__main__":
    main()
