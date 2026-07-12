# MAARU Physical Setup & Hardware Components

## Overview

MAARU (Multi-Channel Acoustic Monitoring Unit) is an ecosystem monitoring system specifically designed for extreme tropical environments. This document explains each hardware component, how it works, and how it is protected from natural conditions.

**Interactive Visualisation**: Open [MAARU Physical Setup Diagram](../../maaru-physical-setup.html) to view the layered structure and physical connections.

---

## 🏗️ Layered Structure (Nested Protection Scheme)

MAARU uses a layered approach to protect components from extreme weather:

```
PLASTIC ROOF (Roof)
    ↓
FOOD BOX (Main Enclosure)
    ├─ Raspberry Pi
    ├─ Mic Sensor Array
    ├─ Micro SD Card
    ├─ USB WiFi Adapter
    ├─ Silica Gel
    └─ IP68 Acoustic Membrane
    ↓
DRY BAG (Power Protection)
    └─ Powerbank
        ↓
    USB Cable
        ↓
    [Connected to Pi]

Mounting:
    Rope & Rubber → Tree
```

Each layer has a specific function for survival in tropical rainforest.

---

## 🔧 Hardware Components

### 1. **Raspberry Pi 3B or Zero 2W**

#### Choice & Specifications

| Aspect | Pi 3B | Pi Zero 2W | Recommendation |
|--------|-------|-----------|----------------|
| **CPU** | 1.4 GHz quad-core | 1 GHz dual-core | 3B (more stable) |
| **RAM** | 1 GB | 512 MB | 3B (for audio buffering) |
| **Power Draw** | 0.5-1.5A | 0.2-0.8A | Zero 2W (if power-critical) |
| **GPIO Pins** | Full set | Full set | Both OK |
| **USB Ports** | 4× USB-A | 1× Micro-USB | 3B (more flexible) |
| **Cost** | ~$45 | ~$28 | Zero 2W (budget), 3B (reliable) |
| **Heat Sink Needed?** | Rarely | No | 3B in hot weather |
| **Recording Duration** | 6-8 hrs | 15-18 hrs | Zero 2W (more efficient) |

#### Recommendations for MAARU
- **Location with stable WiFi**: Pi 3B (more stable for 24/7 operation)
- **Offline location, limited budget**: Pi Zero 2W (more power-efficient, longer powerbank life)

#### Function in MAARU
1. **Input**: Receives audio signal from microphone sensor
2. **Processing**: Encodes audio in FLAC format real-time
3. **Storage**: Manages local files on Micro SD card
4. **Network**: Uploads files via USB WiFi adapter (optional)
5. **Logging**: Records all events for debugging

---

### 2. **Microphone Sensor Array**

MAARU supports two sensor types. Choose based on needs and budget.

#### **Option A: ReSpeaker 6-Mic Array**

**Specifications:**
- **Channels**: 6 simultaneously recorded channels
- **Connection**: GPIO pins (I2S over GPIO)
- **Power**: 0.3-0.5A @ 5V
- **Frequency Response**: 50 Hz - 20 kHz
- **Built-in Features**: LED ring, on-board codec
- **Impedance**: 16 Ω, 32 Ω, 64 Ω (auto-detect)
- **Cost**: ~$60-80

**Advantages:**
- GPIO connection (does not use USB port)
- More power-efficient
- Built-in amplifier
- Battle-tested on many projects

**Disadvantages:**
- Only 6 channels (vs Sipeed 7-mic)
- Must solder GPIO pins if no header pre-installed

**Connected to**: GPIO pins on Raspberry Pi (I2S protocol)

---

#### **Option B: Sipeed 7-Mic Array**

**Specifications:**
- **Channels**: 7 simultaneously recorded channels
- **Connection**: USB Type-C (or USB-A via adapter)
- **Power**: Self-powered via USB (0.5-0.8A)
- **Frequency Response**: 50 Hz - 20 kHz
- **Beamforming**: Software-based, for noise cancellation
- **Codec**: Built-in USB Audio Class compliant
- **Cost**: ~$50-70

