# Design — BJT Common-Emitter DC Bias Web App (ENG29 2121)

วันที่: 2026-11-10
สถานะ: อนุมัติแล้ว 2026-11-10 — เจ้าของโปรเจกต์สั่งให้เริ่มสร้าง
ขอบเขต: DC bias point เท่านั้น

## 1. เจตนาและเหตุผล

ส่งงานแล็บ ENG29 2121 ที่ต้องเป็นเว็บ Flask จริง ไม่ใช่สคริปต์คำนวณในเทอร์มินัล
เป้าหมายเชิงคุณภาพ: ตัวเลขทุกตัวบนหน้าจอต้องออกมาจากสมการที่รันฝั่ง server
ไม่ใช่ค่าคงที่ใน template และไม่ใช่การคำนวณซ้ำใน JavaScript

ต้องการเดโมบน localhost และ commit ขึ้น GitHub ภายในวันนี้

## 2. เป้าหมาย / ไม่ใช่เป้าหมาย / สิ่งที่ถือว่าล้มเหลว

**เป้าหมาย**
1. รับค่า `VCC, R1, R2, RC, RE, beta, VBE` แล้วคืน DC operating point พร้อมหน่วย
2. ตรวจ input และแจ้ง error ที่อ่านรู้เรื่องโดยไม่ทำให้แอปพัง
3. ระบุ region (active / cutoff / saturation) พร้อม warning
4. คำนวณด้วยสองวิธีที่ตั้งสมการต่างกัน แล้วเทียบผลกันจริง
5. รันได้บน localhost และมี test ครอบ logic กับ route

**ไม่ใช่เป้าหมาย**
- AC analysis, transient, load line, กราฟ, Bode plot, function generator
- circuit editor, การเลือกอุปกรณ์, ฐานข้อมูล, login
- FET / MOSFET
- JavaScript ฝั่ง client, auto unit prefix (µA/mA), export, history

**ถือว่าล้มเหลวถ้า**
- ตัวเลขบนหน้าเว็บ hardcode หรือคำนวณฝั่ง client
- independent check ผ่านตลอดจนไม่มีความหมาย (rubber stamp)
- validation พังเป็น traceback / HTTP 500
- ประกาศว่า test ผ่านโดยไม่ได้รันจริง

## 3. ข้อจำกัด

- Windows, Python 3.12.7, **ยังไม่มี Flask และ pytest** → ต้องสร้าง `.venv` และ `requirements.txt`
- รันเฉพาะ localhost, dev server ของ Flask, ไม่มี DB
- ต้องทำเสร็จในคาบเดียว
- repo `Nckktk/Gitlab` มี DC circuit calculator อยู่ที่ root แล้ว → งานนี้อยู่ใน `bjt_bias/` และ**ไม่แตะไฟล์เดิม**
- อินเทอร์เฟซเป็นภาษาไทย หน่วยและสัญลักษณ์วิศวกรรมเป็นภาษาอังกฤษ

## 4. โมเดลวิศวกรรม

ใช้แบบจำลอง BJT โหมด active แบบง่าย: `VBE` คงที่ตามที่ผู้ใช้กรอก, `beta` คงที่, ไม่คิด Early effect, ไม่คิดกระแสรั่ว

พารามิเตอร์ที่รับ: `vcc, r1, r2, rc, re, beta, vbe`

**วิธีที่ 1 — Thevenin equivalent (เส้นทางหลัก)**
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

**วิธีที่ 2 — Nodal analysis (ตรวจทานอิสระ)**
ใช้ `VB = VE + VBE` แล้วตั้ง KCL ที่โหนด B และ E เหลือสมการเดียวในตัวแปร `VE`:
```
(VE + VBE - VCC)/R1 + (VE + VBE)/R2 + VE/((beta + 1) * RE) = 0
```
แก้ได้ `VE` ตรง ๆ → `IE = VE / RE` → `IC = beta/(beta + 1) * IE` → `VC`, `VCE` ตามเดิม

