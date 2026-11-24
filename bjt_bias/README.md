# BJT Bias / CE Amplifier Simulator — ENG29 2121

Flask web app สำหรับ Lab 3/Lab 4: คำนวณ DC bias แบบ Analytical 3 โหมด และจำลอง CE Voltage Divider reference ด้วย ngspice (`.op/.ac/.tran`).

## ความสามารถ

- **Analytical DC Bias 3 โหมด:** Voltage Divider, Fixed Bias, Emitter Bias (pure Python ใน `engineering.py`).
- **SPICE CE Reference:** เรียก ngspice ภายนอกผ่าน `spice_engine.py` เพื่อรัน `.op`, `.ac`, `.tran` สำหรับวงจร CE voltage divider อ้างอิง. แยก provenance ว่าเป็นผล SPICE ไม่ใช่ Analytical.
- **Validation/Errors:** input validation, timeout/process error handling, ไม่แสดงกราฟปลอมเมื่อ run fail.

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `engineering.py` | สูตร Analytical DC bias (Flask-free) |
| `spice_engine.py` | สร้าง netlist, รัน ngspice subprocess, parse output |
| `app.py` | Flask route, validation, dispatch Analytical/SPICE |
| `templates/index.html` | ฟอร์ม, schematic, ผล Analytical, SPICE status/plots |
| `static/style.css` | สไตล์ responsive |
| `tests/` | pytest unit/integration tests (รวม mocked SPICE) |

## ติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r bjt_bias\requirements.txt
```

ติดตั้ง ngspice จากระบบปฏิบัติการแล้วตรวจสอบ:

```powershell
ngspice --version
```

## รัน

```powershell
.venv\Scripts\python -m bjt_bias.app
```

เปิด `http://127.0.0.1:5000`

## ทดสอบ

```powershell
.venv\Scripts\python -m pytest bjt_bias\tests -q
```

## SPICE Reference Circuit (v1)

- Topology: CE Voltage Divider, NPN, Cin/Cout/RL, no emitter bypass (baseline)
- Default inputs: VCC 12V, R1 100kΩ, R2 22kΩ, RC 2.2kΩ, RE 1kΩ, RL 10kΩ, Cin 10µF, Cout 10µF, 10mVpk 1kHz
- Model: `Q2N3904_GENERIC` (generic approximation in code; replace with instructor starter model before official validation)

## สมมติฐาน/ข้อจำกัด

- Analytical ใช้สมมติฐาน BJT idealized (β, VBE ตามที่กรอก) และไม่เหมือน SPICE model ทุกประการ.
- SPICE `.op` รายงาน node voltages/currents จาก ngspice; ค่า IC แสดงจาก current probe ของแหล่ง VCC (`-i(vcc)`).
- AC gain plot ใช้ `v(out)` จาก AC analysis โดยตั้ง AC source magnitude = 1 (อ่านเป็น gain โดยตรง); ต้องระบุจุดวัด/สมมติฐานในรายงานเมื่อตรวจจริง.
- หาก ngspice ไม่พร้อม/รันผิดพลาด/timeout ระบบต้องแสดง error และไม่แสดง success ปลอม.