**Advantages:**
- 7 channels (1 more than ReSpeaker)
- Self-powered via USB (easier power management)
- Plug-and-play (minimal setup)
- More modular

**Disadvantages:**
- Uses 1 USB port (leaves 1 port for WiFi adapter)
- Slightly higher power draw

**Connected to**: USB port on Raspberry Pi

---

#### Sensor Recommendations
- **Location with stable WiFi, long recording sessions**: Sipeed 7-Mic (more channels, plug-and-play)
- **Tight budget, power budget critical**: ReSpeaker 6-Mic (GPIO, more power-efficient)

---

### 3. **Micro SD Card**

**Function**: Local storage for audio recordings and system files.

**Recommended Specifications:**
- **Capacity**: 64 GB - 256 GB (depends on retention policy)
- **Speed Class**: Class 10 minimum, UHS-I recommended
- **Read Speed**: 150+ MB/s
- **Write Speed**: 100+ MB/s
- **Type**: microSD UHS-I (not plain SD)

**File Capacity Example:**
```
Format: FLAC
Channels: 7
Sample Rate: 16 kHz
Bit Depth: 16 bits
Duration per session: 20 minutes

Size per session ≈ 270 MB

64 GB card → ~237 sessions (80 hours of recording)
128 GB card → ~474 sessions (158 hours)
256 GB card → ~948 sessions (316 hours)
```

**Location**: Within the food box, protected from weather

**Durability**: microSD cards in tropical environment:
- Lifetime: 3-5 years (depends on write cycles)
- Recommendation: Rotate every 6 months for redundancy

---

### 4. **USB WiFi Adapter**

**Function**: Wireless connection for SSH access and cloud uploads (optional).

**Recommended Specifications:**
- **Standard**: 802.11ac (WiFi 5) minimum
- **Power**: 0.3-0.5A @ 5V
- **Compatibility**: Raspberry Pi driver support (check beforehand!)
- **Antenna**: External antenna preferred (better range in tropical environment)
- **Cost**: $15-30

**Recommended Adapters:**
- TP-Link TL-WN722N (tested with Pi, external antenna)
- Realtek RTL8811AU (good performance, driver available for Pi)
- Avoid: Built-in only antennas in humid areas

**Location**: Within the food box, antenna can protrude (small, no special protection needed)

**Connection**: USB port on Raspberry Pi

**Power Consideration**: 
- Total USB power available: ~1A (shared with Sipeed if used)
- If using Sipeed 7-Mic: Ensure powerbank can supply ≥2A for both Mic + WiFi

---

### 5. **Powerbank (Power Supply)**

**Function**: Primary power source for entire MAARU.

**Recommended Specifications:**

| Aspect | Value | Notes |
|--------|-------|-------|
| **Capacity** | 20,000 mAh | Standard for 6-18 hours recording |
| **Voltage** | 5V (dual USB-A port) | See power requirement |
| **Output Current** | 2-3A | IMPORTANT: Must support ≥2A |
| **Efficiency** | 80-90% | Not all 20,000 mAh is usable |
| **Lifespan** | 300-500 charge cycles | ~1-2 years with daily use |
| **Cost** | $15-40 | Don't buy extremely cheap |

**Power Budget for MAARU:**

```
Typical Draw:
├─ Raspberry Pi 3B: 0.5-1.0A
├─ ReSpeaker 6-Mic: 0.3-0.5A
├─ Micro SD: <0.05A (negligible)
├─ USB WiFi: 0.3-0.5A (if enabled)
└─ Overhead: ~0.1A
├────────────────────
Total: 1.1-2.5A depending on load

Recording Session Duration:
─────────────────────
20,000 mAh × 0.85 efficiency ÷ 1.5A avg = 11.3 hours
20,000 mAh × 0.85 efficiency ÷ 2.0A avg = 8.5 hours
```

