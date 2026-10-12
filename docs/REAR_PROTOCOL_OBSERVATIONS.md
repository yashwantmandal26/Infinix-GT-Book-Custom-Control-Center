# Live rear-controller investigation — 2026-10-12

Hardware: Infinix GL613, ACPI PNP0501/SERIALIOUART1 on COM1,
115200 baud, 8N1. Official installed application: 1.2.4.

These are observations, not a verified arbitrary-LED protocol. The arcade
firmware fallback in the previous build does not implement custom choreography.

| Test | Received bytes | Physical observation reported by user |
| --- | --- | --- |
| OEM enum ReadBuf (0x90), zero checksum and summed checksum | `34 0e 90 d2` for both | No LED-state data returned |
| Mode 1, green | `34 0e 81 c3` | Green |
| OEM enum Back_Light (0x0F), red | `34 0e 8f d1` | Stayed green; no visible change |
| Mode 1, primary blue; r2/g2/b2 set to red; l1/l2 both 22 | `34 0e 81 c3` | Entire bar blue, no separate red section |
| Mode 3, primary green, fd1=4, fd2–fd4=0 | `34 0e 83 c5` | Strip went off |
| Mode 3, primary green, fd1=fd4=32, fd2=fd3=0 | See rear_rhythm_level32_probe.json | Still off |
| Mode 3, green, fd1=fd4=128, repeated at 20 Hz for 60 seconds | `34 0e 83 c5`; 1181 frames sent | Entire bar green during streaming |
| Mode 3, green, fd1=fd4=4, repeated at 20 Hz | `34 0e 83 c5` | Only some LEDs / centre green |
| Mode 3, green, fd1=12, fd2=fd3=fd4=0, repeated at 20 Hz | `34 0e 83 c5` | Symmetric green coverage from centre towards both sides |
| Mode 3, green primary, red r2/g2/b2, both levels=6, l1=l2=22, repeated | `34 0e 83 c5` | Only green, full bar; two end lights flicker. User notes flicker also occurred in earlier tests. |

The later report qualifies earlier spatial observations: endpoint flicker was
present, so a stable pixel count/coverage mapping has NOT been established.
No tested path produced independently selected red and green segments. The
diagnostic stream was stopped and static blue restored. No custom arcade
hardware implementation has been verified; the earlier native fallback remains
a fallback, not the requested fix.

The fd1-only test still lights both sides. Therefore fd1/fd4 cannot be assumed
to be independent left/right lengths. The inspected OEM code uses fd1 for its
rhythm preview and fd4 for its jump preview. Low-level continuous rhythm output
confirms control of symmetric coverage, not arbitrary pixel addressing.

Single-shot audio tests are inconclusive for sustained output: continuous input
at level 128 produced green. This does not establish whether low levels expose
spatial coverage, whether the controller times out, or whether threshold/level
differences account for the earlier off observations. A lower-level continuous
test is required to separate these variables.

The four-byte replies are consistent with a header, command OR 0x80, and a
sum byte. They are not evidence that every parameter was implemented or that
individual LEDs were addressed. The second RGB fields do not independently
control a section in the tested mode-1 configuration. The name Back_Light
does not establish the behaviour of command 0x0F.

The OEM AudioCapturer.DataTimer_Tick writes an amplitude to MaxVolumn[0] and
MaxVolumn[3]. Page2.setComData supplies those four bytes for modes 3/4, whereas
modes 5/6 supply the secondary colour/level. Thus audio parameters must not be
interpreted as secondary RGB. The fixed-amplitude rhythm test checks whether
this known parameter gives useful spatial extent control. Even a positive
result would not prove arbitrary positions or simultaneous independent colours.

Raw request/reply records remain in the original development workspace; live
probe programs and session logs are not shipped in this sharing package.
No firmware was flashed and no Save command was sent.

External implementations inspected (both expose mode packets, no per-LED API):

- https://github.com/sanidhyy/infinix-gtbook-mecha-bar/blob/main/infinix_mecha_rgb.py
- https://github.com/Tejeshwar2006/infinix-gtbook-control-centre-linux-version/blob/main/app/hardware/serial_backstrip.py
