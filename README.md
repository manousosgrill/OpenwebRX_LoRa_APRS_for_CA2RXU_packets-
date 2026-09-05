# OpenwebRX_LoRa_APRS_for_CA2RXU_packets-


# OpenWebRX+ / LoRa APRS — Technical Work Report

**Date:** 5 September 2026

## 1. Objective

The objective was to improve the OpenWebRX+ LoRa APRS decoder so that it correctly handles CA2RXU LoRa APRS packets while retaining compatibility with standard APRS uncompressed position packets.

The work also removed unwanted CA2RXU application/control data from the displayed APRS comment.

## 2. CA2RXU LoRa APRS Format

The CA2RXU LoRa APRS receiver can transmit a Base91-encoded position format that differs from the conventional APRS compressed-position format.

Example received packet:

```text
=L<Rk8TU&;a !GLoRa APRS Reciever 433.775 Mhz powered by http://sv9tnf.ham.gd|'K!=#7|
```

The important Base91 position section is:

```text
L<Rk8TU&a
```

## 3. CA2RXU Base91 Position Decoding

The APRS parser was modified in:

```text
/usr/lib/python3/dist-packages/owrx/aprs/__init__.py
```

inside the `parseRegularAprsData()` function.

CA2RXU coordinates are decoded using the APRS Base91 coordinate formulas:

```text
lat = 90 - decodeBase91(latitude_data) / 380926
lon = -180 + decodeBase91(longitude_data) / 190463
```

The resulting position was verified as approximately:

* Latitude: **35.5040008°**
* Longitude: **24.0460037°**
* Symbol: **a**
* Symbol table: **L**

## 4. Course, Speed and Altitude

The CA2RXU-specific bytes following the symbol were also handled.

Depending on the packet, these bytes can represent:

* Course
* Speed
* Altitude
* Standing/zero-speed updates

The latest verified packet decoded as:

* Course: **0**
* Speed: **0.0**
* Altitude: **0**

## 5. Removal of the Unwanted CA2RXU Tail

CA2RXU packets contained an additional application/control tail after the human-readable comment, for example:

```text
|'m!=#8|
```

and:

```text
|'K!=#7|
```

The parser was modified so that when a pipe character appears in the comment, the comment is truncated at the first pipe:

```python
if "|" in comment:
    comment = comment.split("|", 1)[0]
```

This preserves the useful comment:

```text
LoRa APRS Reciever 433.775 Mhz powered by http://sv9tnf.ham.gd
```

while removing the unwanted control data.

## 6. Standard Uncompressed APRS Problem

A second packet format was subsequently received:

```text
!3530.24NL02402.76Ea000/000 LoRa APRS Reciever 433.775 Mhz powered by http://sv9tnf.ham.gd
```

This is a normal, uncompressed APRS position.

Its fields are:

```text
3530.24N     Latitude
L            Symbol table
02402.76E    Longitude
a            Symbol
000/000      Course/Speed
```

The correct decoded position is approximately:

```text
35.504° N
24.046° E
```

## 7. Why the Normal Packet Was Initially Decoded Incorrectly

The newly added CA2RXU detector was initially too broad.

It tested whether the position characters were valid Base91 characters. Characters from a normal APRS latitude/longitude string can also satisfy that test.

As a result, the normal APRS packet was incorrectly interpreted as a CA2RXU Base91 packet.

The incorrect result was approximately:

```text
Latitude:  50.03986°
Longitude: -111.89132°
```

with an incorrect symbol.

## 8. Final Compatibility Fix

The CA2RXU detector was made more specific by excluding the normal uncompressed APRS format.

The key additional condition is:

```python
and information[4] != "."
```

A standard APRS latitude such as:

```text
3530.24N
```

contains a decimal point at position 4.

Therefore the normal APRS packet is allowed to continue to the standard uncompressed APRS decoder instead of being intercepted by the CA2RXU Base91 decoder.

This allows both formats to work correctly:

```text
CA2RXU:
=L<Rk8TU&;a !G...

Normal APRS:
!3530.24NL02402.76Ea...
```

## 9. Investigation of `owrx/lora.py`

The LoRa input processing code was inspected in:

```text
/usr/lib/python3/dist-packages/owrx/lora.py
```

The relevant code extracts the APRS information using:

```python
info = matches.group(6)
```

and passes it to the APRS parser using:

```python
"data": info.encode("utf-8")
```

Temporary logging confirmed that the raw received packet was correctly formed:

```text
SV9TNF-10>APLG01,WIDE1-1:!3530.24NL02402.76Ea000/000 ...
```

and that the APRS information passed to the parser was:

```text
!3530.24NL02402.76Ea000/000 ...
```

Therefore the problem was in the APRS format detection inside `parseRegularAprsData()`, not in `lora.py`.

## 10. Final Verification

The final CA2RXU test produced:

```text
Source:       SV9TNF-10
Destination:  APLRG1
Path:         WIDE1-1

Latitude:     35.504000777°
Longitude:    24.046003686°

Symbol:       a
Symbol table: L

Type:         compressed (CA2RXU Base91 format)

Course:       0
Speed:        0.0
Altitude:     0

Comment:
LoRa APRS Reciever 433.775 Mhz powered by http://sv9tnf.ham.gd
```

## 11. Files Involved

### Primary modified file

```text
/usr/lib/python3/dist-packages/owrx/aprs/__init__.py
```

The main modification is inside:

```text
parseRegularAprsData()
```

### Temporary debugging file

Temporary debugging was added to:

```text
/usr/lib/python3/dist-packages/owrx/lora.py
```

The temporary line was:

```python
logger.warning("LORA DEBUG BEFORE REGEX: %r", payload)
```

This debugging line can now be removed.

## 12. Current Status

The following items have been successfully completed:

* **CA2RXU Base91 position decoding — WORKING**
* **Standard APRS uncompressed position decoding — WORKING**
* **Correct Chania-area coordinates — VERIFIED**
* **Correct APRS symbol and symbol table — VERIFIED**
* **CA2RXU course/speed/altitude handling — WORKING**
* **CA2RXU unwanted `|...|` tail removal — WORKING**
* **Human-readable APRS comment retained — WORKING**
* **LoRa APRS packet extraction in `lora.py` — VERIFIED**
* **APRS-IS forwarding — VERIFIED in OpenWebRX logs**

## 13. Final Result

The OpenWebRX+ LoRa APRS decoder now supports both the CA2RXU Base91 position format and conventional APRS uncompressed positions without confusing the two formats.

The useful CA2RXU comment is preserved while the unwanted trailing application/control data is removed.

The final implementation therefore provides correct position decoding for the received `SV9TNF-10` packets while maintaining normal APRS compatibility.