**Location**: Inside dry bag, outside main food box

**Connection**: USB-A to Micro-USB cable to Pi power port

---

### 6. **Silica Gel**

**Function**: Humidity control inside food box.

**Why Important in Tropical Rainforest?**
- Environment: 80-95% relative humidity
- Risk: Condensation inside enclosure when temperature drops at night
- Damage: PCB corrosion, short circuits, sensor malfunction

**Specifications:**
- **Type**: Colour-indicating silica gel (blue → pink when saturated)
- **Quantity**: 50-100g per enclosure
- **Replacement**: Every 1-2 weeks (depends on humidity)
- **Cost**: $2-5 per pack
- **Recharge**: Can be oven-dried at 100°C × 2 hours for reuse

**Placement**: Scattered inside food box, away from electronic components

---

### 7. **IP68 Acoustic Membrane**

**Function**: Protects microphone holes from water while maintaining acoustic transparency.

**Specifications:**
- **Material**: Hydrophobic PTFE membrane
- **Rating**: IP68 (fully sealed against liquid)
- **Acoustic Transparency**: Minimal loss @ 16 kHz
- **Thickness**: 0.1-0.15 mm
- **Cost**: $5-20 per metre

**Installation:**
1. Cut circular piece to cover each microphone hole
2. Adhesive backing or double-sided tape
3. Seal edges with silicone sealant
4. Test with water spray before deployment

**Durability**: 6-12 months in tropical climate, replace if visible damage occurs

---

### 8. **Silicon Sealant (Waterproofing)**

**Function**: Seals all cable holes and prevents water ingress.

**Specifications:**
- **Type**: GE Silicone II or equivalent (outdoor-grade)
- **Cure Time**: 24 hours
- **Colour**: Clear or white (not critical)
- **Quantity**: 1 cartridge per deployment

**Application Points:**
1. USB cable entry point (Micro USB power)
2. USB cable exit point (for powerbank/WiFi)
3. GPIO header (if present, for ReSpeaker)
4. Seams on food box
5. Microphone hole perimeter (after membrane installation)

**Installation:**
1. Clean area with isopropyl alcohol
2. Apply continuous bead of silicone
3. Let cure 24 hours before exposure to water

---

### 9. **Plastic Roof (Waterproof Roof)**

**Function**: Protection from direct rain water.

**Material & Design:**
- **Material**: Used plastic oil container (or food-grade plastic)
- **Design**: Peak/roof shape (slopes down for water runoff)
- **Diameter**: Minimum 5-10 cm larger than food box base
- **Mounting**: Can be tied with zip ties, need not be seamless

**Setup:**
```
        ┌─────┐         Plastic Roof
        │         │
    ┌──┴────┬──┴───┐     (slopes outward)
    │        │        │
    │   [Food Box]   │
    │        │        │
    └────┬──┴───┘
         │      │
      ┌─┴──│         Dry Bag
      │ 20K │  │         (below box)
      └────┘  │
         │      │
    [Rope & Rubber → Tree]
```

---

### 10. **Dry Bag (Power Protection)**

**Function**: Waterproof casing for powerbank.

**Specifications:**
- **Type**: Dry bag for sports (swimming, outdoor)
- **Material**: Nylon + TPU, fully waterproof
- **Capacity**: 5-10L (fit 20K mAh powerbank + cables)
- **Sealing**: Roll-top or zipper with waterproof tape
- **Cost**: $10-20

**Placement**: Remains within plastic roof boundary, but separate from main food box for thermal distribution.

**Tips:**
- Buy one with drainage hole at bottom (moisture can leak out)
- Silica gel can also be placed inside dry bag
- Include USB-A to Micro-USB cable inside

---

### 11. **USB Cable (Power Delivery)**

**Function**: Connects powerbank to Raspberry Pi.

