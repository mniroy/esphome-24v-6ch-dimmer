#!/usr/bin/env python3
"""
JLCPCB Manufacturing Files Exporter for 24V DC 6-Channel Dimmer.
Generates:
1. GERBER-dimmer_6ch.zip (Direct drag-and-drop upload for JLCPCB PCB fabrication)
2. BOM-dimmer_6ch.csv (JLCPCB PCBA BOM format with exact LCSC Part Numbers)
3. CPL-dimmer_6ch.csv (JLCPCB PCBA Component Placement List / Centroid file)
"""

import os
import sys
import shutil
import zipfile
import subprocess
import csv

PRJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB_FILE = os.path.join(PRJ_DIR, "dimmer_6ch.kicad_pcb")
OUT_DIR = os.path.join(PRJ_DIR, "manufacturing", "jlcpcb")
GERBERS_TMP = os.path.join(OUT_DIR, "gerbers_tmp")

KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

# Precise LCSC Part Numbers mapped by component Reference or Value
LCSC_MAP = {
    # Power MOSFETs
    "AOD4184A": "C428236",      # N-MOSFET 40V 50A TO-252 (DPAK)
    "AOD403": "C28969",         # P-MOSFET -30V -70A TO-252 (DPAK)
    
    # Power IC & Regulators
    "XL1509-5.0": "C61063",     # 2A 150kHz Buck Converter SOIC-8
    "W5500": "C32843",          # Hardwired TCP/IP SPI Ethernet Controller LQFP-48
    "AMS1117-3.3": "C6186",     # 3.3V 1A LDO Regulator SOT-223
    
    # Diodes & Protection
    "SS34": "C2400",            # 3A 40V Schottky Diode SMA
    "BZT52C12": "C80671",       # 12V 500mW Zener Diode SOD-123
    "SMBJ28A": "C98226",        # 28V 600W TVS Diode SMB
    
    # Passive Pass-Through & Inductors
    "33uH 3A": "C168344",       # Shielded SMD Power Inductor 6045
    "25MHz": "C112312",         # SMD Crystal 3225-4P 25.000MHz 18pF
    
    # Resistors 0805
    "100R": "C17414",           # 100 Ohm 5% 0805
    "1k": "C17513",             # 1k Ohm 5% 0805
    "10k": "C17415",            # 10k Ohm 5% 0805
    "100k": "C17407",           # 100k Ohm 5% 0805
    "12.4k": "C25744",          # 12.4k Ohm 1% 0805 (W5500 EXRES1)
    
    # Capacitors
    "100nF": "C49678",          # 100nF 50V X7R 0805
    "10uF": "C15850",           # 10uF 25V X5R 0805
    "10uF 50V": "C13585",       # 10uF 50V X7R 1206
    "100uF 35V": "C331289",     # 100uF 35V Radial 6.3x11mm Electrolytic
    "220uF 16V": "C331301",     # 220uF 16V Radial 6.3x11mm Electrolytic
    "470uF 35V": "C331317",     # 470uF 35V Radial 10x16mm Low-ESR Electrolytic
    
    # LEDs
    "LED": "C2297",             # 0805 SMD LED Green
    "LED GRN": "C2297",         # 0805 SMD LED Green
    
    # Connectors & Sockets
    "15A FUSE": "C236378",      # Keystone 3568 Mini Blade Fuse Holder
    "24V_IN": "C8465",          # 5.08mm 2-Pin Screw Terminal
    "CH1": "C8465",
    "CH2": "C8465",
    "CH3": "C8465",
    "CH4": "C8465",
    "CH5": "C8465",
    "CH6": "C8465",
    "HR911105A LAN": "C12074",  # HanRun HR911105A RJ45 MagJack
    "ESP32-DevKit-30P": "C225447" # 1x15 2.54mm Female Pin Header Socket
}

def export_gerbers():
    print("[1/4] Exporting Gerber & Drill files via kicad-cli...")
    if os.path.exists(GERBERS_TMP):
        shutil.rmtree(GERBERS_TMP)
    os.makedirs(GERBERS_TMP, exist_ok=True)
    
    # Gerbers
    cmd_gbr = [
        KICAD_CLI, "pcb", "export", "gerbers",
        "--output", GERBERS_TMP,
        "--subtract-soldermask",
        "--check-zones",
        PCB_FILE
    ]
    subprocess.check_call(cmd_gbr)
    
    # Drill
    cmd_drl = [
        KICAD_CLI, "pcb", "export", "drill",
        "--output", GERBERS_TMP,
        "--format", "excellon",
        "--excellon-units", "mm",
        PCB_FILE
    ]
    subprocess.check_call(cmd_drl)

def create_gerber_zip():
    print("[2/4] Packaging GERBER-dimmer_6ch.zip for JLCPCB...")
    zip_path = os.path.join(OUT_DIR, "GERBER-dimmer_6ch.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(GERBERS_TMP)):
            fpath = os.path.join(GERBERS_TMP, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, arcname=fname)
    print(f"  -> Created: {zip_path} ({os.path.getsize(zip_path)} bytes)")

def generate_jlcpcb_bom_cpl():
    print("[3/4] Extracting Footprints and generating JLCPCB BOM & CPL...")
    sys.path.append("/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/lib/python3.9/site-packages")
    import pcbnew
    
    board = pcbnew.LoadBoard(PCB_FILE)
    
    # Group parts for BOM
    # Key: (Comment/Value, Footprint, LCSC Part #) -> list of refs
    bom_groups = {}
    cpl_rows = []
    
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        val = fp.GetValue()
        pkg = str(fp.GetFPID().GetLibItemName())
        pos = fp.GetPosition()
        mid_x = round(pcbnew.ToMM(pos.x), 2)
        mid_y = round(-pcbnew.ToMM(pos.y), 2) # JLCPCB standard Cartesian (Y positive upwards)
        rot = round(fp.GetOrientation().AsDegrees() % 360.0, 1)
        layer = "Top" if fp.GetLayer() == pcbnew.F_Cu else "Bottom"
        
        # Skip mounting holes in SMT BOM/CPL
        if ref.startswith("H") and "MountingHole" in pkg:
            continue
            
        lcsc = LCSC_MAP.get(val, LCSC_MAP.get(ref, ""))
        
        # Group for BOM
        bom_key = (val, pkg, lcsc)
        bom_groups.setdefault(bom_key, []).append(ref)
        
        # CPL row
        cpl_rows.append({
            "Designator": ref,
            "Val": val,
            "Package": pkg,
            "Mid X": f"{mid_x:.2f}",
            "Mid Y": f"{mid_y:.2f}",
            "Rotation": f"{rot:.1f}",
            "Layer": layer
        })

    # Write BOM
    bom_path = os.path.join(OUT_DIR, "BOM-dimmer_6ch.csv")
    with open(bom_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, pkg, lcsc), refs in bom_groups.items():
            refs_str = ",".join(refs)
            writer.writerow([val, refs_str, pkg, lcsc])
    print(f"  -> Created: {bom_path}")

    # Write CPL
    cpl_path = os.path.join(OUT_DIR, "CPL-dimmer_6ch.csv")
    with open(cpl_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
        writer.writeheader()
        for row in cpl_rows:
            writer.writerow(row)
    print(f"  -> Created: {cpl_path}")

def cleanup():
    print("[4/4] Cleaning temporary files...")
    if os.path.exists(GERBERS_TMP):
        shutil.rmtree(GERBERS_TMP)
    print("Done! All JLCPCB manufacturing files are ready in:", OUT_DIR)

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    export_gerbers()
    create_gerber_zip()
    generate_jlcpcb_bom_cpl()
    cleanup()
