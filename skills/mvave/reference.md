# mvave reference (MK-300 profile)

## Commands

```
usage: mvave [-h] [--device DEVICE] [--port PORT]
             {show,load,param,model,enable,volume,bpm,pan,presets,read,save,copy,rename,chain,reamp,global,global-set,models,params,bank,resolve,listen,doctor}
             ...

M-VAVE pedals over USB without the M-EFCS editor

positional arguments:
  {show,load,param,model,enable,volume,bpm,pan,presets,read,save,copy,rename,chain,reamp,global,global-set,models,params,bank,resolve,listen,doctor}
    show                the edit buffer: name, chain, models, knobs
    load                load preset N (1..160) and show it
    param               set a knob of a block: param AMP Gain 60 (knob by name
                        or 0-based index)
    model               put a model in a block: model AMP 53 | model DLY
                        'Analog' (knobs reset to defaults)
    enable              block on/off: enable DLY on
    volume              preset volume 0-100
    bpm                 preset tempo
    pan                 preset pan: 0 = C, +17 = R17, negative = L
    presets             the 160 stored presets (* = current)
    read                a stored preset straight from flash, without loading
                        it
    save                store the edit buffer into slot N as NAME (refuses a
                        named slot without --overwrite)
    copy                copy a stored preset to another slot: copy 3 150
                        [NAME]
    rename              rename the edit buffer (save afterwards)
    chain               signal order of the blocks: chain WAH FX GATE DS AMP
                        CAB EQ MOD REV DLY VOL (byte-wise writes, read back)
    reamp               play DI.wav through the pedal over USB audio (USB
                        Audio = RESAMPLE) and record OUT.wav
    global              read the global block (space 2)
    global-set          write ONE known global field: global-set rch Dry
    models              catalog: models of a block
    params              catalog: knobs and defaults of a model
    bank                list a bank file (the editor's
                        <device>_am4_preset.bin)
    resolve             which model is based on a real-world unit: resolve AMP
                        'Marshall JCM800'
    listen              print the preset index whenever it changes
                        (footswitches)
    doctor              check the globals for anything that would leave the
                        pedal silent for normal playing (exit 1 if dirty)

options:
  -h, --help            show this help message and exit
  --device DEVICE       pedal profile: mk300 (default mk300)
  --port PORT           MIDI port name (default: the profile's port, e.g. 'USB
                        Composite Device')
```

## Preset struct (edit buffer, space 1, 448 bytes)

| offset | field |
|---|---|
| 0x00 | name, 20 bytes |
| 0x18 | volume u16 |
| 0x1A | bpm u16 |
| 0x1C | pan i16 (0 = C) |
| 0x20 | chain order, 11 block ids |
| 0x2B + block | on/off |
| 0x36 + block | model index |
| 0x42 + 24*block + 2*knob | knob i16 |

Blocks: 0 WAH, 1 FX, 2 GATE, 3 DS, 4 AMP, 5 CAB, 6 EQ, 7 MOD, 8 DLY, 9 REV, 10 VOL

## Global block (space 2, 86 bytes)

| offset | field | values |
|---|---|---|
| 0x00 | current preset index (0-based) | |
| 0x38 | A/B Convert | 0 OFF, 1 ON |
| 0x3C | RCH (right channel output) | 0 Nor, 1 Dry, 2 NoCAB |
| 0x3D | USB Audio | 0 ON, 1 OFF, 2 RESAMPLE, 3 DRY |

Only these were seen written by the editor; write nothing else in space 2.

## Model catalog

### WAH

- 0 X-Wah: Value, Gain, Level
- 1 Funk-Wah: Value, Gain, Level
- 2 Slide-Wah: Value, Gain, Level
- 3 Cry-Wah: Value, Gain, Level
- 4 Wah-Wah: Speed, Q, Mix, Width, Level, Sync
- 5 Sense-Wah: Sense, Attack, Q, fPeak, Mix, Width, Level

### FX

- 0 Wah-Wah: Speed, Q, Mix, Width, Level, Sync
- 1 Lofi: Bit, Level, filter
- 2 Sense-Wah: Sense, Attack, Q, fPeak, Mix, Width, Level
- 3 Boost: Gain, Level
- 4 A Boost: Gain, Bass, Mid, Treble, Level
- 5 E Boost: Gain, Bass, Mid, Treble, Level
- 6 B Boost: Gain, Bass, Mid, Treble, Level
- 7 Boost ED: Gain, Grit, Level
- 8 Compress: Sustain, Attack, Level, Blend
- 9 Compress Pro: Ratio, Gain, Knee, Thd, Attack, Level, Blend
- 10 F Compress: Ratio, Gain, Knee, Thd, Attack, Tone, Level, Blend
- 11 Pitch: High Pitch, Low Pitch, High Level, Low Level, Dry Level
- 12 Octave: High Level, Low Level, Dry Level
- 13 Ring: Freq, Mix
- 14 Pitch shifter: Semi
- 15 Whammy: Mode, Bend, Mix