**Specifications:**
- **Type**: USB-A (male) to Micro-USB (male)
- **Length**: 0.5-1 metre (sufficient reach from dry bag to food box)
- **Current Rating**: Minimum 2A (for optimal power delivery)
- **Shielding**: Shielded recommended (interference in tropical forest)
- **Cost**: $2-5

**Important**: Do not use overly thin cables; voltage drop will reduce effective power to Pi.

---

### 12. **Rope & Rubber (Mounting Hardware)**

**Function**: Secures entire MAARU unit to tree.

**Materials:**
- **Rope**: Synthetic rope (does not rot in high humidity)
- **Rubber**: Rubber straps or bungee cords (flex in strong wind)
- **Zip Ties**: Extra for securing cables & parts

**Mounting Strategy:**
1. Choose stable tree, minimum 2 metres high
2. Create sling from rope/rubber around food box
3. Tie to tree with minimum 3 contact points
4. Don't tie too tight (allow flex), don't leave slack (allow swing)
5. Check every 2 weeks for rope wear

**Safety**: Ensure MAARU cannot fall if 1 rope breaks (redundancy).

---

## 🌧️ Environmental Protection Summary

| Component | Threat | Protection | Check Interval |
|-----------|--------|-----------|----------------|
| **Silica Gel** | Humidity (80-95%) | Absorbs moisture | 1-2 weeks (replace when pink) |
| **Acoustic Membrane** | Water ingress @ mic holes | IP68 hydrophobic PTFE | 3-6 months (inspect for damage) |
| **Silicon Sealant** | Water leaks @ seams | Sealed all openings | 2-3 months (check for cracks) |
| **Plastic Roof** | Direct rain on enclosure | Roof shape + water runoff | 1-2 weeks (after heavy rain) |
| **Dry Bag** | Powerbank moisture | Waterproof casing | 1-2 weeks (check seal integrity) |
| **Rope & Rubber** | Physical damage (wind, animals) | Mounting redundancy | 2 weeks (check for wear/fraying) |

---

## 🔌 Power & Electrical Specifications

### Total System Power Budget

**Peak Power Draw:**
```
Raspberry Pi (3B): 1.0A
ReSpeaker 6-Mic: 0.5A
OR Sipeed 7-Mic: 0.8A
USB WiFi: 0.5A
───────────
Peak (with both Mic + WiFi): 2.3A (Sipeed) or 2.0A (ReSpeaker)
```

**Typical Power Draw (recording only, WiFi off):**
```
Raspberry Pi: 0.7A
ReSpeaker 6-Mic: 0.3A
───────────
Typical: ~1.0A (ReSpeaker)

OR

Raspberry Pi: 0.7A
Sipeed 7-Mic: 0.6A
───────────
Typical: ~1.3A (Sipeed)
```

### Recording Duration Calculation

```
Powerbank Capacity: 20,000 mAh
Actual usable energy: 20,000 × 0.85 efficiency = 17,000 mAh

Duration = Usable Energy ÷ Average Current Draw
────────────────────────────

Scenario 1: ReSpeaker 6-Mic only
Duration = 17,000 mAh ÷ 1.0A = 17 hours

Scenario 2: Sipeed 7-Mic only
Duration = 17,000 mAh ÷ 1.3A = 13 hours

Scenario 3: With WiFi enabled (upload every hour)
Duration = 17,000 mAh ÷ 1.8A = 9.4 hours
```

---

## 🔧 Setup Checklist

### Pre-Deployment

- [ ] Raspberry Pi flashed with Raspberry Pi OS Lite (latest)
- [ ] Sensor (ReSpeaker or Sipeed) tested & connected
- [ ] Micro SD card formatted & mounted
- [ ] USB WiFi adapter installed (if needed)
- [ ] Powerbank fully charged
- [ ] Silica gel placed inside enclosure
- [ ] Acoustic membrane installed on all mic holes
- [ ] Silicon sealant applied to all seams (24h cure)
- [ ] USB cable rated for 2A+ power delivery
- [ ] Plastic roof attached & secure
- [ ] Dry bag sealed & rope/rubber ready

