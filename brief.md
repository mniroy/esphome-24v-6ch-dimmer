# Project Brief: 24V DC 6-Channel LED Dimmer (IKEA SILVERGLANS Alternative — REV 1.2 DIN LAN)

## 1. Ringkasan & Tujuan Proyek
Membuat modul dimmer LED 24V DC multi-channel (6 Channel) berbasis **ESPHome** dengan koneksi **Wired Ethernet LAN (WIZnet W5500)** dan form factor **DIN-Rail Friendly (`152.0 mm × 72.0 mm`, profil UM72)**, yang meniru fungsi kontrol pintar dan kehalusan peredupan (**smooth dimming**) dari seri IKEA SILVERGLANS / TRÅDFRI driver, ditenagai oleh catu daya DC eksternal 24V murni.

Modul ini berfokus pada:
- **Mainboard Dimmer Controller Modular**: Menggunakan soket female pin header `2x15` untuk modul **ESP32 DevKit V1 30-Pin (USB-C)** sehingga mudah dicabut-pasang (*swappable*) jika terjadi kerusakan pada ESP32 tanpa perlu solder ulang.
- **Koneksi Wired LAN Stabil (W5500 + RJ45 MagJack)**: Menggunakan chip Ethernet **WIZnet W5500** onboard + **HanRun HR911105A** RJ45 MagJack + LDO independen **AMS1117-3.3** untuk koneksi jaringan kabel bebas interferensi di dalam panel listrik / kabinet.
- **Form Factor DIN-Rail (`152 mm × 72 mm`)**: Seluruh port kabel menghadap **ATAS** (`LAN RJ45` & `24V DC IN`) dan **BAWAH** (`USB-C` & `CH1–CH6 LED Output`), sehingga sisi kiri dan kanan board bebas 100% untuk dipasang berjejer rapat di DIN-Rail (`UM72` carrier / bracket M3).
- **Output Daya Tinggi**: 6 channel independen berkapasitas **48W–60W per channel** (`2.0A–2.5A` continuous @ 24V, total hingga `360W / 15A`).
- **Kemudahan Perakitan & Ketersediaan Lokal**: Seluruh komponen tersedia luas di pasar Indonesia (Tokopedia / Shopee), setiap komponen dilabeli `Ref` dan `Value/Tipe` secara detail, serta seluruh terminal input/output memiliki tanda polaritas **`+`** dan **`-`** berukuran besar di layer atas (`F.SilkS`) dan bawah (`B.SilkS`).

---

## 2. Parameter Kunci & Spesifikasi Sistem

| Parameter | Spesifikasi Terpilih | Catatan Teknis |
|---|---|---|
| **Revisi & Tanggal Desain** | `REV 1.2 DIN` (`2026-11-18`) | Branding logo **KEAVY Instruments** di pojok kanan atas PCB |
| **Dimensi & Mounting PCB** | **`152.0 mm × 72.0 mm`**, 2-Layer FR4 | Standar **UM72 DIN-Rail** carrier + 4x lubang baut `M3` (`3.2mm`) |
| **Orientasi Port (DIN-Rail)** | **Atas**: `RJ45 LAN`, `24V IN`<br>**Bawah**: `USB-C`, `CH1`–`CH6` | Sisi Kiri & Kanan bebas konektor (bisa dipasang rapat berdampingan) |
| **Tegangan Operasi (`Vin`)** | 24V DC murni (rentang 12V – 28V) | Dari external DC power supply (SMPS DIN-rail / adaptor 24V) |
| **Jumlah Channel Output** | 6 Channel Independen (`CH1`–`CH6`) | Low-side N-Channel MOSFET (`AOD4184A`) PWM switching |
| **Kapasitas Daya per Channel** | **48W – 60W per channel** | **2.0A – 2.5A continuous @ 24V** (`360W / 15A` total) |
| **Tipe Konektor Daya & LED** | **Screw Terminal Block 5.08mm** | Dilengkapi tanda **`+`** dan **`-`** besar di `F.SilkS` & `B.SilkS` |
| **Arsitektur Mikrokontroler** | **Modular Dev Board Socket (`2x15`)** | Soket Female Header 2.54mm untuk **ESP32 DevKit V1 30-Pin USB-C** |
| **Konektivitas Jaringan** | **10/100Mbps Ethernet LAN (SPI)** | Onboard **WIZnet W5500** (`LQFP-48`) + **HanRun HR911105A** + Crystal `25MHz` |
| **Regulasi Daya** | `24V` $\to$ `5V` (`XL1509-5.0`) $\to$ `3.3V` (`AMS1117-3.3`) | `XL1509-5.0` (2A Buck) menyuplai `5V` ESP32 & `AMS1117-3.3` khusus W5500 |
| **Frekuensi PWM** | **19.531 kHz** (`19531 Hz`) | Bebas kedip kamera (*flicker-free*) & bebas dengung (*ultrasonic*) |
| **Proteksi Sirkuit** | Reverse Polarity, Blade Fuse 15A, TVS, Flyback | `AOD403` P-MOSFET + `BZT52C12` + `15A` Mini Blade Fuse + `SMBJ28A` + 6x `SS34` |

---

## 3. Pemetaan Pin GPIO & Integrasi Hardware (Telah Diaudit)

Pemetaan pin pada soket `U2` (**ESP32 DevKit V1 30-Pin**, `1`–`15` di kiri dari atas ke bawah, `16`–`30` di kanan dari bawah ke atas) telah diverifikasi bebas dari konflik *strapping pin* (`GPIO0`, `GPIO2`, `GPIO5`, `GPIO12`, `GPIO15`), bebas dari pin *input-only* (`GPIO34`–`39`), dan bebas dari pin `UART0` (`GPIO1`, `GPIO3`):