### GATE

- 0 AI Gate: Gate, Bias
- 1 Soft Gate: Thd
- 2 Hard Gate: Thd
- 3 Pro Gate: Att, Rel, Thd, Kw, Ratio
- 4 Compress: Sustain, Attack, Level, Blend
- 5 Compress Pro: Ratio, Gain, Knee, Thd, Attack, Level, Blend
- 6 F Compress: Ratio, Gain, Knee, Thd, Attack, Tone, Level, Blend
- 7 AI Ms Gate: Gate, Bias

### DS

- 0 1BLUES_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 1 2TS8: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 2 3DS1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 3 4DS2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 4 5M-VAVE_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 5 6M-VAVE_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 6 7M-VAVE_TS1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 7 8M-VAVE_TS2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 8 9SUPA_1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 9 10SUPA_2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 10 11RAT: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 11 12RAT_BT: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 12 13JHS_1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 13 14JHS_2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 14 15MT_1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 15 16MT_2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 16 17TDS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 17 18XC_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 18 19QC_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 19 20HIGAIN: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 20 21M-BOOSTER: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 21 22TS-9: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 22 23BIG-DR: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 23 24CL_BOOST: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 24 25BD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 25 26M9OS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 26 27M2000: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 27 28DS800: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 28 29DS900: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 29 30MAR-DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 30 31BOG_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 31 32SONDO: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 32 33MID-BOST: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 33 34RED_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 34 35MODEN_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 35 36SuperOD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 36 37BLUES_DR: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 37 38Black-BOX: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 38 39BIG-MUFF: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 39 40PLX: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright

### AMP

- 0 1J120_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 1 2J900_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 2 3J900_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 3 4J900_HV: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 4 5M_BLUES: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 5 6HORIZON: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 6 7M-VAVE_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 7 8ROOM40: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 8 9FD1_BR: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 9 10JOY_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 10 11M-VAVE_TS3: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 11 12MT100 LEAD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 12 13RAT_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 13 14RAT_CR: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 14 15RAT_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 15 16MES_RED: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 16 17FD_CH1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 17 18FD_CH1_HOT: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 18 19MT80 CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 19 20M_SUPER OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 20 21J800_CL_196: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 21 22J800_CL_AMP: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 22 23J800_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 23 24J800_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 24 25JOHNS_CH1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 25 26DARK_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 26 27DARK_OD2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 27 28DARK_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 28 29VXO_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 29 30VXO_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 30 31VXO_OD2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 31 32VXO_OD3: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 32 33OR_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 33 34OR_CRUNCH: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 34 35HIGIAN: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 35 36HIGIAN_RED: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 36 37COOL_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 37 38JVMcrunch: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 38 39JV410_BOOST: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 39 40AXE: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 40 41MES_CH1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 41 42M-VAVE_DS3: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 42 43M-VAVE_DS4: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 43 44M-VAVE LEAD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 44 45LANY_CH1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 45 46LANY_CH1_BR: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 46 47LANY_CH2_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 47 48LANY_CH3_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 48 49ROLANS_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 49 50ROLANS_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 50 51ROLANS_TDS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 51 52BOOSS_METEL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 52 53J900_CH1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 53 54J900_CH2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 54 55JVM_OD_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 55 56JVM_DS_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 56 57RADAL_CL_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 57 58RADAL_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 58 59RADAL_TDS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 59 60RADAL_HDS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 60 61DUMBLE_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 61 62JAZZ_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 62 63M-VAVE_TS1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 63 64M-VAVE_TS2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 64 65EHV5150_CH1: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 65 66EHV5150_CH2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 66 67EHV5150_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 67 68EHV5150_MT: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 68 69XC_CL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 69 70XC_OD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 70 71XC_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 71 72XC_HV: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 72 73J2000_CL_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 73 74J2000_CR_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 74 75J2000_TR_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 75 76J2000_DS_FG: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 76 77J900_CL_57: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 77 78J900_DS_57: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 78 79MAR_METEL: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 79 80MAR_HV: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 80 81WS_JZCL_57: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 81 82OR_CL_ECM: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 82 83OR_CRUNCH: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 83 84OR_SWEET: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 84 85BOG_LEAD: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 85 86BOG_LEAD2: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 86 87BOG_LEAD3: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 87 88BOG_SOLO: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 88 89MATTER_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 89 90UK_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 90 91JHS_DS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 91 92JHS_TDS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 92 93M-VAVE_HOT: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 93 94M-VAVE_RED: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 94 95M-VAVE_MT: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 95 96M-VAVE_BST: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 96 97MES_CH2_57: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 97 98MES_CH2_AMP: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 98 99MES_CH3_57: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 99 100MES_CH3_AM: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 100 101AgDb750_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 101 102ApSVT_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 102 103DgM900_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 103 104FenRum_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 104 105GkF550_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 105 106HkeHd50_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 106 107MarkLm_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 107 108OrgAd_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 108 109PjBuddy_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 109 110RolDb_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 110 111Mb400C1_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 111 112Mb400C2_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 112 113DgXu_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 113 114ApSp_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 114 115Mar50_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 115 116Mark500_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 116 117PjbCub_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 117 118Tc21Vt_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 118 119WatMod_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright
- 119 120GKL800_BS: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright

### CAB

- 0 1AC-SeVin: Level, Low Cut, High Cut
- 1 2JVM_1960_57: Level, Low Cut, High Cut
- 2 3JVM_G12_ECM: Level, Low Cut, High Cut
- 3 4DELUXE REV: Level, Low Cut, High Cut
- 4 5BOG_57: Level, Low Cut, High Cut
- 5 6FD120_7B: Level, Low Cut, High Cut
- 6 7HESS_212DM: Level, Low Cut, High Cut
- 7 8HESS_212VTY: Level, Low Cut, High Cut
- 8 9HIW412SWF: Level, Low Cut, High Cut
- 9 10MAR1960_412: Level, Low Cut, High Cut
- 10 11MESA_412_57: Level, Low Cut, High Cut
- 11 12MESA_412_EC: Level, Low Cut, High Cut
- 12 13WANGS112_EC: Level, Low Cut, High Cut
- 13 14WANGS212_EC: Level, Low Cut, High Cut
- 14 15V30_MC834: Level, Low Cut, High Cut
- 15 16V30_MD421: Level, Low Cut, High Cut
- 16 17VOX_AC30: Level, Low Cut, High Cut
- 17 18FD_TW1971: Level, Low Cut, High Cut
- 18 19FD_TW1980: Level, Low Cut, High Cut
- 19 20FD_TW1988: Level, Low Cut, High Cut
- 20 21FD_TW2000: Level, Low Cut, High Cut
- 21 22M160_Center: Level, Low Cut, High Cut
- 22 23MD421_Cente: Level, Low Cut, High Cut
- 23 24Chug_L: Level, Low Cut, High Cut
- 24 25Chug_R: Level, Low Cut, High Cut
- 25 26EV_MIX_B: Level, Low Cut, High Cut
- 26 27G12-EVH: Level, Low Cut, High Cut
- 27 28G12-EVH_CT: Level, Low Cut, High Cut
- 28 29G12-EVH_i5: Level, Low Cut, High Cut
- 29 30G12-EVH_m16: Level, Low Cut, High Cut
- 30 31Marshall_Bo: Level, Low Cut, High Cut
- 31 32BGN412V30: Level, Low Cut, High Cut
- 32 33MESA_LS: Level, Low Cut, High Cut
- 33 34MESA_CS: Level, Low Cut, High Cut
- 34 35MESA_HS: Level, Low Cut, High Cut
- 35 36Recto_112: Level, Low Cut, High Cut
- 36 37FRMAN112: Level, Low Cut, High Cut
- 37 38OR_112: Level, Low Cut, High Cut
- 38 39HIFI_OK: Level, Low Cut, High Cut
- 39 40Ranll_412: Level, Low Cut, High Cut
- 40 41OR_V30_212: Level, Low Cut, High Cut
- 41 42OR_G75_212: Level, Low Cut, High Cut
- 42 43RE_SUPER_41: Level, Low Cut, High Cut
- 43 44EGNL01_412: Level, Low Cut, High Cut
- 44 45EGNL02_412: Level, Low Cut, High Cut
- 45 46EGNL03_412: Level, Low Cut, High Cut
- 46 47MeOSick-II: Level, Low Cut, High Cut
- 47 48MeOSick-III: Level, Low Cut, High Cut
- 48 49MesaOSick-I: Level, Low Cut, High Cut
- 49 50SoldHor: Level, Low Cut, High Cut
- 50 51SoldSC412: Level, Low Cut, High Cut
- 51 52AC-SeTV20: Level, Low Cut, High Cut
- 52 53Pey5150: Level, Low Cut, High Cut
- 53 54MRSH03: Level, Low Cut, High Cut
- 54 55VA5153: Level, Low Cut, High Cut
- 55 56AC-EmG212: Level, Low Cut, High Cut
- 56 57AC-Se210: Level, Low Cut, High Cut
- 57 58CeleAt: Level, Low Cut, High Cut
- 58 59AC-SeGol: Level, Low Cut, High Cut
- 59 60AC-CateEx: Level, Low Cut, High Cut
- 60 61AC-CateFw: Level, Low Cut, High Cut
- 61 62DieV30: Level, Low Cut, High Cut
- 62 63EAGLProV30s: Level, Low Cut, High Cut
- 63 64Sperimental: Level, Low Cut, High Cut
- 64 65Peavey115: Level, Low Cut, High Cut
- 65 66Peavey112: Level, Low Cut, High Cut
- 66 67VxAc15: Level, Low Cut, High Cut
- 67 68FimanVt: Level, Low Cut, High Cut
- 68 69FenDeluX: Level, Low Cut, High Cut
- 69 70FenProJ: Level, Low Cut, High Cut
- 70 71Alton212: Level, Low Cut, High Cut
- 71 72OgP412: Level, Low Cut, High Cut
- 72 73OgV30: Level, Low Cut, High Cut
- 73 74HaBtonV: Level, Low Cut, High Cut
- 74 75MarMfour: Level, Low Cut, High Cut
- 75 76Elctrovoice: Level, Low Cut, High Cut
- 76 77J120Rolnd: Level, Low Cut, High Cut
- 77 78MessOS: Level, Low Cut, High Cut
- 78 79Mar60AV: Level, Low Cut, High Cut
- 79 80WS212_57: Level, Low Cut, High Cut
- 80 81Agula410: Level, Low Cut, High Cut
- 81 82AmpgSVT410: Level, Low Cut, High Cut
- 82 83AmpgSVT810: Level, Low Cut, High Cut
- 83 84AshB115: Level, Low Cut, High Cut
- 84 85Bareface110: Level, Low Cut, High Cut
- 85 86Bstert115: Level, Low Cut, High Cut
- 86 87DavEendD410: Level, Low Cut, High Cut
- 87 88DgD210C: Level, Low Cut, High Cut
- 88 89DgDG212N: Level, Low Cut, High Cut
- 89 90FdBman410: Level, Low Cut, High Cut
- 90 91FdBmanSf210: Level, Low Cut, High Cut
- 91 92GKRB410A: Level, Low Cut, High Cut
- 92 93GKRB410B: Level, Low Cut, High Cut
- 93 94Hark410: Level, Low Cut, High Cut
- 94 95MbSubway210: Level, Low Cut, High Cut
- 95 96OgOBC212: Level, Low Cut, High Cut
- 96 97Pey115: Level, Low Cut, High Cut
- 97 98RanRB100: Level, Low Cut, High Cut
- 98 99SR115: Level, Low Cut, High Cut
- 99 100Tace412: Level, Low Cut, High Cut

