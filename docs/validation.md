# Lab 03 — Browser Acceptance Record (A1–A5)

ค่าในตารางนี้เป็น **ค่าอ้างอิงอิสระที่คำนวณจากสมการในใบงาน** ไม่ได้อ่านจากโปรแกรมที่กำลังตรวจ
ห้ามใช้ค่าจากโค้ดเป็นคำตอบอ้างอิง

## ข้อมูลร่วม

`VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
เกณฑ์ผลต่าง: `IC` ไม่เกิน `0.01 mA`, `VCE` ไม่เกิน `0.02 V` เมื่อเทียบกับค่าที่ยังไม่ปัดเศษ
(หน้าเว็บแสดง 6 significant figures)

## การคำนวณอิสระ

| กรณี | สมการที่ใช้ | ผลที่คำนวณได้ |
|---|---|---|
| A1 Divider | `VTH = 12·22/(100+22) = 2.163934 V`, `RTH = 100·22/(100+22) = 18.032787 kΩ`, `IB = (VTH−0.7)/(RTH+101·1k)` | `IB = 12.2986 µA`, `IC = 1.22986 mA`, `VCE = 8.05216 V` |
| A2 Fixed | `IB = (12−0.7)/1M = 11.3 µA`, `VE = 0`, `VCE = 12 − IC·2.2k` | `IC = 1.13000 mA`, `VCE = 9.51400 V` |
| A3 Emitter | `IB = 11.3/(1M + 101·1k) = 10.2634 µA`, `VE = IE·1k` | `IC = 1.02634 mA`, `VCE = 8.70545 V` |
| A4 Emitter | `IB = 11.3/(1M + 101·2k) = 9.40100 µA`, `VE = IE·2k` | `IC = 0.94010 mA` (หน้าเว็บแสดง `940.1 µA`), `VCE = 8.03278 V` |

**ทำนายก่อนรัน A4:** เมื่อเปลี่ยน `RE` จาก 1 เป็น 2 kΩ โดยคงค่าอื่นไว้ ตัวหาร
`RB + (β+1)RE` เพิ่มขึ้น → `IB` ลดลง → **`IC` ต้องลดลงจาก A3** (1.02634 → 0.94010 mA)

## ตารางผล

| ID | วิธีตรวจ | อินพุต | คาดหมายก่อนรัน | เห็นจริง (พร้อมหน่วย) | สถานะ | หลักฐาน |
|---|---|---|---|---|---|---|
| A1 · โหมดเดิม | Playwright (Python/Chrome) | Divider R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | `IC 1.22986 mA`, `VCE 8.05216 V` และตรงกับ Lab 2 ก่อนแก้ | `IC 1.22986 mA`, `VCE 8.05216 V`, `IB 12.2986 µA` | PASS | DOM text: `DC BIAS RESULTS · VOLTAGE DIVIDER BIAS` |
| A2 · Fixed | Playwright (Python/Chrome) | Fixed RB=1 MΩ (กรอก `1` + หน่วย MΩ หรือ `1000` + kΩ) ไม่กรอก RE | `IC 1.13000 mA`, `VCE 9.51400 V` | `IC 1.13 mA`, `VCE 9.514 V`, `VE 0 V`, `IB 11.3 µA` | PASS | `docs/evidence-a2.png` + DOM text `DC BIAS RESULTS · FIXED BIAS` |
| A2-megaohm · หน่วยใหม่ | Playwright (Python/Chrome) | Fixed RB=`1` MΩ ไม่กรอก RE (ตรวจกรณีที่โจทย์ระบุ `1 MΩ` ตรง ๆ) | เท่ากับ A2 ทุกประการ | `IC 1.13 mA`, `VC 9.514 V`, `VCE 9.514 V`, ไม่มี error | PASS | DOM text + ผลจาก Chrome (รันซ้ำหลังเพิ่มหน่วย MΩ) |
| A3 · Emitter | Playwright (Python/Chrome) | Emitter RB=1 MΩ, RE=1 kΩ | `IC 1.02634 mA`, `VCE 8.70545 V` | `IC 1.02634 mA`, `VCE 8.70545 V`, `VE 1.0366 V` | PASS | DOM text `DC BIAS RESULTS · EMITTER BIAS` |
| A4 · เปลี่ยนค่าเดียว | Playwright (Python/Chrome) | เหมือน A3 แต่ RE=2 kΩ | `IC` ลดลง (ทำนายไว้); `0.94010 mA`, `VCE 8.03278 V` | `IC 940.1 µA` (= 0.9401 mA, ลดลงจาก A3), `VCE 8.03278 V`, `VE 1.899 V` | PASS | DOM text `DC BIAS RESULTS · EMITTER BIAS` |
| A5 · อินพุตผิด | Playwright (Python/Chrome) | Fixed RB=0 | ข้อความ `ต้องมากกว่าศูนย์`, เว็บไม่ล่ม, ไม่แสดงผลรอบก่อน | ข้อความ `ต้องมากกว่าศูนย์`, ไม่มีบล็อก `DC Bias Results` | PASS | DOM error text from the live page |

**วิธีที่ใช้จริง:** เปิด Chrome (headless) ด้วย Playwright สำหรับ Python ที่ติดตั้ง **เฉพาะใน
`.venv` ของ worktree** (dev-only ไม่ได้ใส่ `requirements.txt` และไม่ได้ติดตั้ง Node)
สคริปต์เปิด `http://127.0.0.1:5000/` ทุกกรณี เลือกโหมด → กด `เปลี่ยนโหมด` → กรอกฟอร์มจริง
→ กดคำนวณ → อ่านข้อความจากหน้าเว็บที่เพิ่ง render และเก็บ screenshot ของ A2

