#!/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
"""
Generate complete KiCad 10 PCB for DIN-Rail Mountable 24V DC 6-Channel LED Dimmer
with Top-Facing LAN (HR911105A + W5500) and Modular ESP32 DevKit USB-C (ESPHome).
All components selected for high availability in Indonesia (Tokopedia/Shopee/LCSC).
"""

import math
import os
import pcbnew
from PIL import Image

PRJ_DIR = os.path.dirname(os.path.abspath(__file__))
KICAD_FP_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LOCAL_FP_DIR = os.path.join(PRJ_DIR, "libs", "ESP32.pretty")

X_SHIFT = 26.0
BOARD_W = 126.0 + X_SHIFT  # 152.0 mm
BOARD_H = 72.0             # 72.0 mm standard UM72 DIN-rail carrier width!
CORNER_R = 3.0


def mm(val):
    return pcbnew.FromMM(val)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def pad_xy(fp, pad_name, pick="first"):
    matches = []
    for p in fp.Pads():
        if p.GetName() == str(pad_name):
            pos = p.GetPosition()
            matches.append((pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)))
    if not matches:
        raise KeyError(f"Pad {pad_name} not found in {fp.GetReference()}")
    if pick == "max_y":
        return max(matches, key=lambda c: c[1])
    if pick == "min_y":
        return min(matches, key=lambda c: c[1])
    if pick == "max_x":
        return max(matches, key=lambda c: c[0])
    return matches[0]


def add_net(board, name):
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def load_fp(lib_dir, fp_name, ref, val, x, y, angle=0.0, val_offset=(0, 2.8), ref_offset=(0, -2.8), show_val=True, show_ref=True, text_size=0.8, text_thick=0.13, ref_angle=0.0, val_angle=0.0):
    fp = pcbnew.FootprintLoad(lib_dir, fp_name)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetPosition(pt(x, y))
    if angle != 0.0:
        fp.SetOrientationDegrees(angle)

    ref_txt = fp.Reference()
    ref_txt.SetVisible(show_ref)
    ref_txt.SetLayer(pcbnew.F_SilkS)
    ref_txt.SetTextSize(pcbnew.VECTOR2I(mm(text_size), mm(text_size)))
    ref_txt.SetTextThickness(mm(text_thick))
    ref_txt.SetTextAngleDegrees(ref_angle)
    ref_txt.SetPosition(pt(x + ref_offset[0], y + ref_offset[1]))

    val_txt = fp.Value()
    val_txt.SetVisible(show_val)
    val_txt.SetLayer(pcbnew.F_SilkS)
    val_txt.SetTextSize(pcbnew.VECTOR2I(mm(text_size), mm(text_size)))
    val_txt.SetTextThickness(mm(text_thick))
    val_txt.SetTextAngleDegrees(val_angle)
    val_txt.SetPosition(pt(x + val_offset[0], y + val_offset[1]))
    return fp


def set_pad_net(fp, pad_names, net):
    if isinstance(pad_names, str):
        pad_names = [pad_names]
    for pad in fp.Pads():
        if pad.GetName() in pad_names:
            pad.SetNet(net)


def add_track(board, x1, y1, x2, y2, width_mm, layer, net):
    if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
        return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pt(x1, y1))
    t.SetEnd(pt(x2, y2))
    t.SetWidth(mm(width_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)
    return t


def add_route(board, pts, width_mm, layer, net):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        add_track(board, x1, y1, x2, y2, width_mm, layer, net)


def add_via(board, x, y, net, dia_mm=0.8, drill_mm=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetWidth(pcbnew.F_Cu, mm(dia_mm))
    v.SetDrill(mm(drill_mm))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetNet(net)
    board.Add(v)
    return v


def add_gnd_via_near(board, x, y, dx, dy, net_gnd, trace_w=0.5):
    vx, vy = x + dx, y + dy
    add_track(board, x, y, vx, vy, trace_w, pcbnew.F_Cu, net_gnd)
    add_via(board, vx, vy, net_gnd, dia_mm=0.85, drill_mm=0.4)


def add_silk_text(board, text, x, y, size_mm=1.0, thickness_mm=0.16, angle=0.0, bold=False, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pt(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size_mm), mm(size_mm)))
    t.SetTextThickness(mm(thickness_mm))
    t.SetLayer(layer)
    t.SetBold(bold)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    if angle != 0.0:
        t.SetTextAngleDegrees(angle)
    board.Add(t)
    return t


def add_board_outline(board):
    w, h, r = BOARD_W, BOARD_H, CORNER_R
    edges = [
        ((r, 0), (w - r, 0)),
        ((w, r), (w, h - r)),
        ((w - r, h), (r, h)),
        ((0, h - r), (0, r)),
    ]
    for (x1, y1), (x2, y2) in edges:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.15))
        seg.SetStart(pt(x1, y1))
        seg.SetEnd(pt(x2, y2))
        board.Add(seg)

    d = r * (1.0 - math.sqrt(0.5))
    corners = [
        ((0, r), (d, d), (r, 0)),
        ((w - r, 0), (w - d, d), (w, r)),
        ((w, h - r), (w - d, h - d), (w - r, h)),
        ((r, h), (d, h - d), (0, h - r)),
    ]
    for s, m, e in corners:
        arc = pcbnew.PCB_SHAPE(board)
        arc.SetShape(pcbnew.SHAPE_T_ARC)
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetWidth(mm(0.15))
        arc.SetArcGeometry(pt(*s), pt(*m), pt(*e))
        board.Add(arc)


