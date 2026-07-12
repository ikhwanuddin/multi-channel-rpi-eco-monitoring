# 📚 MAARU Documentation Guide

## Overview

Complete documentation for **MAARU (Multi-Channel Acoustic Monitoring Unit)** — Raspberry Pi-based ecosystem monitoring system for tropical rainforest.

This documentation is designed for **various levels of understanding**: from non-technical people to hardware engineers.

---

## 🎯 Start Here (Reading Recommendations)

### **For Non-Technical Users / Non-Technical People**

**Goal**: Understand "What is MAARU and how does it work?"

1. **[MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md)** ⭐ **(START HERE)**
   - 5 min read
   - Visual overview
   - Key specs & costs
   - Troubleshooting quick tips

2. **[MAARU Physical Setup Diagram (Interactive)](../../maaru-physical-setup.html)**
   - Zoom & explore
   - Dark/light theme toggle
   - Export as PNG for presentations

3. **[architecture.md](architecture.md)** — Physical Hardware Setup section
   - Layered structure
   - Physical connections
   - Weather protection

### **For Hardware Engineers / Builders**

**Goal**: Understand technical specifications, power budget, maintenance.

1. **[physical-setup.md](physical-setup.md)** ⭐ **(COMPREHENSIVE)**
   - 20+ min read
   - Each component explained in detail
   - Specifications & options
   - Power calculations
   - Setup checklist
   - Maintenance schedule

2. **[architecture.md](architecture.md)** — Physical Hardware Setup section
   - Layers & structure
   - Connection diagram

3. **[MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md)**
   - Cost estimates
   - Hardware choices comparison

### **For Software Developers**

**Goal**: Understand system architecture, data flow, deployment.

1. **[quickstart.md](quickstart.md)**
   - Setup instructions
   - First recording

2. **[architecture.md](architecture.md)**
   - System Components (Software)
   - Boot Sequence
   - Recording Workflow
   - Core Scripts
   - Data Flow

3. **[config.md](config.md)**
   - Configuration options
   - Sensor settings
   - Cloud upload

4. **[cloud_setup.md](cloud_setup.md)**
   - Cloud storage integration
   - Rclone configuration

### **For Field Researchers / Biologists**

**Goal**: Deploy MAARU, record data, upload, troubleshoot in field.

1. **[quickstart.md](quickstart.md)**
   - How to start recording

2. **[MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md)**
   - Hardware choices
   - Power & runtime
   - Troubleshooting

3. **[troubleshooting.md](troubleshooting.md)**
   - Common issues
   - How to debug

4. **[log_guide.md](log_guide.md)**
   - How to read logs
   - What to look for

### **For Project Maintainers**

**Goal**: Understand full system, manage updates, plan improvements.

1. **[CLARIFICATION_SUMMARY.md](CLARIFICATION_SUMMARY.md)**
   - Design decisions
   - Why things are the way they are

2. **[architecture.md](architecture.md)** (complete)
   - Full system overview
   - All components & workflows

3. **[physical-setup.md](physical-setup.md)**
   - Maintenance schedules
   - Environmental factors

4. **[advanced_configuration.md](advanced_configuration.md)**
   - Performance tuning
   - Custom setups

---

## 📋 Complete Documentation Map

### **Quick References**
| File | Length | Purpose |
|------|--------|---------|
| **[MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md)** | 5 min | Everything on 1 page |
| **[CLARIFICATION_SUMMARY.md](CLARIFICATION_SUMMARY.md)** | 10 min | Design decisions explained |

### **Core Documentation**
| File | Length | Audience | Purpose |
|------|--------|----------|---------|
| **[architecture.md](architecture.md)** | 15 min | Everyone | System overview |
| **[physical-setup.md](physical-setup.md)** | 30 min | Hardware | Component details & specs |
| **[quickstart.md](quickstart.md)** | 10 min | Builders | Get running quickly |

### **Configuration & Operations**
| File | Length | Audience | Purpose |
|------|--------|----------|---------|
| **[config.md](config.md)** | 10 min | Developers | Configuration options |
| **[cloud_setup.md](cloud_setup.md)** | 10 min | Cloud users | Cloud storage integration |
| **[log_guide.md](log_guide.md)** | 10 min | Operators | How to read & debug logs |
| **[advanced_configuration.md](advanced_configuration.md)** | 15 min | Power users | Advanced tuning |

### **Help & Support**
| File | Length | Audience | Purpose |
|------|--------|----------|---------|
| **[troubleshooting.md](troubleshooting.md)** | 15 min | Everyone | Fixes for common issues |
| **[index.md](index.md)** | 5 min | Everyone | Documentation index |