## ตรวจ Fixed Bias แบบอิสระ (ตามที่ขอเพิ่ม)

คำนวณด้วยเลขศาสตร์ธรรมดา **ไม่ import โค้ดของแอป** ที่ `VCC=12 V, RC=2200 Ω, β=100, VBE=0.70 V`
และ `VE = 0` (Fixed) แล้วเทียบกับผลที่แอป render จริง:

| RB | IB = (12−0.7)/RB | IC = 100·IB | VC = 12 − IC·2200 | VCE = VC | ผลจากแอป | Region | สถานะ |
|---|---|---|---|---|---|---|---|
| 1 MΩ (`megaohm`) | 11.3 µA | 0.00113 A | 9.514 V | 9.514 V | `IC 1.13 mA`, `VCE 9.514 V` | active | ตรงกัน |
| 470 kΩ | 24.04255319 µA | 0.002404255319 A | 6.710638298 V | 6.710638298 V | `IC 2.40426 mA`, `VCE 6.71064 V` | active | ตรงกัน |
| 100 kΩ | 113 µA | 0.0113 A | −12.86 V | −12.86 V | `IC 11.3 mA`, `VCE −12.86 V` | **model-limit** + warning | ตรงกัน |

**สรุป:** โหมด Fixed คำนวณถูกต้องตามสมการในใบงานทุกกรณี รวมกรณีที่ผลออกติดลบ
(ซึ่งแอปไม่ได้แกล้งทำเป็น cutoff/saturation แต่แจ้งว่าแบบจำลอง Forward Active ใช้ไม่ได้
ตามที่ออกแบบไว้) สาเหตุของ `VC = −2474 V` ที่เคยเห็นคือฟอร์มเดิมไม่มีหน่วย MΩ
พอกรอก `1` ตามโจทย์ (`RB = 1 MΩ`) โดย dropdown อยู่ที่ kΩ → RB กลายเป็น 1 kΩ
การเพิ่มตัวเลือก MΩ แก้จุดนี้โดยตรง

**ทำไมไม่ใช่ Playwright MCP:** session นี้ไม่มี browser tool (`browser_navigate`,
`browser_snapshot`) และไม่มี `node`/`npx` บน PATH สำหรับ `@playwright/mcp` ตามที่
`opencode.json` ตั้งค่าไว้ ไฟล์ config ยังอยู่ใน repo เพื่อให้รันผ่าน MCP ได้บนเครื่องที่มี
Node ตามใบงาน ไม่มีการใช้ `curl` หรือการอ่านโค้ดแทนผลจากหน้าเว็บ

## หลักฐานที่ไม่ใช่ Browser (รันจริงแล้ว)

- ชุดทดสอบเดิม `pytest bjt_bias\tests -q` → **43 passed in 0.24s** (รันซ้ำหลังตรวจ browser)
- ตรวจสมการโดยตรง: Fixed `RB=1000 kΩ` ได้ `IC=1.13 mA`, `VCE=9.514 V`;
  Emitter `RE=1 kΩ` ได้ `IC≈1.02634 mA`, `VCE≈8.70545 V`;
  Emitter `RE=2 kΩ` ได้ `IC≈0.94010 mA`, `VCE≈8.03278 V`
- ตรวจ route ด้วย Flask test client: โหมดผิดได้ข้อความ `โหมดไม่ถูกต้อง`,
  `RB=0` ได้ `ต้องมากกว่าศูนย์` และไม่มีบล็อกผลลัพธ์, กด `เปลี่ยนโหมด` แล้วไม่มีผลค้าง

> รายการในหัวข้อนี้เป็นการตรวจฝั่งเซิร์ฟเวอร์เพิ่มเติม ส่วน browser PASS อยู่ในตาราง A1–A5 ด้านบน

## ไล่ข้อมูลหนึ่งรอบ (คำถามปิด Lab)

ถ้าคำนวณมือถูกแต่เปลี่ยน `RE` แล้วผลไม่เปลี่ยน ให้ตรวจตามลำดับ:
ค่าที่กรอกในฟอร์ม (`name="re"` / `re_unit`) → ชื่อฟิลด์ที่ Flask อ่านจาก `request.form`
→ การคูณ `UNIT_FACTORS` ตอน `parse_mode_inputs` → `analyze_emitter` ถูกเรียกจาก
`analyze_mode(MODE_EMITTER, ...)` → ค่า `result.ic` ที่ Jinja แสดง
แก้ทีละจุดแล้วรัน A3 → A4 ซ้ำ
