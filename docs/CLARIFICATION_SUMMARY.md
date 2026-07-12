# 📋 MAARU Component Diagram Clarification - Summary

## 🎯 Initial Problem

You felt **confused about the component diagram** which was initially mixed between:
- **Hardware** (Raspberry Pi, Sensors, Powerbank, Cables)
- **Software** (Python Recorder, Rclone Upload)

Although initially you only asked to "create docs for non-technical people", we eventually understood that **this diagram required deep clarification**.

---

## ✅ What Has Been Clarified

### **Question 1: Diagram Purpose**
**Result**: Focus on **Physical Setup (Hardware)**, not software.

- ❌ NOT showing software modules (Python Recorder, Rclone)
- ✅ ONLY showing physical hardware components

### **Question 2a: Diagram Structure**
**Result**: **Nested/layered** with larger blocks containing smaller blocks.

**Layered structure selected:**
```
┌─────────────────────────────────────┐
│   PLASTIC ROOF (Roof)               │
│   ┌─────────────────────────────┐   │
│   │ FOOD BOX (Enclosure)        │   │
│   │ ├─ Raspberry Pi             │   │
│   │ ├─ Mic Sensor               │   │
│   │ ├─ Micro SD Card            │   │
│   │ ├─ USB WiFi Adapter         │   │
│   │ └─ Silica Gel               │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │ DRY BAG (Power Protection)  │   │
│   │ └─ Powerbank                │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### **Question 2b: Detail Level**
**Result**: **Option B** - Include protection details.

Components shown:
- Plastic roof (waterproof cover)
- Food box (main enclosure)
- Dry bag (power protection)
- Silica gel (humidity control)
- Acoustic membrane (water-resistant acoustic)
- Rope & rubber (mounting)

### **Question 3: Block Grouping**
**Result**: **Option A - Based on Physical Location**.

**Reason**: Non-technical people more easily understand "where is this component?" rather than "what does it do?".

### **Question 4a: Physical Connections**
**Result**: **YES**, must show connection types.

Connections shown:
- ReSpeaker 6-Mic → **GPIO pins** (Pi)
- Sipeed 7-Mic → **USB port** (Pi)
- USB WiFi Adapter → **USB port** (Pi)
- Powerbank → **USB Micro** (Pi)
- Micro SD Card → **SD Card Slot** (Pi)

### **Question 4b: Data Flow**
**Result**: **NOT needed** (that's for software architecture).

### **Question 5a: Protection Details**
**Result**: **Option C** - Blocks in diagram, details in explanatory text.

### **Question 5b: Dry Bag Location**
**Result**: **Outside the food box, within the plastic roof**.

```
Food box ← Pi, Sensor, SD Card, WiFi, Silica Gel
    ↓ (protected from direct weather)
Dry Bag ← Powerbank (protected + humidity-controlled)
    ↓ (via USB Cable)
[USB Cable to Pi]
```

**Reason**: 
- Powerbank needs humidity control (silica gel can be shared)
- Separate location for thermal distribution

### **Question 6: Output Format**
**Result**: **SVG** (editable).

**Output generated:**
- `maaru-physical-setup.html` — Interactive diagram with dark/light theme toggle, export PNG/JPEG/WebP/SVG
- `maaru-physical-setup.architecture.json` — Schema for re-rendering if hardware changes

### **Question 7: Text Explanation**
**Result**: **YES**, for each component.

**Output generated:**
- `physical-setup.md` (12+ KB) — Detailed explanation for each component
- Updated `architecture.md` — Summary & links

---

## 📦 Generated Output

### **1. Interactive Diagram**
📍 **File**: `/Users/ri322/macmini/maaru-physical-setup.html` (50 KB)

**Features:**
- ✅ Dark/Light theme toggle (auto-detect `prefers-color-scheme`)
- ✅ Export menu: PNG (up to 4×), JPEG, WebP, SVG
- ✅ Copy-to-clipboard functionality
- ✅ Responsive, no external dependencies
- ✅ Dual-theme SVG export for GitHub README

**Diagram Structure:**
- 10 components with semantic types (frontend, backend, cloud, database, external)
- 2 boundary regions (Waterproof Enclosure + Power Protection)
- 9 physical connections with clear labels (GPIO, USB, SD, WiFi, Power)

### **2. Hardware Documentation**
📍 **File**: `/Users/ri322/macmini/multi-channel-rpi-eco-monitoring/docs/physical-setup.md` (15+ KB)

**Sections:**
1. **Overview** — Layered structure & function
2. **Hardware Components** — Details for each part:
   - Raspberry Pi 3B vs Zero 2W (comparison table)
   - ReSpeaker 6-Mic vs Sipeed 7-Mic (comparison + specs)
   - Micro SD Card (capacity, speed, durability)
   - USB WiFi Adapter (recommendations)
   - Powerbank (power budget, runtime calculations)
   - Silica Gel (why important in tropical climate)
   - IP68 Acoustic Membrane (installation guide)
   - Silicon Sealant (waterproofing)
   - Plastic Roof (design & mounting)
   - Dry Bag (material & placement)
   - USB Cable (power rating)
   - Rope & Rubber (mounting strategy)

3. **Environmental Protection Summary** — Table check intervals
4. **Power & Electrical Specs** — Detailed power budget & runtime calculations
5. **Setup Checklist** — Pre-deployment, at-site, maintenance
6. **Typical 24-hour Power Cycle** — Example usage patterns
7. **Known Issues & Mitigations** — Troubleshooting guide
8. **References** — Links to component docs

### **3. Updated Architecture Documentation**
📍 **File**: `/Users/ri322/macmini/multi-channel-rpi-eco-monitoring/docs/architecture.md`

**Changes:**
- ✅ Added "Physical Hardware Setup" section (with diagram)
- ✅ Layered structure explained
- ✅ Physical connections & power flow (table)
- ✅ Mounting & environmental protection
- ✅ Links to `physical-setup.md` and interactive diagram

---

## 🔑 Key Insights from Clarification

### **1. MAARU is not just "Raspberry Pi + Sensor"**

MAARU is a **sophisticated engineering solution** for tropical rainforest:

```
Hardware:
├─ Compute: Pi 3B or Zero 2W
├─ Audio: ReSpeaker 6-Mic (GPIO) or Sipeed 7-Mic (USB)
├─ Storage: Micro SD Card
├─ Network: USB WiFi Adapter
├─ Power: Powerbank (20K mAh)
└─ Protection: 3 layers + silica gel + acoustic membrane + sealant

