# Lab 04 Validation — BJT Amplifier Simulator v1

Date: 2026-11-24  
Environment: Windows (win32), repo `C:\Users\b6648794\Desktop\Gitlab`, Python venv `.venv`, pytest 8.x  
ngspice: **NOT INSTALLED / NOT FOUND in PATH** (`where ngspice` returned not found)  
BJT SPICE model: `Q2N3904_GENERIC` (generic approximation in `bjt_bias/spice_engine.py`; replace with instructor starter model before official validation)

## Automated checks run

| Check | Method | Result | Evidence |
|---|---|---|---|
| Unit/integration tests | `.venv\Scripts\python.exe -m pytest bjt_bias\tests -q` | PASS | 52 passed, 0 failed |
| SPICE missing-engine behavior | Flask test client + mock `ngspice_available=False` | PASS | `test_spice_engine.py::TestAppSpiceIntegration::test_spice_run_missing_ngspice_shows_error_not_success` |
| SPICE result rendering (mocked data) | Flask test client + mock `run_analysis` | PASS | `test_spice_engine.py::TestAppSpiceIntegration::test_spice_result_rendered_from_mock` |

## B1–B8 Browser/Simulation Acceptance

| Case | Method | Input | Expected/Reference | Observed | Evidence | Status |
|---|---|---|---|---|---|---|
| B1 · Regression | Flask test client / existing pytest | Divider: VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, beta=100, VBE=0.7 | IC 1.22986 mA, VCE 8.05216 V (Lab 2/3 reference) | Matches in `test_app.py::test_handout_sample_renders_in_milliamps` and route checks | pytest pass | PASS (test client) |
| B2 · DC SPICE | NOT RUN - real ngspice unavailable | CE reference, Run DC | VB/VE/VC/VCE/IC from ngspice output with model/run status | — | `where ngspice` not found | NOT RUN |
| B3 · Change RE | NOT RUN - real ngspice unavailable | Change RE only, rerun | Operating point changes from real simulation | — | ngspice missing | NOT RUN |
| B4 · AC | NOT RUN - real ngspice unavailable | Run AC | Bode magnitude/phase with units from real run | — | ngspice missing | NOT RUN |
| B5 · Transient | NOT RUN - real ngspice unavailable | 10mVpk, 1kHz | Vin/Vout vs time, phase inversion visible | — | ngspice missing | NOT RUN |
| B6 · Change Source | NOT RUN - real ngspice unavailable | Change amplitude/frequency, rerun | Waveform changes with input | — | ngspice missing | NOT RUN |
| B7 · Invalid / Fail | Flask test client + mock | Run SPICE with ngspice unavailable | Clear error, no fake success/old success graph | "SPICE Error..." shown, "Success" absent | `test_spice_engine.py::TestAppSpiceIntegration::test_spice_run_missing_ngspice_shows_error_not_success` | PASS (error-path, test client) |
| B8 · UI | NOT RUN - Playwright MCP/browser not executed in this session | Desktop/mobile viewport, switch modes | No clipped critical content, readable units/graphs | — | No Playwright MCP run recorded | NOT RUN |

## Notes / Limitations

- Real ngspice `.op/.ac/.tran` evidence is missing because ngspice is not installed in this environment. The adapter and parsers are implemented and covered by mocked tests; real engine validation must be rerun after installing ngspice and confirming the BJT model.
- Playwright MCP browser acceptance was not executed. Before submission, run B1–B8 with a real browser and attach screenshots/log evidence.
- AC gain uses `v(out)` with AC source magnitude 1V in netlist for convenient magnitude reading; verify measurement point convention against the instructor reference circuit before claiming physical gain.
- Existing Lab 3 divider analytical reference remains: IC 1.22986 mA, VCE 8.05216 V for VCC=12V,R1=100kΩ,R2=22kΩ,RC=2.2kΩ,RE=1kΩ,beta=100,VBE=0.7V.