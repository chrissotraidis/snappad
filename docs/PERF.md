# Timing and performance evidence

SnapPad preserves RT64's original-rate mode. The original US reference cadence
still requires a separate known-good reference capture before any optional
frame-rate enhancement can be considered.

## Reading a SnapPad cadence trace

Set `SNAPPAD_PERF_TRACE_PATH` to write one aggregate CSV row per second. The
trace is off during normal play. In addition to input, screen-update, and
successful-presentation rates, current builds record the number, mean length,
and worst length of successful-present intervals, plus counts above 50 ms and
100 ms. These interval fields distinguish a stable original-rate game from a
renderer that is missing its own pacing deadlines without logging or allocating
on RT64's present thread.

Simulator measurements are accepted only when SnapPad is the sole booted
Simulator and the Mac is not compiling, indexing, or running another sustained
CPU/GPU workload. A stable 60 Hz input/screen-update rate does not by itself
make a presentation trace valid when the host is heavily contended. Simulator
results remain diagnostic evidence, not a substitute for a signed-device run.

Summarize a whole trace or an explicit session-time band with the checked-in
standard-library tool:

```sh
python3 scripts/summarize_perf_trace.py path/to/trace.csv
python3 scripts/summarize_perf_trace.py path/to/trace.csv --from-ms 30000 --to-ms 90000
```

Long soaks pair that cadence CSV with `SNAPPAD_AUDIO_TRACE=1` runtime output
and a periodic resident-memory CSV containing
`session_ms,rss_kib,vsz_kib,cpu_percent`. Summarize the correlated audio and
memory interval with:

```sh
python3 scripts/summarize_soak_trace.py path/to/runtime.log path/to/memory.csv
python3 scripts/summarize_soak_trace.py path/to/runtime.log path/to/memory.csv --from-ms 300000 --to-ms 3600000
```

The soak summary reports callback-gap tails, queue/conversion errors, RSS range,
and a least-squares RSS slope. Exclude startup allocation when judging sustained
growth, and do not treat a bounded RSS plateau as a leak merely because its
final sample is higher than process launch.

## 2026-08-27 — 60-minute native macOS transition soak

One telemetry-enabled ARM64 macOS process ran continuously for 60 minutes and
completed 14 natural Beach-to-Oak's-Lab return cycles from the protected
19-species save. No Simulator was booted. The app then received an ordinary
quit event and logged `SDL_QUIT received`; both the primary save and its backup
retained their pre-run SHA-256 values.

Evidence is under `artifacts/2026-08-27/g7-macos-soak/`: `22-cadence.csv`,
`23-runtime.log`, and `24-memory.csv`. The startup-to-quit trace contains 3,599
complete one-second cadence buckets and 360 ten-second memory samples.

| Interval | Input | Screen updates | Presentations | RSS start/end | RSS range | RSS trend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Entire 60-minute mixed-state run | 59.954 Hz | 59.962 Hz | 27.172 Hz | 160,480 / 127,408 KiB | 111,408–175,072 KiB | -521 KiB/min |
| Final 30 minutes | 59.957 Hz | 59.957 Hz | 26.825 Hz | 128,224 / 127,408 KiB | 111,408–139,808 KiB | -134 KiB/min |
| Representative uninterrupted course band, 350–502 s | 60.030 Hz | 60.030 Hz | 30.005 Hz | — | — | — |

The final-half RSS slope is negative and the working set repeatedly returns
after course transitions, so this run shows no sustained resident-memory
growth. Across 1,799 audio records there were zero conversion errors, zero
queue errors, and no queue depth over 100 ms. The largest audio callback gap
was 187.646 ms. The cadence trace's largest successful-present interval was
311.902 ms; long-tail intervals cluster around course/menu transitions and the
few UI-control observations, while the uninterrupted gameplay band had no
present interval over 100 ms. This is native-macOS stability evidence, not a
physical-device thermal or scheduling result.

## 2026-08-27 — native macOS cadence probe

The ARM64 native app now supports opt-in one-second cadence samples through
`SNAPPAD_PERF_TRACE_PATH`. Each CSV row records wall interval, controller-input
polls, emulator screen updates, RT64-confirmed presentations, detected display
refresh, and window focus/minimize state. Normal launches do not create or log
this trace.

Evidence: `artifacts/2026-08-27/g7-frame-cadence.csv` from one native process
using the verified Pokémon Snap (USA) AOT core and a 60 Hz display.