### A. Bus SPI Ethernet W5500 (Baris Pin Kiri `U2`)
| Pin Soket `U2` | Pin ESP32 | Nama Net PCB | Pin Tujuan `U3 (W5500)` | Fungsi |
|---|---|---|---|---|
| **Pad 6** | `GPIO32` | `ETH_RST` | Pin 37 (`RSTn`) | Hardware Reset W5500 |
| **Pad 7** | `GPIO33` | `ETH_INT` | Pin 36 (`INTn`) | Interrupt Request W5500 |
| **Pad 8** | `GPIO25` | `ETH_MISO` | Pin 34 (`MISO`) | SPI Master In Slave Out |
| **Pad 9** | `GPIO26` | `ETH_MOSI` | Pin 35 (`MOSI`) | SPI Master Out Slave In |
| **Pad 10** | `GPIO27` | `ETH_CS` | Pin 33 (`SCSn`) | SPI Chip Select |
| **Pad 11** | `GPIO14` | `ETH_CLK` | Pin 32 (`SCLK`) | SPI Clock (20 MHz) |
| **Pad 14** | `GND` | `GND` | Ground Plane | Referensi Ground |
| **Pad 15** | `VIN / 5V` | `+5V` | Output `L1`/`C5` & Input `U4` | Suplai Utama 5V DC dari Buck `XL1509-5.0` |

> **Konfigurasi Hardware W5500 (`U3`)**:
> - Pin `43, 44, 45` (`PMODE0`, `PMODE1`, `PMODE2`) terhubung langsung ke `+3V3_ETH` (`111` = *All-capable Auto-Negotiation 10/100Mbps Full/Half Duplex*).
> - Pin `10` (`EXRES1`) terhubung ke `GND` melalui resistor presisi `R_EXRES` (`12.4k 1%`).
> - Pin `22` (`1V2O`) didekopel ke `GND` melalui kapasitor `C_1V2` (`100nF`), ditambah 4x kapasitor decoupling `+3V3_ETH` (`C_W1..C_W4` `100nF`).
> - Pin `30` (`XI`) & Pin `31` (`XO`) terhubung ke kristal `Y1` (`25MHz SMD-3225`) dengan kapasitor beban `C_Y1` & `C_Y2` (`18pF`).

### B. 6-Channel PWM Dimmer Output (Baris Pin Kanan `U2`)
| Channel | Terminal Output | Pin Soket `U2` | Pin ESP32 | Nama Net PCB | Komponen Driver Channel |
|---|---|---|---|---|---|
| **Channel 1** | `J2` (`CH1: +24V / -`) | **Pad 21** | `GPIO16` | `PWM_CH1` | `R1 (100R)`, `R2 (10k)`, `Q1 (AOD4184A)`, `D1 (SS34)`, `RL1 (10k)`, `LED1 (LED)` |
| **Channel 2** | `J3` (`CH2: +24V / -`) | **Pad 22** | `GPIO17` | `PWM_CH2` | `R3 (100R)`, `R4 (10k)`, `Q2 (AOD4184A)`, `D2 (SS34)`, `RL2 (10k)`, `LED2 (LED)` |
| **Channel 3** | `J4` (`CH3: +24V / -`) | **Pad 24** | `GPIO18` | `PWM_CH3` | `R5 (100R)`, `R6 (10k)`, `Q3 (AOD4184A)`, `D3 (SS34)`, `RL3 (10k)`, `LED3 (LED)` |
| **Channel 4** | `J5` (`CH4: +24V / -`) | **Pad 25** | `GPIO19` | `PWM_CH4` | `R7 (100R)`, `R8 (10k)`, `Q4 (AOD4184A)`, `D4 (SS34)`, `RL4 (10k)`, `LED4 (LED)` |
| **Channel 5** | `J6` (`CH5: +24V / -`) | **Pad 26** | `GPIO21` | `PWM_CH5` | `R9 (100R)`, `R10 (10k)`, `Q5 (AOD4184A)`, `D5 (SS34)`, `RL5 (10k)`, `LED5 (LED)` |
| **Channel 6** | `J7` (`CH6: +24V / -`) | **Pad 29** | `GPIO22` | `PWM_CH6` | `R11 (100R)`, `R12 (10k)`, `Q6 (AOD4184A)`, `D6 (SS34)`, `RL6 (10k)`, `LED6 (LED)` |

---

## 4. Hasil Verifikasi DRC & File Proyek
- **KiCad 10 PCB**: [dimmer_6ch.kicad_pcb](file:///Users/royyanwicaksono/Dev/PCB/DC%2024%206%20CH%20light%20dimmer/dimmer_6ch.kicad_pcb)
  - `Unconnected Items`: **0**
  - `Shorting Items / Tracks Crossing / Clearance`: **0**
  - `Courtyard Overlaps / Starved Thermals / Solder Mask Bridges`: **0**
- **Generator Script**: [generate_pcb.py](file:///Users/royyanwicaksono/Dev/PCB/DC%2024%206%20CH%20light%20dimmer/generate_pcb.py)
- **Firmware ESPHome**: [firmware/dimmer_6ch.yaml](file:///Users/royyanwicaksono/Dev/PCB/DC%2024%206%20CH%20light%20dimmer/firmware/dimmer_6ch.yaml)
- **Bill of Materials (BOM)**: [manufacturing/BOM.csv](file:///Users/royyanwicaksono/Dev/PCB/DC%2024%206%20CH%20light%20dimmer/manufacturing/BOM.csv)
- **Pick & Place (CPL)**: [manufacturing/dimmer_6ch_cpl.csv](file:///Users/royyanwicaksono/Dev/PCB/DC%2024%206%20CH%20light%20dimmer/manufacturing/dimmer_6ch_cpl.csv)
