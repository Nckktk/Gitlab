# Lab 04 Validation — BJT CE Amplifier Simulator v1

> กรอกเอกสารนี้จากผลรันจริงเท่านั้น ห้าม fabricate ผล ngspice/กราฟ/screenshot

## ข้อมูลการตรวจ

- **Date:** [YYYY-MM-DD]
- **Tester:** [ชื่อ-รหัสนักศึกษา]
- **Repository:** https://github.com/Nckktk/Gitlab.git
- **Commit SHA:** [ใส่ SHA ที่ส่งจริง]
- **Environment:** Windows [version], Python [version], Browser [name/version]
- **ngspice:** [ผลจาก `ngspice --version` หรือ `where.exe ngspice`]
- **BJT SPICE model:** `Q2N3904_GENERIC` (generic approximation ใน `bjt_bias/spice_engine.py`) — [ระบุถ้าเปลี่ยนเป็น instructor starter model]
- **Reference circuit/model source:** [Lab04 handout / starter netlist / แหล่งอ้างอิง]

## Automated Checks (pytest / test client)

| Check | Command / Method | Result | Evidence |
|---|---|---:|---|
| Unit/integration tests | `.venv\Scripts\python.exe -m pytest bjt_bias\tests -q` | PASS (52 passed, ณ commit ล่าสุดที่ทดสอบ) | [แนบ log / screenshot terminal] |
| SPICE missing-engine behavior | Flask test client + mock `ngspice_available=False` | PASS | `bjt_bias/tests/test_spice_engine.py` |
| SPICE result rendering (mocked data) | Flask test client + mock `run_analysis` | PASS | `bjt_bias/tests/test_spice_engine.py` |

## B1–B8 Browser/Simulation Acceptance

เติมทุกเคสจากผลรันจริง ถ้าไม่ได้รันให้ระบุ `NOT RUN` และเหตุผลอย่างตรงไปตรงมา

| Case | Method | Input | Expected / Reference | Observed (ผลจริง) | Evidence (screenshot/log) | Status |
|---|---|---|---|---|---|---:|
| B1 · Regression | Browser + Flask app / เทียบ Lab 3 | Divider: VCC=12V, R1=100kΩ, R2=22kΩ, RC=2.2kΩ, RE=1kΩ, β=100, VBE=0.7V | IC≈1.22986 mA, VCE≈8.05216 V (Lab 2/3 reference) | [ใส่ค่าจริงจากหน้าจอ] | [screenshot] | [PASS/FAIL/NOT RUN] |
| B2 · DC SPICE | Browser + ngspice จริง | CE Reference, Voltage Divider, Run DC (.op) | ได้ VB/VE/VC/VCE/IC จาก ngspice output พร้อม engine/model provenance | [ใส่ค่าจริง] | [screenshot + netlist/log tail] | [PASS/FAIL/NOT RUN] |
| B3 · Change RE | Browser + ngspice จริง | เปลี่ยน RE เท่านั้น แล้ว rerun DC | Operating point เปลี่ยนตามผลจำลองจริง | [ค่า RE เดิม/ใหม่ + ผลจริง] | [screenshot ก่อน/หลัง] | [PASS/FAIL/NOT RUN] |
| B4 · AC | Browser + ngspice จริง | Run AC (.ac) | Bode magnitude/phase มีแกน/หน่วยถูกต้อง จากข้อมูลจริง | [สรุปช่วง freq/gain/phase ที่เห็น] | [screenshot กราฟจาก browser] | [PASS/FAIL/NOT RUN] |
| B5 · Transient | Browser + ngspice จริง | 10 mVpk, 1 kHz, Run Transient (.tran) | Vin/Vout vs time มีหน่วย/แกนถูกต้อง เห็น phase inversion ตามที่คาด | [สิ่งที่เห็นจริง] | [screenshot กราฟจาก browser] | [PASS/FAIL/NOT RUN] |
| B6 · Change Source | Browser + ngspice จริง | เปลี่ยน amplitude/frequency แล้ว rerun | Waveform/response เปลี่ยนสอดคล้องกับ input ใหม่ | [input เดิม/ใหม่ + ผลจริง] | [screenshot ก่อน/หลัง] | [PASS/FAIL/NOT RUN] |
| B7 · Invalid / Fail | Browser / test client | ทำให้ ngspice fail หรือ input invalid | แสดง error ชัดเจน ไม่มี fake success/กราฟเก่าแสดงเป็น success | [ข้อความ error ที่เห็นจริง] | [screenshot/log] | [PASS/FAIL/NOT RUN] |
| B8 · UI | Browser / Playwright MCP | Desktop/mobile viewport, เปลี่ยนโหมด, ดูกราฟ/ผลลัพธ์ | เนื้อหาสำคัญไม่ถูกตัด อ่านค่า/หน่วย/กราฟได้ | [สิ่งที่ตรวจจริง] | [screenshot desktop/mobile] | [PASS/FAIL/NOT RUN] |

## B1 Reference (Lab 2/3 Baseline)

- **Input:** VCC=12V, R1=100kΩ, R2=22kΩ, RC=2.2kΩ, RE=1kΩ, β=100, VBE=0.7V
- **Expected reference:** IC = 1.22986 mA, VCE = 8.05216 V
- **Observed:** [ใส่ผลจริงจากแอป/การทดสอบ]
- **Deviation:** [คำนวณ % หรืออธิบายถ้าเท่ากัน]

## SPICE Evidence Notes

- **Netlist source:** สร้างจาก `bjt_bias/spice_engine.py` ตามพารามิเตอร์ในฟอร์ม
- **Execution:** `subprocess.run([...ngspice..., -b, netlist], shell=False, timeout=...)`
- **Output provenance:** แนบ netlist, log tail, และ screenshot ที่แสดง engine/model/status
- **AC measurement convention:** [ระบุจุดวัด เช่น `v(out)`/`v(in)`, AC source 1V, ฯลฯ]
- **Transient measurement:** [ระบุ Vin/Vout nodes, time window, step]

## Deviations / Limitations

- [ระบุความคลาดเคลื่อนระหว่าง Analytical vs SPICE และสาเหตุที่เป็นไปได้]
- [ระบุข้อจำกัด model: generic Q2N3904 vs instructor model]
- [ระบุข้อจำกัด UI/browser/ngspice version]
- [ถ้าเคสใด NOT RUN ให้ระบุเหตุผล]

## Screenshots / Evidence Checklist

- [ ] Before/After UI (หรือบันทึกการปรับ UI ด้วย Impeccable)
- [ ] B2 DC `.op` screenshot + log tail
- [ ] B4 AC Bode screenshot (browser จริง)
- [ ] B5 Transient screenshot (browser จริง)
- [ ] B7 error screenshot
- [ ] B8 desktop/mobile screenshot
- [ ] Netlist sample / run log sample (ขนาดเหมาะสม)

## AI Use Note (3–5 บรรทัด, เขียนเองก่อนส่ง)

- **AI ช่วย:** [ระบุส่วนที่ AI สร้าง/แก้]
- **นักศึกษาตรวจเอง:** [ระบุสิ่งที่ตรวจ เช่น สูตร, pytest, รัน ngspice จริง, เทียบ handout, ตรวจกราฟ/หน่วย, ตรวจ commit]
- **หลักฐานที่ยืนยันด้วยตนเอง:** [ระบุ screenshot/log/test ที่รันเอง]
