"""Repair knowledge base for phones, cars and home appliances.

Sources (real, public datasets under data/raw/):
- MyFixit (Nabizadeh et al., LREC 2020): iFixit repair manuals for Phone,
  Appliance and Car and Truck categories, CC BY-NC-SA 3.0.
- MechanicDB OBD-II sample: DTC codes -> ranked fixes -> replacement parts.

Each device type gets a small component taxonomy with a platform fault code
(e.g. PH-BATT). Guides are tagged with a component from their subject/title;
a technician's free-text issue is mapped to a component the same way, so
retrieval and fine-tuning share one vocabulary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ASSET_TYPES = ("phone", "car", "appliance")

IDENTIFIER_KIND = {"phone": "IMEI", "car": "VIN", "appliance": "SERIAL"}
USAGE_UNIT = {"phone": "battery_cycles", "car": "km", "appliance": "cycles"}

MYFIXIT_FILES = {
    "phone": ["Phone.json"],
    "appliance": ["Appliance.json"],
    "car": ["Car and Truck.json"],
}


@dataclass(frozen=True)
class Component:
    key: str
    fault_code: str
    label: str
    guide_kw: Tuple[str, ...]  # matched against guide subject/title
    issue_kw: Tuple[str, ...]  # matched against the technician's issue text
    symptoms: Tuple[str, ...]  # typical owner complaints (training prompts)
    severity: str
    check: str  # first diagnostic step
    qa_checks: Tuple[str, ...]


C = Component

COMPONENTS: Dict[str, List[Component]] = {
    "phone": [
        C("battery", "PH-BATT", "Battery", ("battery",),
          ("battery", "drain", "shuts down", "shut down", "hold a charge", "hold charge", "bulg", "swollen", "dies"),
          ("Battery drains very fast and the phone shuts down at around 20%",
           "Phone will not hold a charge and the back cover is bulging",
           "Battery percentage jumps and the phone dies unexpectedly"),
          "medium", "Check battery health and inspect the cell for swelling before opening the device.",
          ("New battery detected with 100% health", "No unexpected shutdown during a 15-minute stress test",
           "Charges from 20% to 80% normally")),
        C("display", "PH-DISP", "Display assembly",
          ("screen", "display", "lcd", "digitizer", "glass", "touch"),
          ("screen", "display", "crack", "touch", "lines", "flicker", "black screen", "lcd", "glass"),
          ("Screen is cracked and touch does not respond in the lower half",
           "Display shows green lines and flickers",
           "Black screen but the phone still rings and vibrates"),
          "high", "Inspect the display assembly and run a touch-grid test to confirm the fault.",
          ("Full touch-grid test passes", "No dead pixels or lines on solid-colour test",
           "Brightness and proximity sensor work")),
        C("charging", "PH-CHRG", "Charging port",
          ("charging", "charge port", "dock connector", "usb", "lightning", "charger", "port", "connector assembly"),
          ("not charging", "charging", "cable", "port", "usb", "lightning", "loose"),
          ("Phone charges only when the cable is held at an angle",
           "Phone is not charging and the cable is not detected",
           "Charging port is loose and data transfer fails"),
          "medium", "Inspect the charging port for lint, corrosion or bent pins and test with a known-good cable.",
          ("Charges with the original cable without wiggling", "Data connection to a computer works",
           "Port is free of debris and corrosion")),
        C("camera", "PH-CAM", "Camera module", ("camera", "lens", "flash"),
          ("camera", "photo", "lens", "focus", "flash", "blurry"),
          ("Rear camera shows a black screen", "Photos are blurry and the camera cannot focus"),
          "low", "Open the camera app on every lens to confirm which module has failed.",
          ("Front and rear cameras open and focus", "Flash fires", "Video records with audio")),
        C("audio", "PH-AUDIO", "Speaker / microphone",
          ("speaker", "earpiece", "loudspeaker", "microphone", "mic", "headphone", "audio", "ringer", "vibrat"),
          ("sound", "speaker", "hear", "mic", "audio", "crackl", "headphone", "vibrat", "earpiece"),
          ("Callers cannot hear me and the earpiece crackles", "No sound from the loudspeaker; ringtone is silent"),
          "medium", "Make a test call and record a voice memo to isolate the faulty audio component.",
          ("Test call: both parties hear clearly", "Loudspeaker plays at full volume without distortion",
           "Microphone records clean audio")),
        C("buttons", "PH-BTN", "Buttons / switches",
          ("button", "key", "keypad", "switch", "power", "volume", "home"),
          ("button", "key", "stuck", "volume", "home button", "power button"),
          ("Power button is stuck and does not respond", "Volume buttons are unresponsive"),
          "low", "Test every physical button in a diagnostic app to confirm which switch fails.",
          ("All physical buttons register", "Power button locks and unlocks reliably")),
        C("logic", "PH-LOGIC", "Logic board",
          ("motherboard", "logic board", "daughterboard", "board", "cpu", "pcb"),
          ("boot", "restart", "won't turn on", "not turn on", "no power", "loop", "dead"),
          ("Phone is stuck in a boot loop", "Phone does not power on even when charged"),
          "high", "Measure current draw at power-on to confirm a logic-board fault.",
          ("Device boots and stays on for 30 minutes", "IMEI and baseband are intact after repair")),
        C("radio", "PH-RF", "Antenna / SIM / wireless",
          ("antenna", "sim", "wifi", "wi-fi", "bluetooth", "gps", "signal"),
          ("signal", "sim", "network", "wifi", "wi-fi", "bluetooth", "gps"),
          ("No signal and the SIM card is not detected", "Wi-Fi keeps disconnecting"),
          "medium", "Test with a known-good SIM and check signal strength in field-test mode.",
          ("SIM detected and calls connect", "Wi-Fi and Bluetooth pair normally")),
        C("housing", "PH-HOUS", "Housing / back cover",
          ("cover", "housing", "case", "frame", "back", "bezel", "midframe", "rear panel"),
          ("back glass", "housing", "frame", "cover", "bent"),
          ("Back glass is shattered", "Housing is bent and the buttons are loose"),
          "low", "Inspect the frame and rear panel for cracks or bending.",
          ("Housing fits flush with no gaps", "Adhesive / water-resistance seal reapplied")),
    ],
    "appliance": [
        C("heating", "AP-HEAT", "Heating element / thermostat",
          ("heating element", "heater", "thermostat", "thermal fuse", "element", "heat", "thermistor"),
          ("not heating", "not heat", "doesn't heat", "won't heat", "no heat", "heat", "cold", "thermostat", "warm"),
          ("Appliance turns on but does not heat", "Heats unevenly and trips the thermal cut-out"),
          "medium", "Measure heating-element and thermal-fuse continuity with a multimeter.",
          ("Reaches the set temperature within spec", "Thermal cut-out does not trip during a full cycle")),
        C("water", "AP-WATER", "Pump / valve / hose",
          ("pump", "drain", "hose", "valve", "inlet", "water", "tank", "float", "level sensor"),
          ("drain", "water", "leak", "pump", "fill", "hose", "flood"),
          ("Water does not drain at the end of the cycle", "Water leaks from underneath the appliance",
           "Machine will not fill with water"),
          "high", "Check the drain filter and hoses for blockage before replacing the pump or valve.",
          ("Drains fully within the cycle time", "No leaks after a full cycle")),
        C("motor", "AP-MOTOR", "Motor / drive",
          ("motor", "belt", "brush", "fan", "bearing", "gear", "clutch", "drive", "suspension"),
          ("spin", "motor", "noise", "grind", "hum", "belt", "rattle", "vibrat", "unbalance"),
          ("Motor hums but the drum or blade does not spin", "Loud grinding noise while running"),
          "medium", "Check motor windings, brushes and the drive belt or clutch for wear.",
          ("Motor runs at full speed without noise", "Current draw within the rated value")),
        C("control", "AP-CTRL", "Control board / switches",
          ("control board", "control unit", "electronic control", "board", "relay", "switch", "button",
           "timer", "knob", "display", "sensor", "pcb", "panel"),
          ("button", "panel", "display", "control", "program", "timer", "relay", "knob"),
          ("Control panel is unresponsive and the buttons do nothing",
           "Display shows an error and the program will not start"),
          "medium", "Read the error code and test the control-board relays and switches.",
          ("All programs start from the control panel", "No error code after a full cycle")),
        C("power", "AP-POWER", "Power supply / cord",
          ("power cord", "cord", "plug", "fuse", "wiring", "wire", "cable", "battery", "charger", "charging"),
          ("dead", "no power", "won't turn on", "not turn on", "cord", "spark", "charging", "battery"),
          ("Appliance is completely dead with no lights", "Power cord is damaged and sparks"),
          "high", "Verify the mains supply, cord continuity and internal fuse.",
          ("Insulation-resistance test passes", "Appliance powers on reliably")),
        C("door", "AP-DOOR", "Door / lid / seal",
          ("door", "seal", "gasket", "latch", "lid", "hinge", "handle"),
          ("door", "latch", "seal", "gasket", "lid", "hinge"),
          ("Door does not latch so the cycle will not start", "Water leaks around the door seal"),
          "medium", "Inspect the door latch, interlock switch and seal for damage.",
          ("Door locks and the interlock is detected", "No leaks around the seal")),
        C("wear", "AP-WEAR", "Wear parts",
          ("filter", "blade", "brush roll", "roller", "bag", "wheel", "bumper", "carafe", "basket"),
          ("suction", "weak", "clog", "blade", "filter", "roller", "dull"),
          ("Suction or performance is much weaker than before", "Blade or roller is worn and stalls"),
          "low", "Inspect filters, blades and rollers for clogging or damage.",
          ("Performance restored to spec", "No abnormal noise")),
    ],
    "car": [
        C("brakes", "CR-BRAKE", "Brakes", ("brake", "rotor", "caliper", "pad", "shoe"),
          ("brake", "grind", "squeal", "pedal", "stopping"),
          ("Grinding noise when braking and longer stopping distance", "Brake pedal feels soft"),
          "high", "Measure pad thickness and rotor runout; check brake fluid level.",
          ("Brake pedal is firm with no pull under braking", "Road test: clean stop from 60 km/h")),
        C("engine", "CR-ENGINE", "Engine / service items",
          ("oil", "spark plug", "coolant", "timing", "radiator", "thermostat", "water pump", "air filter",
           "carburetor", "engine", "distributor", "ignition", "fuel"),
          ("check engine", "engine light", "emission", "engine", "oil", "overheat", "misfire", "stall",
           "rough idle", "coolant", "smoke"),
          ("Engine runs rough and the oil change is overdue", "Engine overheats in traffic"),
          "medium", "Scan for codes and inspect fluids, plugs and ignition parts.",
          ("No warning lights after a road test", "Fluids at correct level with no leaks")),
        C("electrical", "CR-ELEC", "Electrical system",
          ("battery", "alternator", "starter", "fuse", "headlight", "bulb", "light", "window", "switch", "sensor"),
          ("battery", "start", "crank", "light", "fuse", "electrical", "window"),
          ("Car cranks slowly and the battery light flickers", "Headlight is out"),
          "medium", "Load-test the battery and measure charging voltage at idle.",
          ("Charging voltage 13.8-14.6 V", "All lights and switches work")),
        C("suspension", "CR-SUSP", "Suspension / steering",
          ("tie rod", "strut", "shock", "suspension", "control arm", "ball joint", "wheel bearing", "cv",
           "axle", "steering"),
          ("clunk", "steering", "suspension", "pull", "vibration", "bearing", "noise over bumps"),
          ("Clunking noise over bumps and the steering pulls", "Humming noise from a wheel at speed"),
          "high", "Lift the car and check for play in joints, tie rods and bearings.",
          ("No play in steering components", "Alignment within spec after repair")),
        C("body", "CR-BODY", "Body / interior / audio",
          ("stereo", "radio", "speaker", "head unit", "cd", "dash", "seat", "door", "mirror", "handle", "tweeter"),
          ("radio", "stereo", "speaker", "door", "mirror", "seat", "dash"),
          ("Stereo has no sound", "Door handle is broken"),
          "low", "Inspect the affected trim or audio component and its wiring.",
          ("Component works and trim fits flush",)),
    ],
}

GENERAL = {
    "phone": C("general", "PH-GEN", "General phone fault", (), (), ("Phone has an intermittent fault",),
               "medium", "Run full device diagnostics to isolate the faulty module.",
               ("Full device diagnostics pass",)),
    "appliance": C("general", "AP-GEN", "General appliance fault", (), (), ("Appliance stopped working",),
                   "medium", "Inspect the appliance and read any error code.",
                   ("Appliance completes a full cycle",)),
    "car": C("general", "CR-GEN", "General vehicle fault", (), (), ("Warning light on",),
             "medium", "Run a full OBD-II scan and road test.", ("No codes return after a road test",)),
}

# Widely documented washer / dishwasher display codes (manufacturer manuals).
APPLIANCE_ERROR_CODES: Dict[str, Tuple[str, str]] = {
    "OE": ("water", "LG washer: drain error - water not pumped out"),
    "IE": ("water", "LG washer: water inlet error - machine does not fill"),
    "UE": ("motor", "LG washer: unbalanced load"),
    "DE": ("door", "LG washer: door not locked"),
    "5C": ("water", "Samsung washer: drain error"),
    "5E": ("water", "Samsung washer: drain error"),
    "4C": ("water", "Samsung washer: water supply error"),
    "4E": ("water", "Samsung washer: water supply error"),
    "DC": ("door", "Samsung washer: door open / lock fault"),
    "UB": ("motor", "Samsung washer: unbalanced load"),
    "E15": ("water", "Bosch dishwasher: water in base, leak protection triggered"),
    "E24": ("water", "Bosch dishwasher: drain hose kinked or blocked"),
    "E25": ("water", "Bosch dishwasher: drain pump blocked"),
    "F21": ("water", "Whirlpool washer: long drain"),
}

DTC_RE = re.compile(r"\b([PCBU][0-9][0-9A-F]{3})\b", re.I)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def components_for(asset_type: str) -> List[Component]:
    return COMPONENTS.get(asset_type, [])


def component_by_key(asset_type: str, key: str) -> Component:
    for comp in components_for(asset_type):
        if comp.key == key:
            return comp
    return GENERAL[asset_type]


def _score(text: str, keywords: Iterable[str]) -> int:
    return sum(len(kw) for kw in keywords if kw in text)


def classify_guide(asset_type: str, subject: str, title: str) -> Component:
    """Tag an iFixit guide; the subject wins over the full title."""
    for text in (_norm(subject), _norm(title)):
        if not text:
            continue
        best = max(components_for(asset_type), key=lambda c: _score(text, c.guide_kw), default=None)
        if best and _score(text, best.guide_kw) > 0:
            return best
    return GENERAL[asset_type]


def classify_issue(asset_type: str, issue: str, error_code: str = "") -> Component:
    """Map a technician's complaint (and optional appliance code) to a component."""
    code = (error_code or "").strip().upper()
    if asset_type == "appliance" and code in APPLIANCE_ERROR_CODES:
        return component_by_key("appliance", APPLIANCE_ERROR_CODES[code][0])
    text = _norm(issue)
    best = max(components_for(asset_type), key=lambda c: _score(text, c.issue_kw), default=None)
    if best and _score(text, best.issue_kw) > 0:
        return best
    return GENERAL[asset_type]


