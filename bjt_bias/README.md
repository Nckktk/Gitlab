# BJT Common-Emitter DC Bias — ENG29 2121

เว็บแอป Flask สำหรับคำนวณ DC operating point ของวงจรไบแอส BJT แบบ
common-emitter 3 แบบจากหน้าเดียว: **Voltage Divider Bias** (ของ Lab 2),
**Fixed Bias** และ **Emitter Bias แบบแหล่งจ่ายเดียว** พร้อม validation ตามโหมด,
region warning และการตรวจทานด้วยสมการอิสระอีกชุดสำหรับ Divider

ขอบเขต: **DC bias เท่านั้น** — ไม่มี AC, transient, load line, circuit editor หรือ FET
และไม่เพิ่ม `unittest` ใหม่ (ใช้ตาราง A1–A5 ใน `docs/validation.md` ตรวจผ่าน Browser)

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `engineering.py` | สูตรบริสุทธิ์ (ไม่ import Flask) — validate ตามโหมด, แปลงหน่วย, Thevenin, nodal, cross-check, fixed, emitter, region |
| `app.py` | Flask route, เลือกฟังก์ชันตาม `mode`, Jinja filter สำหรับจัดรูปแบบตัวเลข |
| `templates/index.html` | ฟอร์มเลือกโหมด + แผนผัง SVG ตามโหมด + ตารางผล + error/warning |
| `static/style.css` | จัดหน้าแบบการ์ด สองคอลัมน์ |
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

ในหน้าเว็บให้เลือก `Voltage Divider Bias`, `Fixed Bias` หรือ `Emitter Bias` ในช่อง
`วงจรไบอัส` แล้วกด **เปลี่ยนโหมด** เพื่อโหลดฟอร์มที่ใช้เฉพาะวงจรนั้น (switch ฝั่ง Flask
ไม่มี JavaScript) ผลลัพธ์และข้อความเตือนจะระบุโหมดที่เลือกเสมอ ถ้าส่งข้อมูลผิดจะไม่มี
ผลของรอบก่อนแสดงร่วมด้วย

> `bjt_bias/app.py` มี `app.run(debug=True)` สำหรับรันตรง ๆ — อย่าเปิด debugger นี้สู่เครือข่ายสาธารณะ เพราะเปิดให้รันโค้ดจากระยะไกลได้

## ทดสอบ

```powershell
.venv\Scripts\python -m pytest bjt_bias\tests -q
```

## หน่วย

| ปริมาณ | รับเข้า | คำนวณภายใน | แสดงผล |
|---|---|---|---|
| VCC, VBE | V | V | V |
| R1, R2, RB, RC, RE | Ω หรือ kΩ (เลือกจาก dropdown) | Ω | — |
| beta | ไม่มีหน่วย | — | — |
| IB, IC, IE | — | A | A / mA / µA / nA อัตโนมัติ |
| VB, VE, VC, VCE | — | V | V |

- ค่า kΩ ถูกคูณ 1,000 ให้เป็น Ω **ก่อน** คำนวณและก่อนตรวจขอบเขต `1e12`
- ตัวเลขทุกตัวแสดง 6 significant figures (`%.6g`)
- ถ้าไม่ส่ง `*_unit` มา (เช่นเรียกด้วย curl หรือ test ตรง) ระบบถือว่าเป็น Ω

## แบบจำลองและสมมติฐาน

- ใช้ **Forward-Active Approximation**: β คงที่ตลอดช่วงการทำงาน และ VBE คงที่ตามค่าที่กรอก
- ไม่คิด **Early effect** (ไม่มีความต้านทานเอาต์พุต `ro`) และไม่คิดความต้านทาน base ที่ขึ้นกับกระแส
- กระแสอิ่มตัวย้อนกลับ (leakage) เป็นศูนย์
- สมการเชิงเส้นใช้ได้เฉพาะใน active region — นอกช่วงนี้หน้าเว็บจะขึ้น warning และค่าที่แสดงไม่ได้มาจากการจำลองที่แม่นยำ
- แผนผังวงจรในหน้าเว็บเป็นภาพประกอบโครงสร้าง ไม่ได้วาดตามสัดส่วนหรือค่าอุปกรณ์จริง

