"""ngspice adapter for Lab 4 CE Voltage Divider reference circuit.

This module is Flask-free. It builds netlists, runs ngspice as an external
process, and parses plain-text outputs. It never fabricates simulation data.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Generic educational NPN model (approx. 2N3904). Replace with the
# instructor-provided starter model for official lab validation.
DEFAULT_BJT_MODEL_NAME = "Q2N3904_GENERIC"
DEFAULT_BJT_MODEL = (
    ".model Q2N3904_GENERIC NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 "
    "NE=1.259 ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 "
    "CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 "
    "TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)"
)

DEFAULT_SOURCE_AMPLITUDE_MV = 10.0  # peak mV
DEFAULT_SOURCE_FREQUENCY_HZ = 1000.0
DEFAULT_AC_POINTS_PER_DECADE = 20
DEFAULT_AC_FSTART_HZ = 10.0
DEFAULT_AC_FSTOP_HZ = 1_000_000.0
DEFAULT_TRAN_CYCLES = 5
DEFAULT_TRAN_POINTS_PER_CYCLE = 200
MAX_SOURCE_AMPLITUDE_MV = 1_000.0
MAX_SOURCE_FREQUENCY_HZ = 10_000_000.0
MIN_SOURCE_FREQUENCY_HZ = 0.1


class SpiceError(RuntimeError):
    """Raised when ngspice cannot be run or returns invalid output."""


@dataclass(frozen=True)
class SpiceRunConfig:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    beta: float
    vbe: float
    amplitude_mv: float = DEFAULT_SOURCE_AMPLITUDE_MV
    frequency_hz: float = DEFAULT_SOURCE_FREQUENCY_HZ
    model_name: str = DEFAULT_BJT_MODEL_NAME
    model_card: str = DEFAULT_BJT_MODEL


def ngspice_available(executable: str = "ngspice") -> bool:
    return shutil.which(executable) is not None


def ngspice_version(executable: str = "ngspice", timeout: float = 5.0) -> str | None:
    if not ngspice_available(executable):
        return None
    try:
        proc = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None
    text = (proc.stdout or proc.stderr or "").strip()
    return text.splitlines()[0].strip() if text else None


def _fmt_eng(value: float) -> str:
    """Format number for SPICE netlist; avoid locale issues."""
    if not math.isfinite(value):
        raise SpiceError("ค่าพารามิเตอร์ไม่ถูกต้อง")
    return f"{value:.12g}"


def _source_amplitude_v(amplitude_mv: float) -> float:
    return amplitude_mv / 1000.0


def build_ce_netlist(config: SpiceRunConfig, analysis: str) -> str:
    """Build a CE voltage-divider netlist for the requested analysis."""
    if analysis not in {"op", "ac", "tran"}:
        raise SpiceError("โหมดวิเคราะห์ SPICE ไม่ถูกต้อง")

    amp_v = _source_amplitude_v(config.amplitude_mv)
    freq = config.frequency_hz
    # Keep AC small-signal source at 1V for easy gain reading (V(out) is gain).
    ac_mag = 1.0
    lines = [
        "* Lab 04 CE Voltage Divider reference circuit",
        f"VCC vcc 0 DC {_fmt_eng(config.vcc)}",
        f"Vin in 0 DC 0 AC {_fmt_eng(ac_mag)} SIN(0 {_fmt_eng(amp_v)} {_fmt_eng(freq)})",
        f"R1 vcc b {_fmt_eng(config.r1)}",
        f"R2 b 0 {_fmt_eng(config.r2)}",
        f"RC vcc c {_fmt_eng(config.rc)}",
        f"RE e 0 {_fmt_eng(config.re)}",
        f"RL out 0 {_fmt_eng(config.rl)}",
        f"Cin in b {_fmt_eng(config.cin)}",
        f"Cout c out {_fmt_eng(config.cout)}",
        f"Q1 c b e {config.model_name}",
        config.model_card,
    ]

    if analysis == "op":
        lines += [
            ".control",
            "set noaskquit",
            "op",
            "print v(b) v(e) v(c) v(c,e) i(vcc)",
            "quit",
            ".endc",
            ".end",
        ]
        return "\n".join(lines) + "\n"

    if analysis == "ac":
        fstart = DEFAULT_AC_FSTART_HZ
        fstop = DEFAULT_AC_FSTOP_HZ
        if freq > 0:
            fstart = max(1.0, min(DEFAULT_AC_FSTART_HZ, freq / 100.0))
            fstop = max(freq * 10.0, 10_000.0)
            fstop = min(fstop, DEFAULT_AC_FSTOP_HZ)
            if fstop <= fstart:
                fstop = fstart * 10
        lines += [
            ".control",
            "set noaskquit",
            f"ac dec {DEFAULT_AC_POINTS_PER_DECADE} {_fmt_eng(fstart)} {_fmt_eng(fstop)}",
            "wrdata ac_output.txt v(out)",
            "quit",
            ".endc",
            ".end",
        ]
        return "\n".join(lines) + "\n"

    # tran
    period = 1.0 / freq
    tstop = DEFAULT_TRAN_CYCLES * period
    tstep = period / DEFAULT_TRAN_POINTS_PER_CYCLE
    lines += [
        ".control",
        "set noaskquit",
        f"tran {_fmt_eng(tstep)} {_fmt_eng(tstop)} 0 {_fmt_eng(tstep)}",
        "wrdata tran_output.txt v(in) v(out)",
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def _run_ngspice(netlist: str, workdir: Path, executable: str, timeout: float) -> subprocess.CompletedProcess[str]:
    circuit_path = workdir / "circuit.cir"
    log_path = workdir / "run.log"
    circuit_path.write_text(netlist, encoding="utf-8", newline="\n")
    try:
        proc = subprocess.run(
            [executable, "-b", "-o", str(log_path), str(circuit_path)],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SpiceError("ไม่พบ ngspice ใน PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SpiceError(f"ngspice ใช้เวลานานเกินกำหนด ({timeout:g}s)") from exc
    return proc


def _read_log(workdir: Path, proc: subprocess.CompletedProcess[str]) -> str:
    log_path = workdir / "run.log"
    file_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return "\n".join(part for part in [file_text, stdout, stderr] if part).strip()


def _assert_success(proc: subprocess.CompletedProcess[str], log_text: str) -> None:
    if proc.returncode != 0:
        tail = "\n".join(log_text.splitlines()[-20:])
        raise SpiceError(f"ngspice รันไม่สำเร็จ (exit {proc.returncode})\n{tail}".strip())
    lower = log_text.lower()
    fatal_markers = ["fatal error", "run simulation(s) aborted", "no such vector", "can't find model"]
    if any(marker in lower for marker in fatal_markers):
        tail = "\n".join(log_text.splitlines()[-20:])
        raise SpiceError(f"ngspice รายงานข้อผิดพลาด\n{tail}".strip())


def parse_op_output(log_text: str) -> dict[str, float]:
    """Parse DC operating point values from ngspice print output."""
    wanted = {
        "v(b)": "vb",
        "v(e)": "ve",
        "v(c)": "vc",
        "v(c,e)": "vce",
        "i(vcc)": "ic_probe",  # through VCC source; negative means flowing into source
    }
    found: dict[str, float] = {}
    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        # Typical: v(b) = 1.23456e+00
        for key, out_key in wanted.items():
            if line.lower().startswith(key + " ") or line.lower().startswith(key + "="):
                try:
                    value_text = line.split("=", 1)[1].strip().split()[0]
                    found[out_key] = float(value_text)
                except Exception:
                    continue
    missing = [k for k in ["vb", "ve", "vc", "vce", "ic_probe"] if k not in found]
    if missing:
        tail = "\n".join(log_text.splitlines()[-20:])
        raise SpiceError(f"ไม่พบค่า .op ที่ต้องการ: {', '.join(missing)}\n{tail}".strip())

    ic = -found["ic_probe"]
    ib_est = None
    # Not directly printed; leave None. Caller can compute from node voltages if needed.
    return {
        "vb": found["vb"],
        "ve": found["ve"],
        "vc": found["vc"],
        "vce": found["vce"],
        "ic": ic,
    }


def _parse_wrdata(path: Path, expected_columns: int) -> list[list[float]]:
    if not path.exists():
        raise SpiceError(f"ไม่พบไฟล์ผลลัพธ์ {path.name}")
    rows: list[list[float]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        # wrdata may include row index as first column in some modes; detect numeric.
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            continue
        if len(nums) < expected_columns:
            continue
        # If first column looks like integer index and there are extra columns, drop it.
        if len(nums) == expected_columns + 1 and abs(nums[0] - round(nums[0])) < 1e-9:
            nums = nums[1:]
        rows.append(nums[:expected_columns])
    if not rows:
        raise SpiceError(f"ไฟล์ผลลัพธ์ {path.name} ว่างหรืออ่านไม่ได้")
    return rows


def _read_numeric_rows(path: Path) -> list[list[float]]:
    if not path.exists():
        raise SpiceError(f"ไม่พบไฟล์ผลลัพธ์ {path.name}")
    rows: list[list[float]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            continue
        # Drop leading row index if present.
        if len(nums) >= 2 and abs(nums[0] - round(nums[0])) < 1e-9 and abs(nums[0]) < 1e12:
            # Heuristic: wrdata sometimes has integer row number in first col; keep if it looks like freq/time.
            # If second value is also monotonic-ish time/freq in typical ranges, first may be index.
            pass
        rows.append(nums)
    if not rows:
        raise SpiceError(f"ไฟล์ผลลัพธ์ {path.name} ว่างหรืออ่านไม่ได้")
    return rows


def parse_ac_output(workdir: Path) -> dict[str, list[float]]:
    """Parse wrdata AC output. Handles common 3-col (f,re,im) and 4-col (f,re,f,im) forms."""
    path = workdir / "ac_output.txt"
    rows = _read_numeric_rows(path)
    freq: list[float] = []
    gain_db: list[float] = []
    phase_deg: list[float] = []
    for nums in rows:
        if len(nums) >= 4:
            # Common: freq, re, freq, im
            f, vr, vi = nums[0], nums[1], nums[3]
        elif len(nums) == 3:
            f, vr, vi = nums[0], nums[1], nums[2]
        else:
            continue
        mag = math.sqrt(vr * vr + vi * vi)
        gain_db.append(20.0 * math.log10(max(mag, 1e-30)))
        phase_deg.append(math.degrees(math.atan2(vi, vr)))
        freq.append(f)
    if not freq:
        raise SpiceError("ไม่สามารถอ่านข้อมูล AC จากไฟล์ผลลัพธ์")
    return {"frequency_hz": freq, "gain_db": gain_db, "phase_deg": phase_deg}


def parse_tran_output(workdir: Path) -> dict[str, list[float]]:
    """Parse wrdata transient output. Handles common 4-col (t,vin,t,vout) and 3-col forms."""
    path = workdir / "tran_output.txt"
    rows = _read_numeric_rows(path)
    time_s: list[float] = []
    vin: list[float] = []
    vout: list[float] = []
    for nums in rows:
        if len(nums) >= 4:
            # Common: time, v(in), time, v(out)
            t, v_in, v_out = nums[0], nums[1], nums[3]
        elif len(nums) == 3:
            t, v_in, v_out = nums[0], nums[1], nums[2]
        else:
            continue
        if not all(math.isfinite(v) for v in (t, v_in, v_out)):
            continue
        time_s.append(t)
        vin.append(v_in)
        vout.append(v_out)
    if not time_s:
        raise SpiceError("ไม่สามารถอ่านข้อมูล transient จากไฟล์ผลลัพธ์")
    return {"time_s": time_s, "vin_v": vin, "vout_v": vout}


def run_analysis(
    config: SpiceRunConfig,
    analysis: str,
    executable: str = "ngspice",
    timeout: float = 30.0,
) -> dict[str, object]:
    """Run selected ngspice analysis and return parsed data."""
    if not ngspice_available(executable):
        raise SpiceError("ไม่พบ ngspice ใน PATH")

    netlist = build_ce_netlist(config, analysis)
    with tempfile.TemporaryDirectory(prefix="bjt_spice_") as td:
        workdir = Path(td)
        proc = _run_ngspice(netlist, workdir, executable=executable, timeout=timeout)
        log_text = _read_log(workdir, proc)
        _assert_success(proc, log_text)
        version = ngspice_version(executable)
        result: dict[str, object] = {
            "analysis": analysis,
            "engine": "ngspice",
            "engine_version": version,
            "model_name": config.model_name,
            "netlist": netlist,
            "log_tail": "\n".join(log_text.splitlines()[-40:]),
        }
        if analysis == "op":
            result["op"] = parse_op_output(log_text)
        elif analysis == "ac":
            result["ac"] = parse_ac_output(workdir)
        elif analysis == "tran":
            result["tran"] = parse_tran_output(workdir)
        else:
            raise SpiceError("โหมดวิเคราะห์ SPICE ไม่ถูกต้อง")
        return result