**การเทียบผล:** เทียบ `IC` และ `VCE` ด้วย relative tolerance `1e-9`
โดยใช้ตัวส่วน `max(|a|, |b|, 1e-12)` เพื่อกัน `0/0` (ถ้าทั้งคู่เป็นศูนย์พอดี ให้ถือว่า diff = 0)
ผลลัพธ์มีฟิลด์ `check.passed: bool` และ `check.max_rel_diff: float`

**ลำดับการทำงานใน `analyze()` (ตัดสินแล้ว):**
1. เรียกทั้งสอง solver กับ input ดิบ → ได้ผลดิบสองชุด
2. เทียบผลดิบ → `check` (การเทียบเกิด**ก่อน**การปรับค่าตาม region เสมอ)
3. จึงตัดสิน region และปรับค่าที่จะรายงาน

เหตุผล: ในโหมด cutoff สมการ linear ให้ค่าติดลบซึ่งไม่มีความหมายทางกายภาพ
แต่ทั้งสอง solver ยังต้องตรงกัน — ดังนั้น `check` ต้องตอบคำถามว่า "สองสมการตรงกันหรือไม่"
ไม่ใช่ "ค่าที่แสดงตรงกับสมการหรือไม่"

## 5. Region และกรณีขอบ

เรียงลำดับการตัดสิน:
1. `IB <= 0` → **cutoff**
2. `VCE <= 0.2` → **saturation** + warning ว่า Q-point นี้อยู่นอก active region
3. อื่น ๆ → **active**

**ค่าที่รายงานในโหมด cutoff (ตัดสินแล้ว):** ใช้สภาวะขอบทางกายภาพ ไม่ใช่ค่าติดลบจากสมการ
`IB = IC = IE = 0`, `VE = 0`, `VC = VCC`, `VCE = VCC`
(ส่วน `check` ยังคงเทียบผลดิบตามข้อ 4 และควร PASS)

โหมด saturation และ active รายงานค่าจาก linear model ตามจริง **ไม่ clamp** `VCE` เป็น 0.2
เพราะการกลบตัวเลขทำให้ตรวจสอบย้อนกลับไม่ได้

## 6. การตรวจสอบ input

ปฏิเสธเมื่อ: ฟิลด์ว่าง, ไม่ใช่ตัวเลข, `NaN`/`Inf`, `VCC <= 0`, `R1,R2,RC,RE <= 0`, `beta <= 0`, `VBE < 0`, `VBE >= VCC`
และค่าสัมบูรณ์ของทุกฟิลด์ต้องไม่เกิน `1e12` (กัน overflow ที่ทำให้ผลลัพธ์กลายเป็น `nan`)
แสดง error ใต้ฟอร์มและคงค่าที่ผู้ใช้กรอกไว้ (HTTP 200, ไม่ใช่ 500)

## 7. ส่วนประกอบและความรับผิดชอบของไฟล์

| ไฟล์ | ความรับผิดชอบ | ห้ามมี |
|---|---|---|
| `bjt_bias/__init__.py` | ประกาศ package | — |
| `bjt_bias/engineering.py` | validate, `solve_thevenin`, `solve_nodal`, `analyze`, dataclass ผลลัพธ์ | import Flask |
| `bjt_bias/app.py` | Flask app, route `GET/POST /`, อ่านฟอร์ม, เรียก `analyze`, render | สูตรวิศวกรรมใด ๆ |
| `bjt_bias/templates/index.html` | ฟอร์ม + ตารางผล + บล็อก error/warning | เลขผลลัพธ์ที่ hardcode |
| `bjt_bias/static/style.css` | จัดหน้าให้อ่านง่ายพอ | — |
| `bjt_bias/tests/test_engineering.py` | สูตร, 3 region, validation, meta-test ของ check | — |
| `bjt_bias/tests/test_app.py` | GET 200, POST ถูกต้องเห็นผล, POST ผิดเห็น error ไม่ 500 | — |
| `bjt_bias/requirements.txt` | Flask, pytest | — |
| `bjt_bias/README.md` | วิธีติดตั้ง/รัน/ทดสอบ | — |