### At Deployment Site

- [ ] Check roof shape (water should flow outward)
- [ ] Verify rope doesn't restrict thermal airflow
- [ ] Confirm Micro USB port facing downward (water runoff)
- [ ] Test WiFi reception (if enabled)
- [ ] Record 5 minutes audio & verify quality
- [ ] Check all seals with water spray (non-damaging test)
- [ ] Mark location & date on unit

### Maintenance Schedule

**Weekly:**
- Check silica gel colour (replace if pink)
- Verify device still mounted securely
- Inspect for visible damage/cracks

**Monthly:**
- Test full power cycle (shutdown & restart)
- Download latest recordings for backup
- Check for water seepage in enclosure

**Quarterly:**
- Replace acoustic membrane
- Re-apply silicon sealant (if cracks visible)
- Rotate Micro SD cards (if multiple units)

**Annually:**
- Replace Micro SD card (preventive)
- Replace rope & rubber (wear out from UV)
- Deep clean with isopropyl alcohol

---

## 📊 Typical Power Consumption Over 24-hour Cycle

```
Time    Activity          Current    Duration
────────────────────────────
00:00   Idle (night)      0.7A       4 hours = 2.8 Ah
04:00   Recording starts  1.3A       8 hours = 10.4 Ah
12:00   Break + idle      0.7A       8 hours = 5.6 Ah
20:00   Recording resumes 1.3A       4 hours = 5.2 Ah
────────────────────────────
Daily total: 24 Ah

20,000 mAh × 0.85 ≈ 17,000 mAh available
Shortfall: 7,000 mAh (need additional powerbank or solar panel)
```

**Recommendations for 24-hour operation:**
- Use 2× 20K mAh powerbanks, or
- Add solar panel (5W minimum) for trickle charge, or
- Reduce recording hours (10-12 hours per day instead of 16+)

---

## ⚠️ Known Issues & Mitigations

| Issue | Cause | Symptom | Mitigation |
|-------|-------|---------|------------|
| **Water Condensation** | Temperature drop at night | Foggy enclosure, audio noise | Silica gel + ventilation |
| **Rust on GPIO** | High humidity + salt (coastal) | Sensor not detected | Apply silicon conformal coating |
| **Slow Micro SD Write** | Card aging | File truncation | Monitor write speed, replace annually |
| **USB WiFi Dropout** | Interference + weather | Lost SSH connection | Use external antenna, relocate position |
| **Battery Rapid Drain** | Defective cell | Shorter runtime | Use trusted brand powerbank |
| **Thermal Throttling** | Enclosed heat + ambient >30°C | Slower CPU, incomplete recordings | Add passive heat sink, improve airflow |

---

## 📚 References & Additional Resources

- [Raspberry Pi Official Specs](https://www.raspberrypi.org/specifications/)
- [ReSpeaker 6-Mic Array Docs](https://wiki.seeedstudio.com/ReSpeaker_6-Mic_Array_for_Raspberry_Pi/)
- [Sipeed 7-Mic Array Docs](https://github.com/sipeed/spk1110)
- [Dry Bag Best Practices](https://www.rei.com/learn/expert-advice/dry-bags)
- [Tropical Climate Electronics Protection](https://en.wikipedia.org/wiki/Salt_spray_testing)

---

## 🎯 Next Steps

1. **Build & Test**: Assemble MAARU prototype in lab before deployment
2. **Field Test**: Deploy for 1-2 weeks at target location
3. **Monitor**: Check logs & power consumption daily
4. **Iterate**: Adjust protection based on real-world conditions
5. **Document**: Record temperature, humidity, issues encountered

---

*This document will be updated based on lessons learned from field deployments.*