### **Visual References**
| File | Format | Purpose |
|------|--------|---------|
| **[MAARU Physical Setup Diagram](../../maaru-physical-setup.html)** | Interactive SVG | Hardware structure visualization |
| **[maaru-physical-setup.architecture.json](../../maaru-physical-setup.architecture.json)** | JSON Schema | Diagram source (editable) |

---

## 🎯 Common Use Cases

### **"I want to build MAARU**"
→ Read in this order:
1. [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md) (understand what you're building)
2. [MAARU Physical Setup Diagram](../../maaru-physical-setup.html) (visualise structure)
3. [physical-setup.md](physical-setup.md) (detailed component specs)
4. [quickstart.md](quickstart.md) (assemble & test)

### **"MAARU isn't working, how do I debug?"**
→ Read in this order:
1. [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md) (Troubleshooting section)
2. [troubleshooting.md](troubleshooting.md) (detailed debugging)
3. [log_guide.md](log_guide.md) (read logs)
4. [architecture.md](architecture.md) (understand data flow)

### **"How much power will MAARU use?"**
→ Read:
1. [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md) (Power & Runtime)
2. [physical-setup.md](physical-setup.md) (Power & Electrical Specifications)
3. [config.md](config.md) (recording parameters affect power)

### **"I want to deploy MAARU in the field"**
→ Read in this order:
1. [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md) (quick overview)
2. [physical-setup.md](physical-setup.md) (Setup Checklist section)
3. [quickstart.md](quickstart.md) (how to start recording)
4. [troubleshooting.md](troubleshooting.md) (what can go wrong)

### **"I want to add features or customize MAARU"**
→ Read in this order:
1. [architecture.md](architecture.md) (understand system)
2. [advanced_configuration.md](advanced_configuration.md) (customization options)
3. [config.md](config.md) (available settings)
4. Code in `../src/`

### **"I need to explain MAARU to non-technical stakeholders"**
→ Share:
1. [MAARU Physical Setup Diagram](../../maaru-physical-setup.html) (visual)
2. [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md) (1-page summary)
3. Mention cost estimate from QUICK_REFERENCE

---

## 📊 Documentation Statistics

```
Total Documentation:
├─ Markdown files: 11 files, ~80 KB
├─ Interactive diagram: 1 HTML file, 50 KB
├─ Diagram schema: 1 JSON file, 5 KB
└─ Total: ~135 KB (fully self-contained)

Reading Time:
├─ Quick overview: 5 min (QUICK_REFERENCE)
├─ Core documentation: 30 min (architecture + physical-setup)
├─ Everything: 90 min (all docs)
└─ As reference: ~5 min per lookup
```

---

## 🔗 Cross-References

### **Frequently Linked Between Files**

- **architecture.md** → physical-setup.md (component details)
- **physical-setup.md** → troubleshooting.md (environmental issues)
- **config.md** → cloud_setup.md (cloud configuration)
- **quickstart.md** → config.md (after initial setup)
- **troubleshooting.md** → log_guide.md (debugging via logs)
- **all files** → MAARU_QUICK_REFERENCE.md (quick lookup)

### **External Resources**

- [Raspberry Pi Official Specs](https://www.raspberrypi.org/specifications/) — referenced in physical-setup.md
- [ReSpeaker 6-Mic Array Docs](https://wiki.seeedstudio.com/ReSpeaker_6-Mic_Array_for_Raspberry_Pi/) — sensor option
- [Sipeed 7-Mic Array Docs](https://github.com/sipeed/spk1110) — sensor option
- Cloud Storage API Docs (Box, Google Drive, etc.) — in cloud_setup.md

---

## 💾 How Documentation is Organised

```
multi-channel-rpi-eco-monitoring/
├── docs/
│   ├── README_DOCUMENTATION.md  ← You are here
│   ├── index.md                 ← Doc index
│   │
│   ├── MAARU_QUICK_REFERENCE.md ⭐ Start for non-technical
│   ├── CLARIFICATION_SUMMARY.md
│   │
│   ├── architecture.md          ⭐ Core overview
│   ├── physical-setup.md        ⭐ Hardware details
│   │
│   ├── quickstart.md            ⭐ Get running
│   ├── config.md
│   ├── cloud_setup.md
│   │
│   ├── advanced_configuration.md
│   ├── log_guide.md
│   ├── troubleshooting.md
│   │
│   └── [implementation docs in src/]
│
├── [Source code]
├── [Configuration]
└── [Data files]

../
├── maaru-physical-setup.html    ⭐ Interactive diagram
├── maaru-physical-setup.architecture.json
└── [Supporting docs from archify skill]
```

---

## ✨ Key Documentation Highlights

### **What Makes MAARU Unique**

These docs explain why MAARU is designed the way it is:

1. **Nested Protection** (3 layers) — read [physical-setup.md](physical-setup.md)
   - Why is dry bag separate from main enclosure?
   - Why is plastic roof needed?
   - Why is silica gel critical?

2. **Power Budget Constraints** — read [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md)
   - Why powerbank is limiting factor
   - How to extend runtime
   - Trade-offs between components

3. **Environmental Adaptation** — read [physical-setup.md](physical-setup.md)
   - Specifically designed for tropical rainforest
   - 80-95% humidity
   - Frequent heavy rain
   - Temperature swings

4. **Operational Flexibility** — read [config.md](config.md) + [advanced_configuration.md](advanced_configuration.md)
   - Offline or online mode
   - Multiple sensor options
   - Customisable recording parameters
   - Cloud upload strategies

---

## 🤤 Design Philosophy

**MAARU is not just "Raspberry Pi + Mic Array"**

It's a **systems engineering solution** that balances:
- 🔧 Hardware reliability (tropical environment)
- ⚡ Power efficiency (battery-powered)
- 📊 Data quality (7-channel audio @ 16 kHz)
- 🌱 Ecological value (ecosystem monitoring)
- 💰 Cost effectiveness (entry-level monitoring)

This documentation reflects those priorities. Each design choice (hardware, protection, configuration) is explained with trade-offs and constraints.

---

## 📞 Contributing to Documentation

### **Found a bug in the docs?**
- Create issue with specific file & section
- Quote the problematic text
- Suggest correction

### **Want to add a new section?**
- Open issue to discuss
- Propose which doc file it should go in
- Ensure it fits the "Start Here" recommendations

### **Updated MAARU hardware?**
- Update [physical-setup.md](physical-setup.md)
- Update [MAARU_QUICK_REFERENCE.md](MAARU_QUICK_REFERENCE.md) specs table
- Re-render diagram if connections changed

---

## 📅 Documentation Maintenance

| Aspect | Update Frequency | Owner |
|--------|-------------------|-------|
| Quick Reference | Quarterly | Maintainer |
| Hardware specs | When components change | Hardware engineer |
| Software configs | When code changes | Developer |
| Troubleshooting | As issues emerge | Field team |
| Examples | When tested | DevOps/QA |
## 📋 Learning Paths

### **Path 1: Beginner (Non-Technical)**
```
Time: 20 minutes
Goal: Understand MAARU at high level

MAARU_QUICK_REFERENCE.md (5 min)
    ↓
MAARU Physical Setup Diagram (10 min)
    ↓
architecture.md - Physical section (5 min)
```

### **Path 2: Builder (Hardware)**
```
Time: 90 minutes
Goal: Build & deploy MAARU

MAARU_QUICK_REFERENCE.md (5 min)
    ↓
physical-setup.md (40 min)
    ↓
MAARU Physical Setup Diagram (5 min)
    ↓
quickstart.md (10 min)
    ↓
Setup checklist from physical-setup.md (20 min)
    ↓
Test recording (10 min)
```

### **Path 3: Developer (Software)**
```
Time: 60 minutes
Goal: Understand & extend system

MAARU_QUICK_REFERENCE.md (5 min)
    ↓
architecture.md (15 min)
    ↓
config.md (10 min)
    ↓
cloud_setup.md (10 min)
    ↓
quickstart.md (10 min)
    ↓
Browse source code in ../src/
```

### **Path 4: Operator (Field)**
```
Time: 30 minutes
Goal: Deploy, maintain, troubleshoot

MAARU_QUICK_REFERENCE.md (5 min)
    ↓
physical-setup.md - Setup Checklist (10 min)
    ↓
quickstart.md (5 min)
    ↓
troubleshooting.md (10 min)
```
## 🎯 Documentation Goals

✅ **Clarity**: Non-technical people can understand basic concepts
✅ **Completeness**: Engineers have all info needed to build & maintain
✅ **Usability**: Quick lookup for common questions
✅ **Maintainability**: Easy to update when things change
✅ **Accessibility**: Multiple formats (markdown, interactive diagram, JSON schema)

---

## 🗨️ Notes

- All documentation assumes **Raspberry Pi OS Lite** (Linux)
- Examples use **Python 3** (3.7+)
- Sensor examples: **ReSpeaker 6-Mic** and **Sipeed 7-Mic**
- Cloud provider examples: **Box** and **Google Drive** (via rclone)
- Location context: **Tropical rainforest in Lampung, Indonesia**

---

**Last Updated**: July 2024
**For**: Multi-Channel RPi Ecosystem Monitoring Project (MAARU)
**Maintained By**: [Your name/team]

For questions about the documentation itself, see [index.md](index.md) or open an issue.
