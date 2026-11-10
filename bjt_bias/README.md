# BJT Common-Emitter DC Bias — ENG29 2121

เว็บแอป Flask สำหรับคำนวณ DC operating point ของวงจรไบแอส BJT แบบ
common-emitter (voltage-divider bias) จากค่า `VCC, R1, R2, RC, RE, beta, VBE`
พร้อม validation, region warning และการตรวจทานด้วยสมการอิสระอีกชุด

ขอบเขต: **DC bias เท่านั้น** — ไม่มี AC, transient, load line, circuit editor หรือ FET

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `engineering.py` | สูตรบริสุทธิ์ (ไม่ import Flask) — validate, แปลงหน่วย, Thevenin, nodal, cross-check, region |
| `app.py` | Flask route และ Jinja filter สำหรับจัดรูปแบบตัวเลข |
| `templates/index.html` | ฟอร์ม + แผนผังวงจร SVG + ตารางผล + error/warning |
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

> `bjt_bias/app.py` มี `app.run(debug=True)` สำหรับรันตรง ๆ — อย่าเปิด debugger นี้สู่เครือข่ายสาธารณะ เพราะเปิดให้รันโค้ดจากระยะไกลได้

## ทดสอบ

```powershell
.venv\Scripts\python -m pytest bjt_bias\tests -q
```

## หน่วย

| ปริมาณ | รับเข้า | คำนวณภายใน | แสดงผล |
|---|---|---|---|
| VCC, VBE | V | V | V |
| R1, R2, RC, RE | Ω หรือ kΩ (เลือกจาก dropdown) | Ω | — |
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