## สมการตามโหมด

อินพุตร่วมทุกโหมด: `VCC, RC, beta, VBE` แล้วตามด้วยช่องเฉพาะวงจร

| mode | อินพุตเพิ่ม | IB |
|---|---|---|
| `fixed` | `RB` | `(VCC − VBE) / RB` |
| `emitter` | `RB, RE` | `(VCC − VBE) / [RB + (beta + 1)RE]` |
| `divider` | `R1, R2, RE` | `(VTH − VBE) / [RTH + (beta + 1)RE]` |

จาก `IB`: `IC = beta·IB`, `IE = (beta + 1)·IB`,
`VE = IE·RE` (Fixed ใช้ `VE = 0`), `VB = VE + VBE`,
`VC = VCC − IC·RC`, `VCE = VC − VE`

โหมดใหม่ไม่สร้างค่าจำลอง Cutoff/Saturation ขึ้นมาเอง ถ้า `IB <= 0` หรือ
`VCE <= 0.2 V` จะขึ้น `model-limit` พร้อมข้อความเตือนว่าแบบจำลอง Forward Active
อาจใช้ไม่ได้

**วิธีที่ 1 — Thevenin equivalent (divider เท่านั้น)**

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
| `IB <= 0` (divider) | Cutoff | `IB = IC = IE = 0`, `VE = 0`, `VC = VCE = VCC` |
| `VCE <= 0.2 V` (divider) | Saturation + warning | ค่าจาก linear model ตามจริง (ไม่ clamp) |
| `IB <= 0` หรือ `VCE <= 0.2 V` (fixed/emitter) | Model limit + warning | ค่าจาก linear model ตามจริง |
| อื่น ๆ | Active | ค่าจาก linear model |

## ตัวอย่าง

ข้อมูลทดลองเริ่มต้นของ Lab 2: `VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, beta=100, VBE=0.70 V`
(กรอกในช่อง R1…RE เป็น `100, 22, 2.2, 1` แล้วเลือก kΩ)

```
IB  = 12.2986 µA      IC = 1.22986 mA     IE = 1.24216 mA
VB  = 1.94216 V       VE = 1.24216 V      VC = 9.29431 V
VCE = 8.05216 V       region = Active
```

อีกตัวอย่าง: `VCC=12, R1=10000 Ω, R2=2200 Ω, RC=1000 Ω, RE=470 Ω, beta=150, VBE=0.7`

```
IB  = 20.1164 µA      IC = 3.01746 mA     IE = 3.03757 mA
VB  = 2.12766 V       VE = 1.42766 V      VC = 8.98254 V
VCE = 7.55489 V       region = Active
```

ตัวอย่างโหมดใหม่ที่ใช้ค่าร่วม `VCC=12 V, RC=2.2 kΩ, beta=100, VBE=0.70 V`:

| กรณี | โหมด / อินพุต | IC | VCE |
|---|---|---|---|
| A2 | Fixed · RB = 1 MΩ (กรอก `1000` ในช่วง kΩ) | 1.13 mA | 9.514 V |
| A3 | Emitter · RB = 1 MΩ, RE = 1 kΩ | 1.02634 mA | 8.70545 V |
| A4 | Emitter · RB = 1 MΩ, RE = 2 kΩ | 940.1 µA (= 0.9401 mA) | 8.03278 V |

เพิ่ม RE จาก A3 เป็น A4 แล้ว IC ลดลงเพราะตัวหาร `(RB + (beta+1)RE)` เพิ่มขึ้น
ดูตาราง A1–A5 และวิธีตรวจผ่าน Browser ได้ที่ `docs/validation.md`