route contract: ฟิลด์ชื่อ `vcc, r1, r2, rc, re, beta, vbe`, หน่วยใน label ของฟอร์ม
ตัวเลขแสดง **6 significant figures** ด้วย `format(value, ".6g")` หน่วย A / V
(ไม่ใช้ทศนิยมคงที่ 6 ตำแหน่ง เพราะ `IB` ระดับ 1e-5 A จะเหลือเลขนัยสำคัญเดียว
และไม่ใช้ µA/mA prefix ตามที่ตัดออกจาก scope — สัญกรณ์วิทยาศาสตร์ยอมรับได้)

## 8. ตัวอย่างคำนวณด้วยมือ (ใช้เป็นหลักฐานว่า backend คำนวณจริง)

Input: `VCC=12, R1=10000, R2=2200, RC=1000, RE=470, beta=150, VBE=0.7`

```
VBB = 2.163934 V      RB = 1803.278689 ohm
IB  = 2.01164e-5 A    IC = 3.01746e-3 A    IE = 3.03757e-3 A
VE  = 1.42766 V       VC = 8.98254 V       VCE = 7.55489 V
region = active
```

ทดสอบ assert ค่าเหล่านี้ที่ 5 significant figures (delta สัมพัทธ์ `1e-5`)
ทั้งสองวิธีต้องให้ผลตรงกันที่ relative tolerance `1e-9`

## 9. เกณฑ์ตรวจรับ

| # | เกณฑ์ | วิธีพิสูจน์ |
|---|---|---|
| AC1 | backend คำนวณจริง ไม่ hardcode | test อย่างน้อย 3 ชุด input ให้ผลต่างกันและตรงกับค่าคำนวณมือ |
| AC2 | เดโม localhost ได้ | เปิด `http://127.0.0.1:5000` ได้ 200 และกรอกตัวอย่างข้อ 8 เห็นตัวเลขตามนั้น |
| AC3 | validation ไม่พัง | test_client: ค่าว่าง/ตัวอักษร/ติดลบ/ศูนย์/`beta<=0` → เห็น error ไม่มี 500 |
| AC4 | region ถูกต้อง | test 3 เคสที่สร้างขึ้น: active, cutoff (`VBB<VBE` → ค่าที่รายงานเป็นศูนย์ตามข้อ 5), saturation (`VCE<=0.2`) |
| AC5 | independent check มีความหมาย | เคสปกติ PASS, เคส cutoff ยัง PASS (เทียบผลดิบ), และเคสที่จงใจทำให้วิธีหนึ่งเพี้ยนต้อง FAIL |
| AC6 | test ผ่านจริง | รัน `python -m pytest -q` แล้วรายงานจำนวน test และผลจริง |
| AC7 | แยกชั้นจริง | `python -c "import bjt_bias.engineering"` ทำงานได้โดยไม่ต้อง import app และไม่มีสูตรใน `app.py`/template |
| AC8 | ขึ้น GitHub | commit และ push ขึ้น `origin/main` ภายในวันนี้ |

## 10. สิ่งที่เหลือให้ผู้สร้างตัดสินใจ

- รายละเอียด CSS และการจัดวาง
- ถ้อยคำของข้อความ error/warning ภาษาไทย
- ชื่อ test และโครงสร้างภายในไฟล์ test
- พอร์ตของ dev server (ค่าเริ่มต้น 5000)

## 11. ขั้นถัดไป

เมื่อเอกสารนี้อนุมัติ → `writing-plans` สร้างแผนแบบ task ย่อยที่ผูกกับความรับผิดชอบของไฟล์ และต้องทำจบในคาบ
