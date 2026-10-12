# Rear motion investigation

The 36-segment arcade renderer only fed the on-screen preview. Hardware output
called `render_backzone_effect_v2`, averaged the lit segments (or chose white),
then streamed Always On (command 1). Spatial positions and the second colour
were discarded.

The local official binaries were inspected through the existing decompilation
scripts in the parent directory. `ControlCenter.dll`'s `Page2.setComData` sends
command 5 for Game Loop and 6 for Game Cover, including primary RGB and secondary
RGB in the four-byte auxiliary payload. `BydCentral.Core.dll`'s
`Back_light_buf.setBackLightWithAudio` copies that payload to fd1–fd4.
`SerPort.sendCom` marshals the parameter struct, rather than uploading a pixel
array. The official `StartCoverAnimation` routine draws its UI bitmap; it does
not transmit individual LED positions.

## Implemented fallback

Arcade modes now select Game Cover (201–203, 207, 210) or Game Loop
(204–206, 208–209), preserving both user colours. The worker lets firmware run
without continual restarts and retries failed updates. Power rules still win.
The UI explicitly labels arcade drawings as concept previews and names the
actual hardware fallback. The powered-off preview also now initializes its
segment colours, avoiding an unbound local variable and stale display.

This restores a verified command path for native spatial motion. It does NOT
implement the ten independent per-pixel choreographies. No arbitrary per-LED
upload command was established from the inspected OEM code. Physical movement,
colour order and timing require observation on the laptop; mock tests cannot
confirm the controller's visible output.

## Validation

12 new regression cases pass: all ten mappings retain separate colours, power
rules turn the strip off, and worker updates do not continually restart motion
and retry failures. Combined lighting/control tests: 56 passed, 3 failed in
unmodified areas (two AC profile mocks lack `_about_refresh_live`; the Tk layout
test failed loading `menu.tcl`).