def _first_sentence(text: str, limit: int = 150) -> str:
    s = re.sub(r"\s+", " ", (text or "")).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    if m and len(m.group(1)) >= 20:
        s = m.group(1)
    if len(s) > limit:
        s = s[: limit - 1].rsplit(" ", 1)[0] + "…"
    return s


def _subject_from_title(title: str, device: str) -> str:
    s = title
    if device and device.lower() in s.lower():
        s = re.sub(re.escape(device), "", s, flags=re.I)
    s = re.sub(r"\b(replacement|replace|replacing|repairing|repair|how to|your|installing|install)\b", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" -:()") or title


@dataclass
class Guide:
    """One real repair procedure (iFixit guide or MechanicDB DTC fix list)."""

    ref_id: str
    source: str  # "iFixit (MyFixit)" | "MechanicDB"
    asset_type: str
    family: str
    device: str
    title: str
    subject: str
    component: str
    fault_code: str
    steps: List[str]
    tools: List[str] = field(default_factory=list)
    parts: List[str] = field(default_factory=list)
    url: str = ""
    est_minutes: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Guide":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


def load_myfixit(raw_dir: Path) -> List[Guide]:
    guides: List[Guide] = []
    for asset_type, files in MYFIXIT_FILES.items():
        for name in files:
            path = Path(raw_dir) / name
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                steps = [s.get("Text_raw", "").strip() for s in row.get("Steps", [])]
                steps = [s for s in steps if s]
                if not steps:
                    continue
                device = row.get("Category") or ""
                subject = (row.get("Subject") or "").strip() or _subject_from_title(row["Title"], device)
                comp = classify_guide(asset_type, subject, row["Title"])
                tools = [t.get("Name", "") for t in row.get("Toolbox", []) if t.get("Name")]
                guides.append(
                    Guide(
                        ref_id=f"ifixit-{row['Guidid']}",
                        source="iFixit (MyFixit)",
                        asset_type=asset_type,
                        family=(row.get("Ancestors") or [""])[0],
                        device=device,
                        title=row["Title"],
                        subject=subject,
                        component=comp.key,
                        fault_code=comp.fault_code,
                        steps=steps,
                        tools=tools,
                        parts=[f"{subject} ({device})" if device else subject],
                        url=row.get("Url", ""),
                        est_minutes=min(180, 10 + 4 * len(steps)),
                    )
                )
    return guides


