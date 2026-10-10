# 🚀 MAARU Quick Reference Card

## What is MAARU?

**MAARU** = Multichannel Acoustic Autonomous Recording Unit

A waterproof, tropical-climate-hardened system that records ecosystem sounds on a Raspberry Pi with a multichannel microphone array (Sipeed: 8 recorded channels; ReSpeaker 6-Mic: 6). Records for 6-18 hours per charge, stores audio locally, and can upload to cloud storage.

**Location**: Tethered to a tree in tropical rainforest (Lampung, Indonesia)

---

## 📦 What's Inside MAARU

### **3 Protection Layers** (nested)

```
Layer 1: Plastic Roof
    ↓
Layer 2: Food Box (Main Enclosure) ← All electronics here
    - Raspberry Pi (brain)
    - Sensor Mic Array (ear) — pick ONE:
      • ReSpeaker 6-Mic (GPIO) → 1.0A power, 6 channels
      • Sipeed 6+1 Mic + MA-USB8 board (USB) → 1.3A power, 8 recorded channels
    - Micro SD Card (memory)
    - USB WiFi Adapter (network)
    - Silica Gel (dries humidity)
    ↓
Layer 3: Dry Bag (Power box) ← Powerbank lives here
    - Powerbank 20K mAh (battery)
    - USB Cable (connects to Pi)

Mounting: Rope & Rubber (rope + rubber) → Tied to tree
```

---

## ⚡ Power & Runtime

### **Power Draw (Typical)**

| Component | Current |
|-----------|---------|
| Raspberry Pi | 0.7A |
| ReSpeaker 6-Mic | 0.3A |
| **Total (ReSpeaker)** | **~1.0A** |
| --- | --- |
| Sipeed | 0.6A |
| **Total (Sipeed)** | **~1.3A** |

### **Recording Duration**

| Scenario | Runtime |
|----------|---------|
| **ReSpeaker only** | ~17 hours |
| **Sipeed only** | ~13 hours |
| **With WiFi enabled** | ~9 hours |
| **Both Mic + WiFi** | ~8 hours |

**Note**: 20K mAh powerbank, 85% efficiency = 17,000 mAh usable

---

## 🎯 Hardware Choices at a Glance

### **Raspberry Pi: 3B or Zero 2W?**

| Aspect | Pi 3B | Zero 2W |
|--------|-------|---------|
| **Performance** | Better | Lower |
| **Power Draw** | 0.5-1.5A | 0.2-0.8A |
| **Price** | ~$45 | ~$28 |
| **Best For** | Stable, WiFi | Budget, long recording |

→ **Recommended**: Pi 3B (more reliable)

### **Microphone: ReSpeaker or Sipeed?**

| Aspect | ReSpeaker 6-Mic | Sipeed 6+1 Mic (MA-USB8) |
|--------|-----------------|--------------|
| **Channels** | 6 | 8 (6 ring + beamformed + centre) |
| **Connection** | GPIO (I2S) | USB |
| **Power** | 0.3A | 0.6A |
| **Cost** | $60-80 | $50-70 |
| **Setup** | More complex (legacy OS, frozen kernel) | Plug-and-play, current OS |
| **Best For** | Power-critical | Modularity |

→ **Recommended**: Sipeed (more channels, simpler, current OS)

---

## 🌧️ Protection in Tropical Climate

### **Why 3 Layers?**

**Tropical rainforest = extreme conditions:**
- Humidity: 80-95% RH (vs 40-60% normal)
- Rain: Frequent & heavy downpours
- Temperature: 24-32°C year-round
- Moisture: Salt-like residue from air

**Mitigation:**
1. **Plastic Roof**: Roof prevents direct rain
2. **Food Box**: Main enclosure, silicon seals all cracks
3. **Dry Bag**: Powerbank stays dry (battery+water = short circuit)

### **Maintenance Checklist**

| Task | Interval | Why |
|------|----------|-----|
| Check silica gel colour | 1-2 weeks | Replace when pink (saturated) |
| Inspect seals | 1-2 weeks | Water can slowly seep in |
| Test power cycle | 1 month | Ensure boot still works |
| Replace acoustic membrane | 3-6 months | Degradation from sun + humidity |
| Re-apply silicon sealant | 3-6 months | Cracking from UV + temperature |
| Replace Micro SD | 6-12 months | Wear from constant writes |
| Replace rope/rubber | 1 year | UV degradation |

---

## 📊 Storage Capacity

**One 20-minute recording ≈ 307 MB as WAV** (8 channels, 16 kHz, 16-bit); the FLAC file is smaller, depending on content

| SD Card | Recording Hours (WAV upper bound) |
|---------|-----------------|
| 64 GB | at least ~67 hours |
| 128 GB | at least ~133 hours |
| 256 GB | at least ~267 hours |

**Recommended**: Rotate 64 GB cards monthly (backup + failover)

---

## 🔌 Connection Diagram (Text)

```
Powerbank (Dry Bag)
    ↓ USB-A cable
    ↓
[Micro USB] → Raspberry Pi ← [USB Port 1] ← USB WiFi Adapter
                ↓
        [GPIO/USB Port 2] ← Sensor Mic Array
                ↓
        [SD Card Slot] ← Micro SD Card
```

**Key Connections:**
- **ReSpeaker** → GPIO pins (I2S protocol)
- **Sipeed** → USB port (USB Audio Class, MA-USB8 board)
- **WiFi** → USB port (optional, for SSH + uploads)
- **Power** → Micro USB (5V 2A+ recommended)

