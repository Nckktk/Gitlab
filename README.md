# ENG29 2121 — BJT DC Bias / Amplifier Simulator (Lab 3 → Lab 4)

โปรเจกต์นี้ต่อยอดจาก Lab 3 Flask web app สำหรับคำนวณ DC bias ของ BJT CE และเพิ่มเส้นทางจำลอง **ngspice จริง** สำหรับวงจร CE Voltage Divider อ้างอิง (DC `.op`, AC `.ac`, Transient `.tran`) ตาม Lab 04 handout.

## สถานะปัจจุบัน

- **Lab 3 baseline:** มี 3 โหมด Analytical DC Bias (`Voltage Divider`, `Fixed Bias`, `Emitter Bias`) ใน `bjt_bias/engineering.py` และหน้าเว็บ Flask เดิม/ขยาย.
- **Lab 4 SPICE path:** มี `bjt_bias/spice_engine.py` สำหรับสร้าง netlist, เรียก `ngspice` แบบ external process (`subprocess.run`, ไม่ใช้ `shell=True`, มี timeout), และ parse ผลลัพธ์. UI แสดงสถานะ engine/provenance และแยกผล Analytical กับ SPICE.
- **ข้อจำกัดสภาพแวดล้อมนี้:** เครื่องที่ใช้พัฒนาตอนนี้ **ไม่พบ `ngspice` ใน PATH** จึงยังไม่ได้รัน B2–B6 แบบ engine จริง; การทดสอบที่รันได้เป็น pytest + Flask test client + mocked subprocess. ดู `docs/validation.md`.

## โครงสร้างหลัก

```text
bjt_bias/
  app.py              # Flask routes, form handling, SPICE dispatch
  engineering.py      # Analytical DC bias (3 modes), pure Python
  spice_engine.py     # ngspice netlist/run/parse adapter
  templates/index.html
  static/style.css
  tests/
docs/
  validation.md
  superpowers/...
```

## ติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r bjt_bias\requirements.txt
```

ติดตั้ง ngspice แยกจาก Python (ไม่ใช่ pip package) และตรวจให้เรียกได้จาก terminal:

```powershell
ngspice --version
```

## รัน

```powershell
.venv\Scripts\python -m bjt_bias.app
```

เปิด URL ที่ Flask แจ้ง เช่น `http://127.0.0.1:5000/`

## ทดสอบ

```powershell
.venv\Scripts\python -m pytest bjt_bias\tests -q
```

## หมายเหตุสำคัญ

- ผล SPICE ที่แสดงใน UI ต้องมาจาก ngspice run จริง; ถ้า engine ไม่พร้อมระบบจะแสดง error/สถานะ ไม่แสดงกราฟปลอม.
- BJT model เริ่มต้นใน `spice_engine.py` เป็น generic 2N3904 approximation สำหรับการพัฒนา; ก่อนส่งงานจริงควรแทนด้วย model ที่ instructor starter กำหนดและบันทึก provenance.
- อย่า commit `.venv/`, `.env`, API keys, หรือไฟล์ run ชั่วคราวขนาดใหญ่.