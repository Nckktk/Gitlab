# BJT Common-Emitter DC Bias — ENG29 2121

เว็บแอป Flask สำหรับคำนวณ DC operating point ของวงจรไบแอส BJT แบบ
common-emitter (voltage-divider bias) จากค่า `VCC, R1, R2, RC, RE, beta, VBE`
พร้อม validation, region warning และการตรวจทานด้วยสมการอิสระอีกชุด

ขอบเขต: **DC bias เท่านั้น** — ไม่มี AC, transient, load line, circuit editor หรือ FET

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `engineering.py` | สูตรบริสุทธิ์ (ไม่ import Flask) — validate, Thevenin, nodal, cross-check, region |
| `app.py` | Flask route และการอ่านค่าจากฟอร์มเท่านั้น |
| `templates/index.html` | ฟอร์ม + ตารางผล + error/warning |
| `static/style.css` | จัดหน้าให้อ่านง่าย |
| `tests/` | unit test ของสูตร และ route test ด้วย Flask test client |

## ติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r bjt_bias\requirements.txt
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

## สมการ

**วิธีที่ 1 — Thevenin equivalent**

```
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
IB  = (VBB - VBE) / (RB + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = IE * RE
VC  = VCC - IC * RC
VCE = VC - VE
```

**วิธีที่ 2 — Nodal analysis** (ตรวจทานอิสระ)

ใช้ `VB = VE + VBE` แล้วตั้ง KCL ที่โหนด B และ E:

```
(VE + VBE - VCC)/R1 + (VE + VBE)/R2 + VE/((beta + 1) * RE) = 0
```

แก้หา `VE` แล้วได้ `IE = VE / RE`, `IC = beta/(beta + 1) * IE`
ทั้งสองวิธีต้องตรงกันที่ relative tolerance `1e-9` มิฉะนั้นหน้าเว็บจะขึ้น "ไม่ผ่าน"

## เกณฑ์ region

| เงื่อนไข | Region | ค่าที่รายงาน |
|---|---|---|
| `IB <= 0` | Cutoff | `IB = IC = IE = 0`, `VE = 0`, `VC = VCE = VCC` |
| `VCE <= 0.2 V` | Saturation + warning | ค่าจาก linear model ตามจริง (ไม่ clamp) |
| อื่น ๆ | Active | ค่าจาก linear model |

## ตัวอย่าง

Input: `VCC=12, R1=10000, R2=2200, RC=1000, RE=470, beta=150, VBE=0.7`

```
IB  = 2.01164e-05 A   IC = 0.00301746 A   IE = 0.00303757 A
VB  = 2.12766 V       VE = 1.42766 V      VC = 8.98254 V
VCE = 7.55489 V       region = Active
```