---

## 📱 How to Access

### **SSH from Phone/Computer**

If WiFi adapter is connected:

```bash
# Find MAARU's IP (ask network admin)
ssh pi@<IP_ADDRESS>

# Health snapshot (if shell shortcuts are installed)
healtheco

# Check recorded files
ls -laR /home/pi/monitoring_data/live_data/

# Download a day of recordings
scp -r pi@<IP>:/home/pi/monitoring_data/live_data/RPiID-<serial>/<YYYY-MM-DD> .
```

### **SD Card Direct** (if WiFi fails)

1. Shut the Pi down (button or `sudo shutdown -h now`)
2. Take out the Micro SD card
3. Read it on a computer that can read the Linux (ext4) partition
4. Copy `/home/pi/monitoring_data/live_data/`

---

## 🚨 Troubleshooting at a Glance

| Problem | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| **No sound recorded** | Sensor not connected | Check GPIO/USB cable, test with `arecord -l` |
| **No files while on WiFi** | Recording pauses while internet is reachable | Expected; use `test_mode: 1` for bench tests |
| **Slow file writes** | SD card aging | Replace with new card |
| **Power shuts off early** | Weak powerbank | Replace or add 2nd powerbank |
| **Water inside enclosure** | Silica gel saturated | Replace silica gel |
| **WiFi won't connect** | Interference or adapter dead | Try relocating, test adapter separately |
| **Files truncated** | Power loss during write | Check battery, reduce recording duration |

**For detailed troubleshooting**: See [troubleshooting.md](troubleshooting.md)

---

## 💡 Pro Tips

1. **Silica Gel is your friend** — Replace every 1-2 weeks (check colour)
2. **Powerbank is your budget** — Plan for 2 powerbanks for 24-hour operation
3. **Test before deployment** — Record 5 min in lab, verify audio quality + file integrity
4. **Backup often** — Download files every week (SD cards can fail)
5. **Keep spares** — Extra silica gel, USB cable, powerbank at site
6. **Log everything** — Check `~/multi-channel-rpi-eco-monitoring/logs/logfile.log` (or `monitor`) for errors
7. **Weather watch** — Heavy rain? Check enclosure afterwards

---

## 📈 Cost Estimate

| Component | Cost | Notes |
|-----------|------|-------|
| **Raspberry Pi 3B** | $45 | Reusable, backbone |
| **Sipeed 6+1 Mic + MA-USB8** | $60 | Better than ReSpeaker for MAARU |
| **Micro SD 64GB** | $15 | Replaceable annually |
| **USB WiFi Adapter** | $20 | Optional but recommended |
| **Powerbank 20K mAh** | $20 | Need 2 for 24hr operation |
| **Enclosure + Protection** | $50 | Food box, plastic roof, dry bag, silica, sealant |
| **Mounting** | $10 | Rope, rubber, zip ties |
| --- | --- | --- |
| **TOTAL (1 unit)** | **~$220** | Minimum viable MAARU |
| **TOTAL (2 powerbanks)** | **~$240** | Recommended for 24-hour operation |

**For 3 units (ecosystem-wide)**:
- 3× MAARU: ~$660 (minimum)
- 6× Powerbanks (2 per unit): +$60
- **Total for ecosystem**: ~$720

---

## 🔗 Documentation Map

| Document | Read If... |
|----------|-----------|
| **[architecture.md](architecture.md)** | Want system overview |
| **[physical-setup.md](physical-setup.md)** | Need component details |
| **[config.md](config.md)** | Need to customize settings |
| **[troubleshooting.md](troubleshooting.md)** | Something broke |
| **[log_guide.md](log_guide.md)** | Need to debug via logs |
| **[MAARU Physical Setup Diagram](maaru-physical-setup.svg)** | Visual learner |

---

## ❓ FAQs

**Q: Can I use Pi 4B instead?**
A: Yes, but more power-hungry (~1.5-2A), shorter runtime. Not recommended unless you have solar panel.

**Q: Can I use bigger powerbank?**
A: Yes! 30K mAh or 40K mAh available. More runtime but heavier & bulkier. Budget ~$30-50 for larger capacities.

**Q: What if I want WiFi always on?**
A: Cuts runtime by ~50%. Use 2 powerbanks. In the field, enable the field WiFi timer (installer menu 9), which puts WiFi to sleep after 20 minutes without a link.

**Q: Can I run MAARU for 24 hours?**
A: Yes, with 2 powerbanks. Swap at 12-hour mark. Or add solar panel (5W minimum) for trickle-charge.

**Q: Will humidity destroy it?**
A: That's why we have silica gel + IP68 membrane + silicon sealant. But nothing lasts forever. Plan for annual maintenance.

**Q: How do I know when Micro SD is dying?**
A: Files become incomplete or corrupted. Check `dmesg` logs. Replace when this starts happening.

---

## 📞 Support

- **Hardware Issues**: Check this doc + [physical-setup.md](physical-setup.md)
- **Software Issues**: Check [config.md](config.md) + [troubleshooting.md](troubleshooting.md)
- **Deployment Strategy**: Ask a biologist or field researcher
- **Cloud Upload Setup**: See [cloud_setup.md](cloud_setup.md)

---

**For**: Multi-Channel RPi Eco-Monitoring Project (MAARU)
**Location**: Lampung, Indonesia (tropical rainforest)