def add_zone(board, net, layer, points_mm, priority=0, clearance_mm=0.3):
    zone = pcbnew.ZONE(board)
    zone.SetNet(net)
    zone.SetLayer(layer)
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(mm(clearance_mm))
    zone.SetMinThickness(mm(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(mm(0.25))
    zone.SetThermalReliefSpokeWidth(mm(0.35))

    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points_mm:
        outline.Append(mm(x), mm(y))
    board.Add(zone)
    return zone


def add_keepout_zone(board, points_mm):
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowZoneFills(True)
    lset = pcbnew.LSET()
    lset.AddLayer(pcbnew.F_Cu)
    lset.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(lset)

    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points_mm:
        outline.Append(mm(x), mm(y))
    board.Add(zone)
    return zone


def add_logo_from_png(board, png_path, x0, y0, target_width_mm=22.0):
    """Convert white/alpha logo.png into crisp filled silkscreen rectangles on F.SilkS."""
    im = Image.open(png_path).convert("RGBA")
    orig_w, orig_h = im.size
    new_w = 240
    new_h = max(1, int(round(orig_h * (new_w / orig_w))))
    im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

    pixel_size = target_width_mm / new_w
    pixels = im.load()

    for row in range(new_h):
        in_run = False
        run_start = 0
        for col in range(new_w + 1):
            is_on = False
            if col < new_w:
                r, g, b, a = pixels[col, row]
                if a > 128 and (r + g + b) / 3 > 128:
                    is_on = True
            if is_on and not in_run:
                in_run = True
                run_start = col
            elif not is_on and in_run:
                in_run = False
                rx1 = x0 + run_start * pixel_size
                rx2 = x0 + col * pixel_size
                ry1 = y0 + row * pixel_size
                ry2 = y0 + (row + 1.05) * pixel_size
                rect = pcbnew.PCB_SHAPE(board)
                rect.SetShape(pcbnew.SHAPE_T_RECT)
                rect.SetLayer(pcbnew.F_SilkS)
                rect.SetFilled(True)
                rect.SetWidth(mm(0.01))
                rect.SetStart(pt(rx1, ry1))
                rect.SetEnd(pt(rx2, ry2))
                board.Add(rect)


def build_board():
    board = pcbnew.BOARD()
    add_board_outline(board)
    S = X_SHIFT

    # 1. Nets
    net_gnd = add_net(board, "GND")
    net_24v_in = add_net(board, "+24V_IN")
    net_24v_fused = add_net(board, "+24V_FUSED")
    net_24v_bus = add_net(board, "+24V_BUS")
    net_rev_gate = add_net(board, "REV_GATE")
    net_5v = add_net(board, "+5V")
    net_3v3_eth = add_net(board, "+3V3_ETH")
    net_sw = add_net(board, "BUCK_SW")
    net_pwr_led = add_net(board, "PWR_LED_A")

    # LAN / W5500 Nets
    net_eth_clk = add_net(board, "ETH_CLK")
    net_eth_cs = add_net(board, "ETH_CS")
    net_eth_mosi = add_net(board, "ETH_MOSI")
    net_eth_miso = add_net(board, "ETH_MISO")
    net_eth_int = add_net(board, "ETH_INT")
    net_eth_rst = add_net(board, "ETH_RST")
    net_txp = add_net(board, "ETH_TXP")
    net_txn = add_net(board, "ETH_TXN")
    net_rxp = add_net(board, "ETH_RXP")
    net_rxn = add_net(board, "ETH_RXN")
    net_xi = add_net(board, "ETH_XI")
    net_xo = add_net(board, "ETH_XO")
    net_exres = add_net(board, "ETH_EXRES")
    net_1v2o = add_net(board, "ETH_1V2O")
    net_link_led = add_net(board, "ETH_LINK_LED")
    net_act_led = add_net(board, "ETH_ACT_LED")

    net_pwm = [add_net(board, f"PWM_CH{i}") for i in range(1, 7)]
    net_gate = [add_net(board, f"GATE_CH{i}") for i in range(1, 7)]
    net_out = [add_net(board, f"CH{i}_OUT-") for i in range(1, 7)]
    net_led = [add_net(board, f"LED_CH{i}_K") for i in range(1, 7)]

    # 2. Mounting Holes (M3) for UM72 DIN-rail brackets / standoffs
    for idx, (mx, my) in enumerate([(5, 5), (BOARD_W - 5, 5), (5, BOARD_H - 5), (BOARD_W - 5, BOARD_H - 5)], 1):
        mh = load_fp(
            f"{KICAD_FP_DIR}/MountingHole.pretty",
            "MountingHole_3.2mm_M3_Pad_Via",
            f"H{idx}", "M3", mx, my, show_val=False
        )
        mh.Reference().SetVisible(False)
        set_pad_net(mh, "1", net_gnd)
        board.Add(mh)

    # 3. Modular ESP32 DevKit USB-C (U2) at x = 10 + S (36.0), y = 11.0
    u2 = load_fp(
        LOCAL_FP_DIR, "ESP32-DevKit-USB-C",
        "U2", "ESP32-DevKit-30P", 10.0 + S, 11.0,
        ref_offset=(12.7, 13.0), val_offset=(12.7, 16.0)
    )
    set_pad_net(u2, ["14", "17"], net_gnd)
    set_pad_net(u2, "15", net_5v)
    eth_pins = ["6", "7", "8", "9", "10", "11"]
    eth_nets = [net_eth_rst, net_eth_int, net_eth_miso, net_eth_mosi, net_eth_cs, net_eth_clk]
    for pnum, enet in zip(eth_pins, eth_nets):
        set_pad_net(u2, pnum, enet)
    gpio_pins = ["21", "22", "24", "25", "26", "29"]
    for i, pin in enumerate(gpio_pins):
        set_pad_net(u2, pin, net_pwm[i])
    board.Add(u2)

    # Antenna Keep-Out Zone
    add_keepout_zone(board, [(8.5 + S, 0.5), (37.0 + S, 0.5), (37.0 + S, 9.3), (8.5 + S, 9.3)])

    # ESP32 Pinout Silkscreen Helpers
    add_silk_text(board, "5V", 6.2 + S, 46.56, size_mm=0.85, bold=True)
    add_silk_text(board, "GND", 5.8 + S, 44.02, size_mm=0.85, bold=True)
    add_silk_text(board, "USB-C", 22.7 + S, 59.0, size_mm=1.0, bold=True)
    add_silk_text(board, "ANTENNA KEEP-OUT", 22.7 + S, 2.0, size_mm=0.85)

    # 3B. Top-Facing DIN-Rail LAN / Ethernet Subsystem (HR911105A + W5500)
    # J_LAN: HanRun HR911105A at (22.5, 16.0) rotated 180 deg -> RJ45 port faces TOP EDGE (y=0)!
    j_lan = load_fp(
        LOCAL_FP_DIR,
        "RJ45_Hanrun_HR911105A_Horizontal",
        "J_LAN", "HR911105A LAN", 22.5, 16.0, angle=180.0,
        ref_offset=(-4.5, 6.0), val_offset=(-4.5, 8.0)
    )
    set_pad_net(j_lan, "1", net_txp)
    set_pad_net(j_lan, "2", net_txn)
    set_pad_net(j_lan, "3", net_rxp)
    set_pad_net(j_lan, ["4", "5", "9", "12"], net_3v3_eth)
    set_pad_net(j_lan, "6", net_rxn)
    set_pad_net(j_lan, ["8", "SH"], net_gnd)
    set_pad_net(j_lan, "10", net_link_led)
    set_pad_net(j_lan, "11", net_act_led)
    board.Add(j_lan)

    # U3: W5500 Ethernet Controller (LQFP-48) directly below J_LAN
    u3 = load_fp(
        f"{KICAD_FP_DIR}/Package_QFP.pretty",
        "LQFP-48_7x7mm_P0.5mm",
        "U3", "W5500", 18.0, 38.5, angle=0.0,
        ref_offset=(0.0, -6.2), val_offset=(0.0, 6.2)
    )
    set_pad_net(u3, "1", net_txn)
    set_pad_net(u3, "2", net_txp)
    set_pad_net(u3, ["3", "9", "14", "16", "19", "21", "23", "29", "48"], net_gnd)
    set_pad_net(u3, ["4", "8", "11", "15", "17", "28", "43", "44", "45"], net_3v3_eth)
    set_pad_net(u3, "5", net_rxn)
    set_pad_net(u3, "6", net_rxp)
    set_pad_net(u3, "10", net_exres)
    set_pad_net(u3, "22", net_1v2o)
    set_pad_net(u3, "25", net_link_led)
    set_pad_net(u3, "27", net_act_led)
    set_pad_net(u3, "30", net_xi)
    set_pad_net(u3, "31", net_xo)
    set_pad_net(u3, "32", net_eth_clk)
    set_pad_net(u3, "33", net_eth_cs)
    set_pad_net(u3, "34", net_eth_miso)
    set_pad_net(u3, "35", net_eth_mosi)
    set_pad_net(u3, "36", net_eth_int)
    set_pad_net(u3, "37", net_eth_rst)
    board.Add(u3)

    # Y1: 25MHz Crystal for W5500
    y1 = load_fp(
        f"{KICAD_FP_DIR}/Crystal.pretty",
        "Crystal_SMD_3225-4Pin_3.2x2.5mm",
        "Y1", "25MHz", 18.0, 50.0, angle=0.0,
        ref_offset=(0.0, -2.5), val_offset=(0.0, 2.5)
    )
    set_pad_net(y1, "1", net_xi)
    set_pad_net(y1, ["2", "4"], net_gnd)
    set_pad_net(y1, "3", net_xo)
    board.Add(y1)

    # R_EXRES: 12.4k 1% resistor for W5500 pin 10
    r_exres = load_fp(
        f"{KICAD_FP_DIR}/Resistor_SMD.pretty",
        "R_0805_2012Metric",
        "R_EX", "12.4k", 7.0, 38.5, angle=180.0,
        ref_offset=(0.0, -1.8), val_offset=(0.0, 1.8)
    )
    set_pad_net(r_exres, "1", net_exres)
    set_pad_net(r_exres, "2", net_gnd)
    board.Add(r_exres)

    # C_1V2: 100nF decoupling for W5500 1V2O
    c_1v2 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_SMD.pretty",
        "C_0805_2012Metric",
        "C_1V2", "100nF", 7.0, 44.5, angle=180.0,
        ref_offset=(0.0, -1.8), val_offset=(0.0, 1.8)
    )
    set_pad_net(c_1v2, "1", net_1v2o)
    set_pad_net(c_1v2, "2", net_gnd)
    board.Add(c_1v2)

    # U4: AMS1117-3.3 Dedicated 3.3V Regulator for W5500 Ethernet
    u4 = load_fp(
        f"{KICAD_FP_DIR}/Package_TO_SOT_SMD.pretty",
        "SOT-223-3_TabPin2",
        "U4", "AMS1117-3.3", 18.0, 60.0, angle=0.0,
        ref_offset=(0.0, -6.5), val_offset=(0.0, -5.2),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(u4, "1", net_gnd)
    set_pad_net(u4, ["2", "4"], net_3v3_eth)
    set_pad_net(u4, "3", net_5v)
    board.Add(u4)

    c_eth_in = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_SMD.pretty",
        "C_0805_2012Metric",
        "C_E1", "10uF", 10.5, 62.0,
        ref_offset=(0.0, -1.8), val_offset=(0.0, 1.8)
    )
    set_pad_net(c_eth_in, "1", net_5v)
    set_pad_net(c_eth_in, "2", net_gnd)
    board.Add(c_eth_in)

    c_eth_out = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_SMD.pretty",
        "C_0805_2012Metric",
        "C_E2", "10uF", 26.5, 60.0,
        ref_offset=(0.0, -1.8), val_offset=(0.0, 1.8)
    )
    set_pad_net(c_eth_out, "1", net_3v3_eth)
    set_pad_net(c_eth_out, "2", net_gnd)
    board.Add(c_eth_out)

    # 4. Power Input & Protection Stage (Top-Facing DIN-Rail Edge)
    j1 = load_fp(
        f"{KICAD_FP_DIR}/TerminalBlock_Phoenix.pretty",
        "TerminalBlock_Phoenix_MKDS-3-2-5.08_1x02_P5.08mm_Horizontal",
        "J1", "24V_IN", 47.0 + S, 7.5, angle=180.0,
        show_ref=False, show_val=False
    )
    set_pad_net(j1, "1", net_24v_in)
    set_pad_net(j1, "2", net_gnd)
    board.Add(j1)
    j1_p1 = pad_xy(j1, "1")
    j1_p2 = pad_xy(j1, "2")
    add_silk_text(board, "+24V", j1_p1[0], 15.2, size_mm=0.9, thickness_mm=0.18, bold=True)
    add_silk_text(board, "-GND", j1_p2[0], 15.2, size_mm=0.9, thickness_mm=0.18, bold=True)
    add_silk_text(board, "+", j1_p1[0], 10.5, size_mm=1.4, thickness_mm=0.25, bold=True, layer=pcbnew.B_SilkS)
    add_silk_text(board, "-", j1_p2[0], 10.5, size_mm=1.4, thickness_mm=0.25, bold=True, layer=pcbnew.B_SilkS)

    f1 = load_fp(
        f"{KICAD_FP_DIR}/Fuse.pretty",
        "Fuseholder_Blade_Mini_Keystone_3568",
        "F1", "15A FUSE", 56.0 + S, 6.0,
        ref_offset=(4.96, -3.5), val_offset=(4.96, 6.5)
    )
    set_pad_net(f1, "1", net_24v_in)
    set_pad_net(f1, "2", net_24v_fused)
    board.Add(f1)

    q_rev = load_fp(
        f"{KICAD_FP_DIR}/Package_TO_SOT_SMD.pretty",
        "TO-252-3_TabPin2",
        "Q_REV", "AOD403", 76.0 + S, 8.5, angle=0.0,
        ref_offset=(0.0, -6.0), val_offset=(0.0, -4.8),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(q_rev, "1", net_rev_gate)
    set_pad_net(q_rev, ["2", ""], net_24v_fused)
    set_pad_net(q_rev, "3", net_24v_bus)
    board.Add(q_rev)

    dz1 = load_fp(
        f"{KICAD_FP_DIR}/Diode_SMD.pretty",
        "D_SOD-123",
        "DZ1", "BZT52C12", 71.0 + S, 16.5, angle=180.0,
        ref_offset=(0.0, -2.0), val_offset=(0.0, 2.0),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(dz1, "1", net_24v_bus)
    set_pad_net(dz1, "2", net_rev_gate)
    board.Add(dz1)

    r_rev = load_fp(
        f"{KICAD_FP_DIR}/Resistor_SMD.pretty",
        "R_0805_2012Metric",
        "R_REV", "100k", 78.0 + S, 16.5,
        ref_offset=(0.0, -1.8), val_offset=(0.0, 1.8),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(r_rev, "1", net_rev_gate)
    set_pad_net(r_rev, "2", net_gnd)
    board.Add(r_rev)

    d_tvs = load_fp(
        f"{KICAD_FP_DIR}/Diode_SMD.pretty",
        "D_SMB",
        "D_TVS", "SMBJ28A", 86.5 + S, 18.5,
        ref_offset=(0.0, -2.8), val_offset=(0.0, 2.8),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(d_tvs, "1", net_24v_bus)
    set_pad_net(d_tvs, "2", net_gnd)
    board.Add(d_tvs)

    c1 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_THT.pretty",
        "CP_Radial_D10.0mm_P5.00mm",
        "C1", "470uF 35V", 85.0 + S, 8.5,
        ref_offset=(2.5, -6.2), val_offset=(2.5, 6.2)
    )
    set_pad_net(c1, "1", net_24v_bus)
    set_pad_net(c1, "2", net_gnd)
    board.Add(c1)

    c2 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_SMD.pretty",
        "C_1206_3216Metric",
        "C2", "10uF 50V", 95.0 + S, 14.5,
        ref_offset=(0.0, -2.2), val_offset=(0.0, 2.2),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(c2, "1", net_24v_bus)
    set_pad_net(c2, "2", net_gnd)
    board.Add(c2)

    c3 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_SMD.pretty",
        "C_0805_2012Metric",
        "C3", "100nF", 95.0 + S, 20.0,
        ref_offset=(0.0, -2.0), val_offset=(0.0, 2.0),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(c3, "1", net_24v_bus)
    set_pad_net(c3, "2", net_gnd)
    board.Add(c3)

    # 5. Buck Converter 24V -> 5V (XL1509-5.0E1)
    c4 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_THT.pretty",
        "CP_Radial_D6.3mm_P2.50mm",
        "C4", "100uF 35V", 44.5 + S, 23.0, angle=-90.0,
        ref_offset=(0.0, -4.8), val_offset=(0.0, 6.0),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(c4, "1", net_24v_bus)
    set_pad_net(c4, "2", net_gnd)
    board.Add(c4)

    u1 = load_fp(
        f"{KICAD_FP_DIR}/Package_SO.pretty",
        "SOIC-8_3.9x4.9mm_P1.27mm",
        "U1", "XL1509-5.0", 54.0 + S, 23.5,
        ref_offset=(0.0, -3.7), val_offset=(0.0, -5.0),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(u1, "1", net_24v_bus)
    set_pad_net(u1, "2", net_sw)
    set_pad_net(u1, "3", net_5v)
    set_pad_net(u1, ["4", "5", "6", "7", "8"], net_gnd)
    board.Add(u1)

    d_buck = load_fp(
        f"{KICAD_FP_DIR}/Diode_SMD.pretty",
        "D_SMA",
        "D_BUCK", "SS34", 54.0 + S, 30.0,
        ref_offset=(0.0, -2.8), val_offset=(0.0, 2.8),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(d_buck, "1", net_sw)
    set_pad_net(d_buck, "2", net_gnd)
    board.Add(d_buck)

    l1 = load_fp(
        f"{KICAD_FP_DIR}/Inductor_SMD.pretty",
        "L_Bourns_SRN6045TA",
        "L1", "33uH 3A", 64.5 + S, 25.0,
        ref_offset=(0.0, -4.0), val_offset=(0.0, 4.0),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(l1, "1", net_sw)
    set_pad_net(l1, "2", net_5v)
    board.Add(l1)

    c5 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_THT.pretty",
        "CP_Radial_D6.3mm_P2.50mm",
        "C5", "220uF 16V", 74.0 + S, 25.0,
        ref_offset=(1.25, -4.5), val_offset=(1.25, 4.5),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(c5, "1", net_5v)
    set_pad_net(c5, "2", net_gnd)
    board.Add(c5)

    c6 = load_fp(
        f"{KICAD_FP_DIR}/Capacitor_SMD.pretty",
        "C_0805_2012Metric",
        "C6", "100nF", 74.0 + S, 32.0,
        ref_offset=(3.6, -0.6), val_offset=(3.6, 0.6),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(c6, "1", net_5v)
    set_pad_net(c6, "2", net_gnd)
    board.Add(c6)

    r_pwr = load_fp(
        f"{KICAD_FP_DIR}/Resistor_SMD.pretty",
        "R_0805_2012Metric",
        "R_PWR", "1k", 39.5 + S, 45.0,
        ref_offset=(0.0, -2.0), val_offset=(0.0, -3.2),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(r_pwr, "1", net_5v)
    set_pad_net(r_pwr, "2", net_pwr_led)
    board.Add(r_pwr)

    d_pwr = load_fp(
        f"{KICAD_FP_DIR}/LED_SMD.pretty",
        "LED_0805_2012Metric",
        "D_PWR", "LED GRN", 39.5 + S, 49.5,
        ref_offset=(0.0, 2.0), val_offset=(0.0, 3.2),
        text_size=0.8, text_thick=0.13
    )
    set_pad_net(d_pwr, "2", net_pwr_led)
    set_pad_net(d_pwr, "1", net_gnd)
    board.Add(d_pwr)

    # 6. 6-Channel MOSFET Switching Array & Bottom-Facing Screw Terminals
    col_x = [49.0 + S, 61.0 + S, 73.0 + S, 85.0 + S, 97.0 + S, 109.0 + S]
    ch_parts = []
    for idx, cx in enumerate(col_x):
        ch = idx + 1

        rpd = load_fp(
            f"{KICAD_FP_DIR}/Resistor_SMD.pretty",
            "R_0805_2012Metric",
            f"R{2*ch}", "10k", cx - 3.0, 39.0,
            ref_offset=(0.0, -1.6), val_offset=(0.0, -2.8),
            text_size=0.8, text_thick=0.13
        )
        set_pad_net(rpd, "1", net_pwm[idx])
        set_pad_net(rpd, "2", net_gnd)
        board.Add(rpd)

        rg = load_fp(
            f"{KICAD_FP_DIR}/Resistor_SMD.pretty",
            "R_0805_2012Metric",
            f"R{2*ch-1}", "100R", cx + 2.5, 39.0,
            ref_offset=(0.0, -1.6), val_offset=(0.0, -2.8),
            text_size=0.8, text_thick=0.13
        )
        set_pad_net(rg, "1", net_pwm[idx])
        set_pad_net(rg, "2", net_gate[idx])
        board.Add(rg)

        q = load_fp(
            f"{KICAD_FP_DIR}/Package_TO_SOT_SMD.pretty",
            "TO-252-3_TabPin2",
            f"Q{ch}", "AOD4184A", cx, 46.8, angle=-90.0,
            ref_offset=(-2.2, -12.5), val_offset=(2.2, -12.5),
            text_size=0.8, text_thick=0.13
        )
        set_pad_net(q, "1", net_gate[idx])
        set_pad_net(q, ["2", ""], net_out[idx])
        set_pad_net(q, "3", net_gnd)
        board.Add(q)

        d_fly = load_fp(
            f"{KICAD_FP_DIR}/Diode_SMD.pretty",
            "D_SMA",
            f"D{ch}", "SS34", cx - 3.5, 55.2, angle=-90.0,
            ref_offset=(-2.65, -1.6), val_offset=(-2.65, 1.6),
            ref_angle=90.0, val_angle=90.0,
            text_size=0.8, text_thick=0.13
        )
        set_pad_net(d_fly, "1", net_24v_bus)
        set_pad_net(d_fly, "2", net_out[idx])
        board.Add(d_fly)

        r_led = load_fp(
            f"{KICAD_FP_DIR}/Resistor_SMD.pretty",
            "R_0805_2012Metric",
            f"RL{ch}", "10k", cx + 3.0, 52.5,
            ref_offset=(0.0, 1.8), val_offset=(-3.5, 0.0),
            text_size=0.8, text_thick=0.13
        )
        set_pad_net(r_led, "1", net_24v_bus)
        set_pad_net(r_led, "2", net_led[idx])
        board.Add(r_led)

        led = load_fp(
            f"{KICAD_FP_DIR}/LED_SMD.pretty",
            "LED_0805_2012Metric",
            f"LED{ch}", "LED", cx + 3.0, 56.2,
            ref_offset=(0.0, 1.8),
            show_val=False,
            text_size=0.8, text_thick=0.13
        )
        set_pad_net(led, "2", net_led[idx])
        set_pad_net(led, "1", net_out[idx])
        board.Add(led)

        j_out = load_fp(
            f"{KICAD_FP_DIR}/TerminalBlock_Phoenix.pretty",
            "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
            f"J{ch+1}", f"CH{ch}", cx - 2.54, 65.5, angle=0.0,
            show_ref=False, show_val=False
        )
        set_pad_net(j_out, "1", net_24v_bus)
        set_pad_net(j_out, "2", net_out[idx])
        board.Add(j_out)

        # Clear, bold + and - polarity markings and CHx label (Top & Bottom)
        add_silk_text(board, f"CH{ch}", cx - 0.5, 54.5, size_mm=0.85, thickness_mm=0.16, bold=True)
        add_silk_text(board, "+", cx - 2.54, 59.2, size_mm=0.85, thickness_mm=0.14, bold=True)
        add_silk_text(board, "-", cx + 2.54, 59.2, size_mm=0.85, thickness_mm=0.14, bold=True)
        add_silk_text(board, "+", cx - 2.54, 62.5, size_mm=1.3, thickness_mm=0.22, bold=True, layer=pcbnew.B_SilkS)
        add_silk_text(board, "-", cx + 2.54, 62.5, size_mm=1.3, thickness_mm=0.22, layer=pcbnew.B_SilkS)
        ch_parts.append((rg, rpd, q, d_fly, r_led, led, j_out))

    # 7. Branding, Logo, Version & Design Date (Top-Right Corner)
    logo_path = os.path.join(PRJ_DIR, "logo.png")
    if os.path.exists(logo_path):
        add_logo_from_png(board, logo_path, 96.0 + S, 3.8, target_width_mm=20.0)

    add_silk_text(board, "24V 6-CH LAN ESPHOME DIMMER", 109.5 + S, 11.2, size_mm=0.85, bold=True)
    add_silk_text(board, "REV 1.2 DIN  |  2026-11-18", 109.5 + S, 13.4, size_mm=0.85, bold=True)
    add_silk_text(board, "MAX 60W/CH (2.5A) | 15A TOTAL", 109.5 + S, 15.6, size_mm=0.8)

    # 8. Top-Facing HR911105A LAN -> W5500 Routing (clean short vertical bus!)
    # HR911105A pins (1..8) are at y=16.0..18.54, x=13.6..22.5 (1 is rightmost, 8 is leftmost)
    # 1=TXP -> U3(2), 2=TXN -> U3(1), 3=RXP -> U3(6), 6=RXN -> U3(5), 8=GND
    add_gnd_via_near(board, pad_xy(j_lan, "8")[0], pad_xy(j_lan, "8")[1], 0.0, 2.0, net_gnd)

    jp1, up2 = pad_xy(j_lan, "1"), pad_xy(u3, "2")
    add_route(board, [jp1, (jp1[0], 29.5), (11.4, 29.5), (11.4, up2[1]), up2], 0.22, pcbnew.F_Cu, net_txp)

    jp2, up1 = pad_xy(j_lan, "2"), pad_xy(u3, "1")
    add_via(board, jp2[0], jp2[1] + 2.0, net_txn, dia_mm=0.65, drill_mm=0.35)
    add_track(board, jp2[0], jp2[1], jp2[0], jp2[1] + 2.0, 0.22, pcbnew.F_Cu, net_txn)
    add_route(board, [up1, (12.2, up1[1]), (12.2, 34.5)], 0.22, pcbnew.F_Cu, net_txn)
    add_via(board, 12.2, 34.5, net_txn, dia_mm=0.65, drill_mm=0.35)
    add_route(board, [(jp2[0], jp2[1] + 2.0), (jp2[0], 28.5), (12.2, 28.5), (12.2, 34.5)], 0.22, pcbnew.B_Cu, net_txn)

    jp3, up6 = pad_xy(j_lan, "3"), pad_xy(u3, "6")
    add_route(board, [jp3, (jp3[0], 27.5), (9.8, 27.5), (9.8, up6[1]), up6], 0.22, pcbnew.F_Cu, net_rxp)

    jp6, up5 = pad_xy(j_lan, "6"), pad_xy(u3, "5")
    add_via(board, jp6[0], jp6[1] + 2.0, net_rxn, dia_mm=0.65, drill_mm=0.35)
    add_track(board, jp6[0], jp6[1], jp6[0], jp6[1] + 2.0, 0.22, pcbnew.F_Cu, net_rxn)
    add_route(board, [up5, (10.6, up5[1]), (10.6, 36.5)], 0.22, pcbnew.F_Cu, net_rxn)
    add_via(board, 10.6, 36.5, net_rxn, dia_mm=0.65, drill_mm=0.35)
    add_route(board, [(jp6[0], jp6[1] + 2.0), (jp6[0], 26.5), (10.6, 26.5), (10.6, 36.5)], 0.22, pcbnew.B_Cu, net_rxn)

    # HR911105A Center Taps (4, 5) & LED Anodes (9, 12) -> +3V3_ETH (PTH pads connect F.Cu & B.Cu directly)
    jp4, jp5, jp9, jp12 = pad_xy(j_lan, "4"), pad_xy(j_lan, "5"), pad_xy(j_lan, "9"), pad_xy(j_lan, "12")
    # Connect Pad 12 to Pad 9 cleanly on F.Cu above the LED row
    add_route(board, [jp12, (jp12[0], 2.2), (jp9[0], 2.2), jp9], 0.35, pcbnew.F_Cu, net_3v3_eth)

    # HR911105A LEDs: 10->25 (Link) & 11->27 (Act) drop to B.Cu at x=23.4 and route around SH (25.805, 12.69)
    jp10, up25 = pad_xy(j_lan, "10"), pad_xy(u3, "25")
    add_via(board, 23.4, up25[1], net_link_led, dia_mm=0.6, drill_mm=0.3)
    add_track(board, up25[0], up25[1], 23.4, up25[1], 0.22, pcbnew.F_Cu, net_link_led)
    add_route(board, [(23.4, up25[1]), (29.0, up25[1]), (29.0, 6.4)], 0.22, pcbnew.B_Cu, net_link_led)
    add_via(board, 29.0, 6.4, net_link_led, dia_mm=0.6, drill_mm=0.3)
    add_route(board, [(29.0, 6.4), (jp10[0], 6.4), jp10], 0.22, pcbnew.F_Cu, net_link_led)

    jp11, up27 = pad_xy(j_lan, "11"), pad_xy(u3, "27")
    add_via(board, 23.4, up27[1], net_act_led, dia_mm=0.6, drill_mm=0.3)
    add_track(board, up27[0], up27[1], 23.4, up27[1], 0.22, pcbnew.F_Cu, net_act_led)
    add_route(board, [(23.4, up27[1]), (28.2, up27[1]), (28.2, 2.5), (jp11[0], 2.5), jp11], 0.22, pcbnew.B_Cu, net_act_led)

    # W5500 Crystal Y1 (XI=30 on F.Cu x=24.0 -> 53.1, XO=31 on F.Cu x=24.8 -> 47.0 -> B.Cu under XI -> F.Cu!)
    u3_xi = pad_xy(u3, "30")
    u3_xo = pad_xy(u3, "31")
    y1_xi = pad_xy(y1, "1")
    y1_xo = pad_xy(y1, "3")
    add_route(board, [u3_xi, (24.0, u3_xi[1]), (24.0, 53.1), (16.9, 53.1), y1_xi], 0.22, pcbnew.F_Cu, net_xi)
    add_route(board, [u3_xo, (24.8, u3_xo[1]), (24.8, 47.0)], 0.22, pcbnew.F_Cu, net_xo)
    add_via(board, 24.8, 47.0, net_xo, dia_mm=0.6, drill_mm=0.3)
    add_route(board, [(24.8, 47.0), (22.2, 47.0)], 0.22, pcbnew.B_Cu, net_xo)
    add_via(board, 22.2, 47.0, net_xo, dia_mm=0.6, drill_mm=0.3)
    add_route(board, [(22.2, 47.0), (19.1, 47.0), y1_xo], 0.22, pcbnew.F_Cu, net_xo)
    add_gnd_via_near(board, pad_xy(y1, "2")[0], pad_xy(y1, "2")[1], 0.0, 1.4, net_gnd)
    add_gnd_via_near(board, pad_xy(y1, "4")[0], pad_xy(y1, "4")[1], -1.5, 0.0, net_gnd)

    # W5500 EXRES (10) & 1V2O (22)
    add_route(board, [pad_xy(u3, "10"), (8.0, 40.25), (8.0, 38.5), pad_xy(r_exres, "1")], 0.22, pcbnew.F_Cu, net_exres)
    add_gnd_via_near(board, pad_xy(r_exres, "2")[0], pad_xy(r_exres, "2")[1], -1.5, 0.0, net_gnd)
    add_route(board, [pad_xy(u3, "22"), (pad_xy(u3, "22")[0], 44.9), (7.95, 44.9), pad_xy(c_1v2, "1")], 0.22, pcbnew.F_Cu, net_1v2o)
    add_gnd_via_near(board, pad_xy(c_1v2, "2")[0], pad_xy(c_1v2, "2")[1], -1.5, 0.0, net_gnd)

    # Clean non-crossing W5500 GND & +3V3_ETH fanout (including PMODE0..2 pins 43, 44, 45 tied to +3V3_ETH)
    gnd_tl = (15.8, 36.0)
    add_via(board, gnd_tl[0], gnd_tl[1], net_gnd, dia_mm=0.7, drill_mm=0.35)
    for gpin, (dx, dy) in [("48", (0.0, 1.0)), ("3", (1.0, 0.0))]:
        gp = pad_xy(u3, gpin)
        add_route(board, [gp, (gp[0] + dx, gp[1] + dy), gnd_tl], 0.22, pcbnew.F_Cu, net_gnd)

    gnd_bot = (17.5, 41.1)
    add_via(board, gnd_bot[0], gnd_bot[1], net_gnd, dia_mm=0.7, drill_mm=0.35)
    for gpin, (dx, dy) in [("14", (0.0, -1.0)), ("16", (0.0, -1.0)), ("19", (0.0, -1.0)), ("21", (0.0, -1.0)), ("23", (0.0, -1.0))]:
        gp = pad_xy(u3, gpin)
        add_route(board, [gp, (gp[0] + dx, gp[1] + dy), gnd_bot], 0.22, pcbnew.F_Cu, net_gnd)

    p9 = pad_xy(u3, "9")
    add_route(board, [p9, (12.4, p9[1]), (12.4, 39.5)], 0.22, pcbnew.F_Cu, net_gnd)
    add_via(board, 12.4, 39.5, net_gnd, dia_mm=0.6, drill_mm=0.3)
    p29 = pad_xy(u3, "29")
    add_route(board, [p29, (20.4, p29[1]), (20.4, 37.5)], 0.22, pcbnew.F_Cu, net_gnd)
    add_via(board, 20.4, 37.5, net_gnd, dia_mm=0.6, drill_mm=0.3)

    vdd_star = (18.2, 38.7)
    add_via(board, vdd_star[0], vdd_star[1], net_3v3_eth, dia_mm=0.7, drill_mm=0.35)
    for vpin, (dx, dy) in [("4", (1.0, 0.0)), ("8", (1.0, 0.0)), ("43", (0.0, 1.0)), ("44", (0.0, 1.0)), ("45", (0.0, 1.0))]:
        vp = pad_xy(u3, vpin)
        add_route(board, [vp, (vp[0] + dx, vp[1] + dy), vdd_star], 0.22, pcbnew.F_Cu, net_3v3_eth)
    p28 = pad_xy(u3, "28")
    add_route(board, [p28, (21.0, p28[1]), (19.5, 39.75), (19.5, 38.7), vdd_star], 0.22, pcbnew.F_Cu, net_3v3_eth)

    p11 = pad_xy(u3, "11")
    add_route(board, [p11, (12.4, p11[1]), (12.4, 41.5)], 0.22, pcbnew.F_Cu, net_3v3_eth)
    add_via(board, 12.4, 41.5, net_3v3_eth, dia_mm=0.6, drill_mm=0.3)

    vdd_out_vias = [(12.4, 41.5)]
    for vpin in ["15", "17"]:
        vp = pad_xy(u3, vpin)
        vx, vy = vp[0], 43.8
        add_track(board, vp[0], vp[1], vx, vy, 0.22, pcbnew.F_Cu, net_3v3_eth)
        add_via(board, vx, vy, net_3v3_eth, dia_mm=0.6, drill_mm=0.3)
        vdd_out_vias.append((vx, vy))

    # AMS1117-3.3 (U4) +5V -> +3V3_ETH
    u4_gnd = pad_xy(u4, "1")
    u4_out = pad_xy(u4, "2")
    u4_tab = pad_xy(u4, "2", "max_x")
    u4_in = pad_xy(u4, "3")
    add_track(board, u4_out[0], u4_out[1], u4_tab[0], u4_tab[1], 0.8, pcbnew.F_Cu, net_3v3_eth)
    add_gnd_via_near(board, u4_gnd[0], u4_gnd[1], -1.5, 0.0, net_gnd)
    ce1_p1 = pad_xy(c_eth_in, "1")
    add_route(board, [u4_in, (u4_in[0], 64.5), (ce1_p1[0], 64.5), ce1_p1], 0.6, pcbnew.F_Cu, net_5v)
    add_gnd_via_near(board, pad_xy(c_eth_in, "2")[0], pad_xy(c_eth_in, "2")[1], 1.5, 0.0, net_gnd)
    add_route(board, [u4_tab, pad_xy(c_eth_out, "1")], 0.6, pcbnew.F_Cu, net_3v3_eth)
    ce2_p1 = pad_xy(c_eth_out, "1")
    add_via(board, ce2_p1[0], ce2_p1[1] - 2.0, net_3v3_eth, dia_mm=0.8, drill_mm=0.4)
    add_track(board, ce2_p1[0], ce2_p1[1], ce2_p1[0], ce2_p1[1] - 2.0, 0.6, pcbnew.F_Cu, net_3v3_eth)
    add_gnd_via_near(board, pad_xy(c_eth_out, "2")[0], pad_xy(c_eth_out, "2")[1], 1.5, 0.0, net_gnd)
    add_route(board, [(ce2_p1[0], ce2_p1[1] - 2.0), (21.2, 58.0), (21.2, 43.8), vdd_out_vias[2], vdd_out_vias[1], vdd_out_vias[0]], 0.35, pcbnew.B_Cu, net_3v3_eth)
    add_route(board, [vdd_out_vias[2], (19.5, 43.8), (19.5, 38.7), vdd_star], 0.35, pcbnew.B_Cu, net_3v3_eth)
    add_route(board, [vdd_out_vias[0], (8.6, 41.5), (8.6, 15.2), (12.8, 15.2), (12.8, 13.8), (jp5[0], 13.8), jp5], 0.35, pcbnew.B_Cu, net_3v3_eth)
    add_route(board, [(jp5[0], 13.8), (jp4[0], 13.8), jp4], 0.35, pcbnew.B_Cu, net_3v3_eth)
    add_route(board, [(8.6, 15.2), (8.6, jp12[1]), jp12], 0.35, pcbnew.B_Cu, net_3v3_eth)

    # +5V feed from U2 Pin 15
    u2_5v = pad_xy(u2, "15")
    add_route(board, [u2_5v, (u2_5v[0] + 5.0, u2_5v[1]), (u2_5v[0] + 5.0, 64.5), (ce1_p1[0], 64.5)], 0.6, pcbnew.B_Cu, net_5v)
    add_via(board, ce1_p1[0], 64.5, net_5v)

    # W5500 SPI Bus -> ESP32 U2 Left Pins (6, 7, 8, 9, 10, 11)
    spi_pairs = [
        ("6", "37", net_eth_rst, 30.0),
        ("7", "36", net_eth_int, 30.85),
        ("9", "35", net_eth_mosi, 32.55),
        ("8", "34", net_eth_miso, 31.70),
        ("10", "33", net_eth_cs, 33.40),
        ("11", "32", net_eth_clk, 34.25),
    ]
    for idx, (epin, wpin, snet, vx) in enumerate(spi_pairs):
        ep = pad_xy(u2, epin)
        wp = pad_xy(u3, wpin)
        vy = 31.7 + idx * 0.9
        fx = 23.8 + idx * 0.45
        if wpin == "37":
            add_route(board, [wp, (wp[0], vy), (vx, vy)], 0.22, pcbnew.F_Cu, snet)
        else:
            add_route(board, [wp, (fx, wp[1]), (fx, vy), (vx, vy)], 0.22, pcbnew.F_Cu, snet)
        add_via(board, vx, vy, snet, dia_mm=0.65, drill_mm=0.35)
        add_route(board, [(vx, vy), (vx, ep[1]), ep], 0.22, pcbnew.B_Cu, snet)

    # 9. Power Input & Buck Routing
    f1_p1_top = pad_xy(f1, "1", "min_y")
    f1_p1_bot = pad_xy(f1, "1", "max_y")
    f1_p2_top = pad_xy(f1, "2", "min_y")
    f1_p2_bot = pad_xy(f1, "2", "max_y")
    add_track(board, f1_p1_top[0], f1_p1_top[1], f1_p1_bot[0], f1_p1_bot[1], 2.0, pcbnew.F_Cu, net_24v_in)
    add_track(board, f1_p2_top[0], f1_p2_top[1], f1_p2_bot[0], f1_p2_bot[1], 2.0, pcbnew.F_Cu, net_24v_fused)
    add_route(board, [j1_p1, (j1_p1[0], 3.0), (f1_p1_top[0], 3.0), f1_p1_top], 2.5, pcbnew.F_Cu, net_24v_in)

    qrev_tab = pad_xy(q_rev, "2", "max_x")
    qrev_pin2 = pad_xy(q_rev, "2", "first")
    qrev_g = pad_xy(q_rev, "1")
    qrev_s = pad_xy(q_rev, "3")
    add_track(board, qrev_pin2[0], qrev_pin2[1], qrev_tab[0], qrev_tab[1], 0.6, pcbnew.F_Cu, net_24v_fused)
    add_route(board, [f1_p2_top, (f1_p2_top[0], 3.0), (qrev_tab[0], 3.0), qrev_tab], 2.5, pcbnew.F_Cu, net_24v_fused)

    dz1_p1 = pad_xy(dz1, "1")
    dz1_p2 = pad_xy(dz1, "2")
    rrev_p1 = pad_xy(r_rev, "1")
    rrev_p2 = pad_xy(r_rev, "2")
    add_route(board, [qrev_g, (68.5 + S, qrev_g[1]), (68.5 + S, 15.0), (dz1_p2[0], 15.0), dz1_p2], 0.35, pcbnew.F_Cu, net_rev_gate)
    add_route(board, [dz1_p2, (dz1_p2[0], 18.5), (rrev_p1[0], 18.5), rrev_p1], 0.35, pcbnew.F_Cu, net_rev_gate)
    add_gnd_via_near(board, rrev_p2[0], rrev_p2[1], 1.5, 0.0, net_gnd)

    c1_p1 = pad_xy(c1, "1")
    dtvs_p1 = pad_xy(d_tvs, "1")
    dtvs_p2 = pad_xy(d_tvs, "2")
    c2_p1 = pad_xy(c2, "1")
    c2_p2 = pad_xy(c2, "2")
    c3_p1 = pad_xy(c3, "1")
    c3_p2 = pad_xy(c3, "2")
    c4_p1 = pad_xy(c4, "1")

    add_route(board, [qrev_s, (qrev_s[0], 13.5), (83.0 + S, 13.5), (c1_p1[0], 13.5), c1_p1], 2.5, pcbnew.F_Cu, net_24v_bus)
    add_route(board, [qrev_s, (dz1_p1[0], qrev_s[1]), dz1_p1], 0.6, pcbnew.F_Cu, net_24v_bus)
    add_route(board, [c1_p1, (c1_p1[0], 16.0), (dtvs_p1[0], 16.0), dtvs_p1], 1.2, pcbnew.F_Cu, net_24v_bus)
    add_route(board, [c1_p1, (c1_p1[0], 14.5), c2_p1], 1.0, pcbnew.F_Cu, net_24v_bus)
    add_route(board, [c2_p1, c3_p1], 0.6, pcbnew.F_Cu, net_24v_bus)
    add_gnd_via_near(board, dtvs_p2[0], dtvs_p2[1], 1.8, 0.0, net_gnd)
    add_gnd_via_near(board, c2_p2[0], c2_p2[1], 1.5, 0.0, net_gnd)
    add_gnd_via_near(board, c3_p2[0], c3_p2[1], 1.5, 0.0, net_gnd)

    u1_p1 = pad_xy(u1, "1")
    u1_p2 = pad_xy(u1, "2")
    u1_p3 = pad_xy(u1, "3")
    u1_p4 = pad_xy(u1, "4")
    u1_p5 = pad_xy(u1, "5")
    u1_p8 = pad_xy(u1, "8")
    add_route(board, [(83.0 + S, 13.5), (83.0 + S, 20.0), (44.5 + S, 20.0), c4_p1], 1.5, pcbnew.F_Cu, net_24v_bus)
    add_route(board, [c4_p1, (c4_p1[0], u1_p1[1]), u1_p1], 1.0, pcbnew.F_Cu, net_24v_bus)

    dbuck_p1 = pad_xy(d_buck, "1")
    dbuck_p2 = pad_xy(d_buck, "2")
    l1_p1 = pad_xy(l1, "1")
    l1_p2 = pad_xy(l1, "2")
    c5_p1 = pad_xy(c5, "1")
    c6_p1 = pad_xy(c6, "1")
    c6_p2 = pad_xy(c6, "2")

    add_route(board, [u1_p2, (48.0 + S, u1_p2[1]), (48.0 + S, 30.0), dbuck_p1], 1.0, pcbnew.F_Cu, net_sw)
    add_route(board, [dbuck_p1, (dbuck_p1[0], 32.5), (60.2 + S, 32.5), (60.2 + S, l1_p1[1]), l1_p1], 1.0, pcbnew.F_Cu, net_sw)
    add_gnd_via_near(board, dbuck_p2[0], dbuck_p2[1], 1.8, 0.0, net_gnd)

    add_track(board, u1_p4[0], u1_p4[1], u1_p5[0], u1_p5[1], 0.4, pcbnew.F_Cu, net_gnd)
    add_track(board, u1_p5[0], u1_p5[1], u1_p8[0], u1_p8[1], 0.6, pcbnew.F_Cu, net_gnd)
    add_gnd_via_near(board, u1_p8[0], u1_p8[1], 1.8, 0.0, net_gnd)

    add_route(board, [l1_p2, c5_p1], 1.2, pcbnew.F_Cu, net_5v)
    add_route(board, [c5_p1, (72.5 + S, c5_p1[1]), (72.5 + S, c6_p1[1]), c6_p1], 0.5, pcbnew.F_Cu, net_5v)
    add_gnd_via_near(board, c6_p2[0], c6_p2[1], 1.5, 0.0, net_gnd)

    add_route(board, [u1_p3, (49.8 + S, u1_p3[1]), (49.8 + S, 26.5)], 0.3, pcbnew.F_Cu, net_5v)
    add_via(board, 49.8 + S, 26.5, net_5v)
    add_route(board, [(49.8 + S, 26.5), (49.8 + S, 27.5), (70.0 + S, 27.5), (70.0 + S, c5_p1[1])], 0.35, pcbnew.B_Cu, net_5v)
    add_via(board, 70.0 + S, c5_p1[1], net_5v)
    add_track(board, 70.0 + S, c5_p1[1], c5_p1[0], c5_p1[1], 0.4, pcbnew.F_Cu, net_5v)

    rpwr_p1 = pad_xy(r_pwr, "1")
    rpwr_p2 = pad_xy(r_pwr, "2")
    dpwr_p1 = pad_xy(d_pwr, "1")
    dpwr_p2 = pad_xy(d_pwr, "2")

    add_via(board, c5_p1[0], c5_p1[1] + 2.5, net_5v)
    add_track(board, c5_p1[0], c5_p1[1], c5_p1[0], c5_p1[1] + 2.5, 0.6, pcbnew.F_Cu, net_5v)
    add_route(board, [(c5_p1[0], c5_p1[1] + 2.5), (74.0 + S, 27.51), (32.0 + S, 27.51), (32.0 + S, 45.28), (38.5 + S, 45.28)], 0.4, pcbnew.B_Cu, net_5v)
    add_via(board, 38.5 + S, 45.28, net_5v)
    add_track(board, 38.5 + S, 45.28, rpwr_p1[0], rpwr_p1[1], 0.5, pcbnew.F_Cu, net_5v)
    add_track(board, rpwr_p2[0], rpwr_p2[1], dpwr_p2[0], dpwr_p2[1], 0.3, pcbnew.F_Cu, net_pwr_led)
    add_gnd_via_near(board, dpwr_p1[0], dpwr_p1[1], -1.5, 0.0, net_gnd)
    add_route(board, [(32.0 + S, 27.51), (22.0 + S, 27.51), (22.0 + S, u2_5v[1]), u2_5v], 0.8, pcbnew.B_Cu, net_5v)

    # 10. PWM Bus & 6-Channel Routing
    for idx, (rg, rpd, q, d_fly, r_led, led, j_out) in enumerate(ch_parts):
        esp_xy = pad_xy(u2, gpio_pins[idx])
        rg_p1 = pad_xy(rg, "1")
        rg_p2 = pad_xy(rg, "2")
        rpd_p1 = pad_xy(rpd, "1")
        rpd_p2 = pad_xy(rpd, "2")
        q_g = pad_xy(q, "1")
        q_d_pin = pad_xy(q, "2", "min_y")
        q_d_tab = pad_xy(q, "2", "max_y")
        q_s = pad_xy(q, "3")
        dfly_p2 = pad_xy(d_fly, "2")
        rled_p2 = pad_xy(r_led, "2")
        led_p1 = pad_xy(led, "1")
        led_p2 = pad_xy(led, "2")
        j_p2 = pad_xy(j_out, "2")

        add_track(board, q_d_pin[0], q_d_pin[1], q_d_tab[0], q_d_tab[1], 0.8, pcbnew.F_Cu, net_out[idx])

        bus_x = 37.2 + S + idx * 0.85
        via_y = 33.8 + idx * 0.85
        add_route(board, [esp_xy, (bus_x, esp_xy[1]), (bus_x, via_y)], 0.3, pcbnew.F_Cu, net_pwm[idx])
        add_via(board, bus_x, via_y, net_pwm[idx])
        add_route(board, [(bus_x, via_y), (rpd_p1[0], via_y)], 0.3, pcbnew.B_Cu, net_pwm[idx])
        add_via(board, rpd_p1[0], via_y, net_pwm[idx])
        add_track(board, rpd_p1[0], via_y, rpd_p1[0], rpd_p1[1], 0.3, pcbnew.F_Cu, net_pwm[idx])
        add_route(board, [rpd_p1, (rpd_p1[0], 37.5), (rg_p1[0], 37.5), rg_p1], 0.3, pcbnew.F_Cu, net_pwm[idx])
        add_gnd_via_near(board, rpd_p2[0], rpd_p2[1], 0.0, 1.8, net_gnd)

        add_route(board, [rg_p2, (rg_p2[0], q_g[1]), q_g], 0.35, pcbnew.F_Cu, net_gate[idx])
        add_gnd_via_near(board, q_s[0], q_s[1], -1.8, 0.0, net_gnd, trace_w=1.0)

        add_route(board, [q_d_tab, (q_d_tab[0], 58.5), (j_p2[0], 60.5), j_p2], 2.0, pcbnew.F_Cu, net_out[idx])
        add_route(board, [dfly_p2, (dfly_p2[0], 58.5), (q_d_tab[0], 58.5)], 1.0, pcbnew.F_Cu, net_out[idx])
        add_route(board, [led_p1, (q_d_tab[0], led_p1[1])], 0.35, pcbnew.F_Cu, net_out[idx])
        add_track(board, rled_p2[0], rled_p2[1], led_p2[0], led_p2[1], 0.3, pcbnew.F_Cu, net_led[idx])

    # 11. High-Current +24V_BUS Feeder & Copper Pours
    add_route(board, [c1_p1, (c1_p1[0], 13.5), (93.0 + S, 13.5), (93.0 + S, 23.0), (116.0 + S, 23.0), (116.0 + S, 60.5)], 3.0, pcbnew.F_Cu, net_24v_bus)

    add_zone(board, net_gnd, pcbnew.B_Cu, [(1.0, 1.0), (BOARD_W - 1.0, 1.0), (BOARD_W - 1.0, BOARD_H - 1.0), (1.0, BOARD_H - 1.0)], priority=0, clearance_mm=0.5)
    add_zone(board, net_24v_bus, pcbnew.F_Cu, [(42.5 + S, 51.0), (118.0 + S, 51.0), (118.0 + S, 70.0), (42.5 + S, 70.0)], priority=1, clearance_mm=0.3)
    add_zone(board, net_gnd, pcbnew.F_Cu, [(32.0, 12.0), (40.5 + S, 12.0), (40.5 + S, 70.0), (32.0, 70.0)], priority=0, clearance_mm=0.5)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    out_path = os.path.join(PRJ_DIR, "dimmer_6ch.kicad_pcb")
    board.Save(out_path)
    print(f"Successfully generated: {out_path}")


if __name__ == "__main__":
    build_board()