| Observed state | Samples | Input polls/s | Screen updates/s | Presented frames/s |
| --- | ---: | ---: | ---: | ---: |
| Focused Tunnel gameplay band | 958 | approximately 60 | approximately 60 | mean 29.976, range 26.000–31.000 |
| Focused menu/transition band | 85 | approximately 60 | approximately 60 | mean 58.922, range 50.000–60.939 |
| Entire 1,051-second trace | 1,051 | mean 59.937 | mean 59.952 | mean 32.413 |

Interpretation: the current native build keeps simulation and controller
sampling at about 60 Hz while ordinary Tunnel gameplay presents at about 30
fps; menus and some transitions present near 60 fps. Scripted input durations
must therefore use the 60 Hz poll counter, not visible-frame counts. This is a
measurement of SnapPad's current build, not yet proof that it matches original
hardware.

The successful hidden-path run in
`artifacts/2026-08-27/g46-frame-cadence.csv` independently reproduced the same
cadence while exercising the real pester collision and reveal cutscene:

| Observed state | Samples | Input polls/s | Screen updates/s | Presented frames/s |
| --- | ---: | ---: | ---: | ---: |
| Focused gameplay band | 202 | mean 59.890 | mean 59.890 | mean 29.925, range 25.819–32.869 |
| Focused menu/transition band | 29 | mean 59.010 | mean 59.935 | mean 59.764, range 54.618–61.815 |
| Entire focused trace | 231 | mean 59.780 | mean 59.896 | mean 33.671 |

## 2026-08-27 — production iPad Simulator cadence probe

The production ARM64 iOS Simulator bundle was run on one iPad Pro 11-inch (M5)
Simulator with iOS 26.5 and a 60 Hz simulated display. This was the generated
Pokémon Snap AOT core, not the ROM-free shell preview. The observed path covered
fresh name entry, Oak's Lab, Beach course selection, live Beach rendering, a
Z-held/A-shutter photograph, explicit FlashRAM save, process termination, and
Continue restoration.

Evidence: `artifacts/2026-08-27/g9-ipad/11-ipad-frame-cadence.csv`. The table
uses the final 80 focused one-second samples from the restored Beach run.

| Observed state | Samples | Input polls/s | Screen updates/s | Presented frames/s |
| --- | ---: | ---: | ---: | ---: |
| Focused iPad Beach gameplay | 80 | mean 59.893 | mean 59.893 | mean 29.928, range 25.922–31.000 |

The production executable used for this run hashes to
`242eee67797ea09f635d2fd80e9b503b023c348552b75f6aacd37003d53ca7e9`.
These numbers establish Simulator cadence only; they do not predict physical
iPad heat, battery, memory pressure, audio routing, touch feel, or sustained
device performance.

## 2026-08-27 — unattended iPhone Simulator cadence probe

After a user-visible report of intermittent phone Simulator drops, one iPhone
17 Pro Simulator on iOS 26.5 was left untouched during live Beach gameplay.
The final 45 complete one-second intervals exclude the screenshots and UI
inspection used to enter the course.

Evidence:
`artifacts/2026-08-27/g9-iphone-fresh/02-iphone-unattended-cadence.csv`
and the matching production log. The sampled executable preceded only a final
B-button hold-preservation refinement; A/Start pulse behavior and runtime
cadence code are unchanged in the final audited bundle.

| Observed state | Samples | Input polls/s | Screen updates/s | Presented frames/s |
| --- | ---: | ---: | ---: | ---: |
| Unattended iPhone Beach gameplay | 45 | mean 59.918, range 55.888–60.878 | mean 59.918, range 55.888–60.878 | mean 29.937, range 27.944–31.000 |

Two intervals were below 29 presented fps and one interval was below 58 input
polls/s. The lowest bucket recorded 56 input polls, 56 screen updates, and 28
presentations; the audio trace over the same interval recorded 114 callbacks
and a 101.385 ms maximum callback gap. All four signals recovered in the next
bucket. This is a real short whole-process stall in the Simulator trace, not a
sustained renderer-only slowdown. Its cause and physical-device relevance are
not yet proven.

## 2026-08-27 — production telemetry overhead removed and re-probed

The audio discontinuity probe was still active in ordinary production runs. It
scanned every converted output frame and wrote a large stderr record every two
seconds. That work is now disabled unless `SNAPPAD_AUDIO_TRACE=1` is explicitly
set. `SNAPPAD_PERF_TRACE_PATH` remains independently available, so frame cadence
can be measured without turning the expensive audio analysis back on.

The rebuilt production app was then run unattended on the same iPhone 17 Pro
Simulator. The 48 contiguous gameplay-like one-second buckets before the
end-of-course transition measured:

| Observed state | Samples | Input polls/s | Screen updates/s | Presented frames/s |
| --- | ---: | ---: | ---: | ---: |
| Audio telemetry gated, iPhone Beach | 48 | mean 59.963, range 56.830–61.000 | mean 59.963, range 56.830–61.569 | mean 29.971, range 26.919–31.841 |

Evidence:
`artifacts/2026-08-27/g9-iphone-fresh/08-iphone-audio-gated-cadence.csv`
and `09-iphone-audio-gated-production.log`. The log contains no periodic
`[audio ...]` records. The rebuilt Simulator executable hashes to
`c974d2ca99c1bacd528ab24a14e07bc3665ff8ecbe2035cf14f0c89d935f8c2a`.

Removing the production-only overhead is worthwhile, but it did not eliminate
the intermittent Simulator stall: six buckets presented below 29 fps and one
bucket sampled input below 58 Hz, all recovering immediately. The evidence
still points to a short whole-process scheduling interruption rather than a
sustained renderer bottleneck. Physical-device relevance remains unproven.

## 2026-08-27 — successful-present intervals and matched resolution comparison

The cadence trace now measures intervals at RT64's actual successful
`swapChain->present` boundary. A first 2x run was rejected because an unrelated
ten-worker compile drove host load above 100; its retained files are explicitly
labeled invalid and are not performance evidence.

After that compile ended, the same Beach opening was run twice on the only
booted iPhone 17 Pro Simulator: fixed 2x and Auto, which the renderer confirmed
as 6x / 1920x1440. Both 45-second bands began approximately two seconds after
the live course view appeared. The same unrelated emulator process remained at
approximately one full CPU core during both bands, making these useful as a
controlled resolution comparison but not as absolute idle-host acceptance.

| Setting | Samples | Input polls/s | Screen updates/s | Presentations/s | Mean present interval | Maximum | >50 ms | >100 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed 2x / 640x480 | 45 | 60.020 | 60.042 | 26.956 | 37.122 ms | 82.111 ms | 143 / 1218 (11.741%) | 0 |
| Auto 6x / 1920x1440 | 45 | 59.915 | 59.915 | 28.043 | 35.672 ms | 130.620 ms | 104 / 1267 (8.208%) | 2 / 1267 (0.158%) |

Evidence:
`artifacts/2026-08-27/g10-iphone-present-pacing/07-2x-steady-single-core-contention.csv`
and `09-auto-6x-steady-single-core-contention.csv`. The trace SHA-256 values are
`0a45e189d56ab891ed27a3f95bdf990121d3bb79012097ab6570cad87f1fd8dd`
and `5732a081eaa01fb00bc5c836c7d389c1bbae26bf13c447819953ec9edee49513`.

Interpretation: lowering the internal resolution did not improve this matched
Simulator segment; Auto was slightly faster on aggregate, within ordinary
run-to-run variation, while both kept the native input and screen bridge at 60
Hz. The observed phone Simulator drops therefore are not evidence that Auto's
6x target is the bottleneck, and SnapPad keeps PaperPad's Auto default. The
rare interval tail and physical-device relevance remain open; do not infer an
enhanced-framerate requirement from this diagnostic comparison.

## 2026-08-27 — successful-present intervals on native macOS Beach

The telemetry-current ARM64 macOS app completed another authentic Beach course
band while the input-only photo harness exercised the stock detector, shutter,
course, and Camera Check transition paths. The 199 complete buckets from
50.450 through 249.302 seconds exclude application startup and title/lab entry:

| Observed state | Samples | Input polls/s | Screen updates/s | Presentations/s | Mean present interval | Maximum | >50 ms | >100 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ARM64 macOS Beach course | 199 | 59.998 | 59.998 | 29.971 | 33.380 ms | 97.077 ms | 9 / 5987 (0.150%) | 0 |

Evidence:
`artifacts/2026-08-27/g6-stage2-unlock/06-beach-perf.csv` and
`04-beach-gameplay.log`. This is a roughly 200-second course observation, not
the required 60-minute soak. An unrelated emulator remained active on one host
CPU core, so the result establishes stable application cadence under that
known condition rather than an idle-host performance ceiling.

Open timing work:

- record the same counters in title, lab, every course, Camera Check, gallery,
  credits, iPhone Simulator, physical candidates, and a known-good original US
  reference run;
- extend the completed native soak with photo-review and additional-course
  transition coverage;
- add a physical-device trace to distinguish Simulator scheduling stalls from
  application or renderer pacing defects.