### EQ

- 0 Guitar EQ 6: 100Hz, 200Hz, 400Hz, 800Hz, 1.6kHz, 3.2kHz
- 1 Bass EQ 7: 50Hz, 120Hz, 400Hz, 500Hz, 800Hz, 4.5kHz, 10k
- 2 Normal EQ 10: 31.25Hz, 62.5Hz, 125Hz, 250Hz, 500Hz, 1kHz, 2kHz, 4kHz, 8kHz, 16kHz

### MOD

- 0 Chorus: Speed, Depth, Mix, Sync
- 1 Tri Chorus: Speed, Depth, Mix, Sync
- 2 Flanger: Speed, Depth, Fb, Mix, Sync
- 3 Tri Flanger: Speed, Depth, Fb, Mix, Sync
- 4 Tremolo: Speed, Depth, Level, Sync
- 5 Tri Tremolo: Speed, Depth, Level, Sync
- 6 Opto Tremolo: Speed, Depth, Level, Sync
- 7 Phaser: Speed, MidCut, Reso, Fb, Sync
- 8 Vibrato: Speed, Depth, Sync
- 9 Tri Vibrato: Speed, Depth, Sync
- 10 Opto Vibrato: Speed, Depth, Sync
- 11 Univibe: Speed, Depth, Mix, Sync
- 12 Tri Univibe: Speed, Depth, Mix, Sync
- 13 Autofilter: Speed, Min, Max, Mix, Fb, Sync
- 14 Phaser Stereo: Speed, Stage, Regen, Mix, Lfo, Sync
- 15 Flanger Stereo: Speed, Depth, Regen, Mix, Jet, Lfo, Sync
- 16 Vibe Stereo: Speed, Stage, Regen, Mix, Lfo, Sync
- 17 Chorus Stereo: Speed, Depth, Mode, Mix, Sync
- 18 Tremolo Stereo: Speed, Depth, Level, Mode, Sync
- 19 Vibrato Stereo: Speed, Depth, Bits, Mix, Sync