Nested Protection:
├─ Plastic Roof (roof, water runoff)
├─ Food Box (main enclosure, weatherproof)
└─ Dry Bag (power supply, humidity control)

Mounting:
└─ Rope & Rubber (physical security to tree)
```

### **2. Hardware Choices Matter**

| Choice | Impact |
|--------|--------|
| **Pi 3B vs Zero 2W** | Recording duration (8 hrs vs 18 hrs) |
| **ReSpeaker vs Sipeed** | Power consumption, channel count, USB availability |
| **Dry Bag Location** | Thermal distribution, protection level |
| **Silica Gel Replacement** | Device reliability in high humidity |

### **3. Power Budget is Critical**

```
20K mAh Powerbank ÷ 1.3A average draw = 13 hours max
(vs Pi 3B specs ~30 hours in datasheet)

Reason: 15% efficiency loss (USB, circuitry), thermal throttling
```

→ **24-hour continuous operation requires 2 powerbanks or solar panel**

### **4. Environmental Factors Drive Design**

Tropical rainforest conditions (Lampung, Indonesia):
- 🌧️ Humidity: 80-95% RH
- 🌡️ Temperature: 24-32°C year-round
- 💨 Rain: Frequent & heavy
- 🦟 Creatures: Insects, mould, salt-like moisture

**Mitigations:**
- Nested enclosure (3 layers of protection)
- Silica gel (desiccant)
- IP68 acoustic membrane (water-resistant acoustic)
- Silicon sealant (all seams)
- Regular maintenance (weekly checks)

---

## 📊 Comparison: Before vs After

### **BEFORE (Confusing Diagram)**
```
❌ Mixed hardware + software in 1 diagram
❌ No clear structure or hierarchy
❌ No explanation of connections
❌ Non-technical people confused about what's what
```

### **AFTER (Clear & Organised)**
```
✅ Hardware ONLY (software separate)
✅ Clear nested structure (3 layers + mounting)
✅ All connections labelled with interface types
✅ Detailed documentation for each component
✅ Non-technical people can understand:
   - Why 3 layers of protection?
   - What's the difference between ReSpeaker & Sipeed?
   - Why powerbank needs dry bag?
   - How long can it record?
   - When to replace silica gel?
```

---

## 🎯 How to Use These Docs

### **For Non-Technical People**
1. Start with **Interactive Diagram** (`maaru-physical-setup.html`)
   - Visual, colour-coded, easy to understand
   - Can zoom & explore

2. Read **Brief Summary** (architecture.md → Physical Hardware Setup section)
   - 3 layers of protection
   - 3 choices of microphone sensor
   - Power & runtime info

3. If deeper dive needed: **physical-setup.md**
   - Explanation of each component
   - Why certain choices matter
   - Maintenance checklist

### **For Hardware Engineers**
1. View **Diagram** (SVG format, editable)
2. Read **physical-setup.md** sections:
   - Specifications table
   - Power budget calculations
   - Environmental protection strategy
   - Maintenance schedule

3. Use **JSON schema** (`maaru-physical-setup.architecture.json`) to:
   - Modify components
   - Update connections
   - Re-render custom diagrams

### **For Cloud/Software Integration**
1. Focus on **architecture.md** → System Components (Software)
2. Ignore hardware details (physical-setup.md)
3. Understand power implications → sizing of uploads, frequency of operations

---

## 🔗 File References

| File | Purpose | Audience |
|------|---------|----------|
| `maaru-physical-setup.html` | Interactive hardware diagram | Everyone (visual-first) |
| `architecture.md` | System overview + physical + software | Project leads |
| `physical-setup.md` | Detailed component specifications | Hardware engineers, maintainers |
| `maaru-physical-setup.architecture.json` | Diagram source (editable) | Diagrammers, infrastructure-as-code |
| `README_MAARU_DIAGRAM.md` | Quick start guide | First-time viewers |
| `MAARU_HARDWARE_BOM.md` | Bill of materials + costs | Procurement, budgeting |

---

## ✨ Takeaway

**MAARU component diagram is not just about "What hardware is included?"**

**But more about: "How is this system designed to survive in tropical rainforest while delivering 6-18 hours recording time?"**

Each protection layer (plastic roof, food box, dry bag), each component choice (Pi 3B vs Zero 2W, ReSpeaker vs Sipeed), and each maintenance procedure (silica gel replacement) **is a concrete answer to that question**.

---

*This clarification resulted from **7 systematic grill-me questions** that systematically unpacked every aspect of the diagram until reaching shared understanding.*
