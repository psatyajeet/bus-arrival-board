# Bench checklist

## Computer

- [ ] Run the fixture tests from the [README](README.md).
- [ ] Confirm both stops and route IDs against live 511 data during service.
- [ ] Stop the laptop’s watch loop before starting the board with the same key.

## MatrixPortal M4

- [ ] Bench test on a nonconductive surface. Disconnect power before mating
      or disconnecting the HUB75 panel or changing the power leads.
- [ ] Confirm the demo lights the full panel.
- [ ] Install CircuitPython and its matching libraries, local settings, and firmware.
- [ ] Check both directions and the next two arrivals against a trusted live source.
- [ ] Watch the first countdown tick down. Check that it changes to `DUE`
      near arrival and advances to the next prediction.
- [ ] Interrupt Wi-Fi after a successful fetch. Confirm cached countdowns
      continue. Restore Wi-Fi and verify that fresh arrivals return on a later poll.
- [ ] Power cycle the board using the kit’s power supply and confirm that live
      arrivals return without a computer connected.
- [ ] Let it run for a day before committing to an enclosure. Check temperatures,
      ventilation, cable strain relief, and readability from the normal viewing distance.