### DLY

- 0 Clean: Time, Fb, Mix, Sync
- 1 Modern: Time, Fb, Mix, Phaser, Mod, Sync
- 2 Echo: Time, Fb, Mix, Sync
- 3 Analog: Time, Fb, Mix, Sync
- 4 Duck: Time, Fb, Mix, Release, Speed, Depth, Sync
- 5 Dtype: Time, Fb, Mix, Grit, Speed, Depth, Sync
- 6 Tremolo: Time, Fb, Mix, Pattern, Speed, Depth, Sync
- 7 Filter: Time, Fb, Mix, Filter, Speed, Depth, Sync
- 8 Dual: Time, Fb, Mix, T-Mode, Speed, Depth, Sync
- 9 Lofi: Time, Fb, Mix, Grit, Speed, Depth, Sync
- 10 Pattern: Time, Fb, Mix, Pattern, Speed, Depth, Sync
- 11 Ice: Time, Fb, Mix, Pitch, Mod, Sync
- 12 Reverse: Time, Fb, Mix, Phaser, Mod, Sync
- 13 PingPong Stereo: Time, Fb, Mix, Sync
- 14 Clean Stereo: Time, Fb, Mix, Sync
- 15 Modern Stereo: Time, Fb, Mix, Sync
- 16 Echo Stereo: Time, Fb, Mix, Sync
- 17 Analog Stereo: Time, Fb, Mix, Release, Speed, Depth, Sync
- 18 Duck Stereo: Time, Fb, Mix, Grit, Speed, Depth, Sync
- 19 Dtype Stereo: Time, Fb, Mix, Pattern, Speed, Depth, Sync
- 20 Tremolo Stereo: Time, Fb, Mix, Filter, Speed, Depth, Sync
- 21 Filter Stereo: Time, Fb, Mix, T-Mode, Speed, Depth, Sync
- 22 Dual Stereo: Time, Fb, Mix, Grit, Speed, Depth, Sync
- 23 Lofi Stereo: Time, Fb, Mix, Pattern, Speed, Depth, Sync
- 24 Pattern Stereo: Time, Fb, Mix, Pitch, Mod, Sync
- 25 Ice Stereo: Time, Fb, Mix, Phaser, Mod, Sync
- 26 Reverse Stereo: Time, Fb, Mix, Phaser, Mod, Sync

### REV

- 0 Room: Decay, Mix, High Pass, Low Pass, Mod Depth
- 1 Hall: Decay, Mix, High Pass, Low Pass, Mod Depth
- 2 Plate: Decay, Mix, High Pass, Low Pass, Mod Depth
- 3 Spring: Decay, Mix, High Pass, Low Pass, Combs
- 4 Shimmer: Decay, Mix, Tone, Pitch, Amount
- 5 Bloom: Decay, Mix, Tone, Lend, Length
- 6 Cloud: Decay, Mix, High Pass, Low Pass, Diff
- 7 Lofi: Decay, Mix, Sample Rate, Noise Level, Mod Depth
- 8 Swell: Decay, Mix, Tone, Lend, Rise Time
- 9 Room stereo: Decay, Mix, High Pass, Low Pass, Mod Depth
- 10 Hall stereo: Decay, Mix, High Pass, Low Pass, Mod Depth
- 11 Plate stereo: Decay, Mix, High Pass, Low Pass, Mod Depth
- 12 Spring stereo: Decay, Mix, High Pass, Low Pass, Combs
- 13 Shimmer stereo: Decay, Mix, Tone, Pitch, Amount
- 14 Bloom stereo: Decay, Mix, Tone, Lend, Length
- 15 Cloud stereo: Decay, Mix, High Pass, Low Pass, Diff
- 16 Lofi stereo: Decay, Mix, Sample Rate, Noise Level, Mod Depth
- 17 Swell stereo: Decay, Mix, Tone, Lend, Rise Time

### VOL

- 0 VOL: VOL