def load_mechanicdb(raw_dir: Path) -> List[Guide]:
    """One Guide per DTC: ranked fixes become the steps, parts come from the fix list."""
    import pandas as pd

    base = Path(raw_dir)
    joined = base / "dtc_fixes_joined.parquet"
    if not joined.exists():
        return []
    df = pd.read_parquet(joined).sort_values(["dtc_code", "probability_rank"])
    parts_df = pd.read_parquet(base / "replacement_parts.parquet")
    parts_by_fix: Dict[int, List[str]] = {}
    for rec in parts_df.to_dict("records"):
        parts_by_fix.setdefault(int(rec["fix_id"]), []).append(str(rec["part_name"]))

    guides: List[Guide] = []
    for code, grp in df.groupby("dtc_code", sort=True):
        first = grp.iloc[0]
        steps: List[str] = []
        parts: List[str] = []
        minutes = 0.0
        for rec in grp.to_dict("records")[:3]:
            head = re.sub(r"^\s*\d+[.)]\s*", "", str(rec["step_by_step_instructions"]))
            head = re.split(r"•|\s\d+[.)]\s", head)[0]
            steps.append(f"{rec['fix_title']}: " + _first_sentence(head, 140))
            parts.extend(parts_by_fix.get(int(rec["fix_id"]), []))
            minutes += float(rec.get("est_labor_hours") or 0) * 60
        guides.append(
            Guide(
                ref_id=f"mechanicdb-{code}",
                source="MechanicDB",
                asset_type="car",
                family=str(first["system_category"]),
                device=str(first.get("oem_make") or "Any OBD-II vehicle"),
                title=f"{code} {first['short_description']}",
                subject=str(first["short_description"]),
                component=str(first["fault_family"]),
                fault_code=str(code),
                steps=steps,
                parts=list(dict.fromkeys(parts))[:5],
                est_minutes=int(minutes) or 60,
                description=_first_sentence(str(first["detailed_technical_explanation"]), 260),
            )
        )
    return guides


def condensed_steps(guide: Guide, limit: int = 4) -> List[str]:
    """Pick up to `limit` evenly spaced steps, first sentence each."""
    steps = guide.steps
    if len(steps) <= limit:
        picked = steps
    else:
        idx = sorted({round(i * (len(steps) - 1) / (limit - 1)) for i in range(limit)})
        picked = [steps[i] for i in idx]
    return [_first_sentence(s) for s in picked]


def extract_dtc(text: str) -> str:
    m = DTC_RE.search(text or "")
    return m.group(1).upper() if m else ""
