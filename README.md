# ENG29 2121 — BJT DC Bias / CE Amplifier Simulator (Lab 3 → Lab 4)

Flask web app สำหรับคำนวณ **DC Bias แบบ Analytical 3 โหมด** (Lab 3 baseline) และจำลองวงจร **CE Voltage Divider Reference** ด้วย **ngspice จริง** (`.op`, `.ac`, `.tran`) สำหรับ Lab 04.

> **สำคัญ:** ผล SPICE ที่แสดงใน UI ต้องมาจาก ngspice ที่รันจริงเท่านั้น ระบบจะแสดง error/สถานะเมื่อ engine ไม่พร้อม และไม่แสดงกราฟปลอม

## สิ่งที่มีในโปรเจกต์

- **Lab 3 Analytical DC Bias (3 modes):** `Voltage Divider Bias`, `Fixed Bias`, `Emitter Bias` ใน `bjt_bias/engineering.py`
- **Lab 4 ngspice path:** สร้าง netlist, เรียก `ngspice` ด้วย `subprocess.run(..., shell=False, timeout=...)`, parse output จริง, แยกแสดงผล Analytical/SPICE ใน `bjt_bias/spice_engine.py` + `bjt_bias/app.py`
- **UI:** ฟอร์มพารามิเตอร์, เลือกโหมด bias, ปุ่มคำนวณ DC, ปุ่ม/แท็บรัน SPICE, กราฟ AC/Transient จากข้อมูลจริง, แสดง netlist/log tail และ provenance

## โครงสร้างหลัก

```text
bjt_bias/
  app.py                 # Flask routes, form handling, SPICE dispatch
  engineering.py         # Analytical DC bias (3 modes), pure Python
  spice_engine.py        # ngspice netlist/run/parse adapter
  templates/index.html   # UI template
  static/style.css       # UI styling
  tests/                 # pytest + Flask test client tests
docs/
  validation.md          # B1–B8 validation record
README.md
```

## ความต้องการระบบ

- Python 3.x (ทดสอบกับ venv ในโปรเจกต์)
- Python dependencies: ดู `bjt_bias/requirements.txt`
- **ngspice** (ติดตั้งแยกจาก Python, ไม่ใช่ pip package) สำหรับรัน `.op/.ac/.tran`

## ติดตั้ง Python Dependencies

```powershell
cd C:\Users\b6648794\Desktop\Gitlab
python -m venv .venv
.venv\Scripts\python -m pip install -r bjt_bias\requirements.txt
```

## ติดตั้ง ngspice (Windows)

1. ดาวน์โหลด ngspice สำหรับ Windows จาก https://ngspice.sourceforge.io/download.html
2. แตกไฟล์/ติดตั้ง แล้วหาโฟลเดอร์ที่มี `ngspice.exe` (เช่น `...\Spice64\bin`)
3. ทำให้ `ngspice` เรียกได้จาก terminal:
   - **ชั่วคราว (PowerShell session เดียว):**
     ```powershell
     $env:Path += ";C:\Users\b6648794\Downloads\ngspice-47_64\Spice64\bin"
     ```
   - **ชั่วคราว (cmd session เดียว):**
     ```cmd
     set "PATH=%PATH%;C:\Users\b6648794\Downloads\ngspice-47_64\Spice64\bin"
     ```
   - **ถาวรระดับ User:** เพิ่มโฟลเดอร์ `bin` ใน *Edit environment variables for your account* → `Path`
4. ตรวจสอบ:

```powershell
where.exe ngspice
.venv\Scripts\python -c "import shutil; print(shutil.which('ngspice'))"
```

## วิธีรัน Server

รันใน terminal ที่มี ngspice ใน PATH (ถ้าต้องการใช้ SPICE):

```powershell
cd C:\Users\b6648794\Desktop\Gitlab
$env:Path += ";C:\Users\b6648794\Downloads\ngspice-47_64\Spice64\bin"   # ปรับ path ตามเครื่อง
.venv\Scripts\python -m bjt_bias.app
```

เมื่อเห็นข้อความ `Running on http://127.0.0.1:5000` ให้เปิด browser ไปที่ URL นั้น

## วิธีใช้งานใน Browser

1. เปิด `http://127.0.0.1:5000/`
2. เลือก **Bias Mode** (Voltage Divider / Fixed / Emitter) แล้วใส่พารามิเตอร์
3. กด **คำนวณ DC Bias** เพื่อดูผล Analytical
4. สำหรับ Lab 4 CE Reference: เลือก `Voltage Divider Bias` แล้วกดแท็บ/ปุ่ม **DC (.op)**, **AC (.ac)**, หรือ **Transient (.tran)** เพื่อรัน ngspice จริง
5. ตรวจผลใน panel Simulation & Plots, Engineering Results, และ `Netlist / log tail`

## ทดสอบอัตโนมัติ

```powershell
cd C:\Users\b6648794\Desktop\Gitlab
.venv\Scripts\python -m pytest bjt_bias\tests -q
```

การทดสอบที่รันได้ในสภาพแวดล้อมที่ไม่มี ngspice จะใช้ mocked subprocess/Flask test client; ดูรายละเอียดใน `docs/validation.md`.

## Validation / Submission Evidence

- บันทึกการตรวจ B1–B8: `docs/validation.md`
- ก่อนส่งงาน ควรแนบ: screenshot กราฟจริงจาก browser, log tail/netlist ที่เกี่ยวข้อง, before/after UI (ถ้ามี), และบันทึก 3–5 บรรทัดว่า AI ทำอะไร/นักศึกษาตรวจอะไรเอง

## ข้อจำกัดและหมายเหตุ

- **BJT model:** ค่าเริ่มต้นใน `spice_engine.py` เป็น `Q2N3904_GENERIC` (generic approximation) — ก่อนตรวจ/ส่งงานจริงควรแทนด้วย model ที่ instructor starter กำหนด และบันทึก provenance ใน `docs/validation.md`
- **ngspice ไม่พร้อม:** UI จะแสดง SPICE error และไม่แสดงกราฟปลอม
- **AC convention:** netlist ตั้ง AC source magnitude = 1V เพื่อให้อ่าน magnitude ได้สะดวก; ควรตรวจจุดวัด/ convention กับ reference circuit ก่อนสรุปผล gain ทางกายภาพ
- **อย่า commit:** `.venv/`, `.env`, API keys/tokens, ไฟล์ run ชั่วคราวขนาดใหญ่

## Submission Info (เติมก่อนส่ง)

- GitHub Repository URL: `https://github.com/Nckktk/Gitlab.git`
- Commit SHA: `[ใส่ commit SHA ที่ส่งจริง]`
- ผู้จัดทำ/ตรวจสอบ: `[ชื่อ-รหัสนักศึกษา]`