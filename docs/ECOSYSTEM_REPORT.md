# Smart Guitar Ecosystem — Repository Report

## Overview

These five repositories form an integrated ecosystem for a "Smart Guitar" platform that combines hardware manufacturing (luthiers-toolbox), music theory computation, practice coaching, and AI-powered feedback.

---

## Repository Functions

### 1. **sg-spec** — Contract Specifications
| | |
|---|---|
| **URL** | https://github.com/HanzoRazer/sg-spec |
| **Purpose** | Single source of truth for data contracts and interface schemas |
| **Role** | Defines Pydantic models and TypeScript types shared across all systems |

**Key Features:**
- `SmartGuitarSpec` schema (scale length, fret count, string count)
- Hardware capability descriptors (`hardware/profile.json`)
- Cross-repo governance documentation
- Installable via `pip install sg-spec`

---

### 2. **sg-coach** — Practice Coach (Mode 1)
| | |
|---|---|
| **URL** | https://github.com/HanzoRazer/sg-coach |
| **Purpose** | Deterministic, rules-based evaluation of practice sessions |
| **Role** | No LLM required — pure rule evaluation and assignment planning |

**Three-Layer Architecture:**
```
SessionRecord (facts) → CoachEvaluation (interpretation) → PracticeAssignment (intent)
```

**Key Features:**
- CLI: `sg-coach export-bundle`, `sg-coach ota-pack`, `sg-coach ota-verify`
- OTA (Over-The-Air) bundle generation for device updates
- Deterministic rules for consistent evaluation

---

### 3. **sg-ai** — AI Coach (Groove Layer)
| | |
|---|---|
| **URL** | https://github.com/HanzoRazer/sg-ai |
| **Purpose** | Offline AI coach running on-device |
| **Role** | Pure function: `CoachContextPacket` → `CoachingDraft` |

**Key Principles:**
- **Offline-first** — no external API calls
- **Schema in, schema out** — strict JSON validation
- **Privacy-first** — no PII storage
- **Real-time capable** — latency budget enforced in CI

---

### 4. **ai-integrator** — AI Feature Builder
| | |
|---|---|
| **URL** | https://github.com/HanzoRazer/ai-integrator |
| **Purpose** | Unified interface for multiple AI service providers |
| **Role** | Backend abstraction layer for OpenAI, Anthropic, Google AI, etc. |

**Supported Providers:**
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Google AI (Gemini)
- Hugging Face, Cohere
- Custom providers (extensible)

---

### 5. **string_master_v.4.0** — Zone-Tritone System
| | |
|---|---|
| **URL** | https://github.com/HanzoRazer/string_master_v.4.0 |
| **Purpose** | Harmonic theory engine + practice utilities |
| **Role** | Core music theory library powering harmony analysis |

**Three Fundamental Principles:**
1. **Zones define color** — two whole-tone families
2. **Tritones define gravity** — dominant function anchors
3. **Half-steps define motion** — chromatic energy transfer

**CLI Tools:**
- `zt-gravity` — gravity chains, chord analysis
- `zt-band` — practice accompaniment

---

## Dependency Graph

```
                    ┌─────────────────┐
                    │    sg-spec      │◄──────────────────────┐
                    │  (contracts)    │                       │
                    └────────┬────────┘                       │
                             │                                │
              ┌──────────────┼──────────────┐                 │
              │              │              │                 │
              ▼              ▼              ▼                 │
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
     │  sg-coach   │  │   sg-ai     │  │ luthiers-   │───────┘
     │  (Mode 1)   │  │(Groove Lyr) │  │  toolbox    │
     │  rules-eval │  │ offline AI  │  │(mfg + RMOS) │
     └──────┬──────┘  └──────┬──────┘  └─────────────┘
            │                │
            │                │
            ▼                ▼
     ┌─────────────────────────────┐
     │   string_master_v.4.0      │
     │   (Zone-Tritone theory)    │
     │   zt-gravity, zt-band      │
     └─────────────────────────────┘
                    │
                    ▼
            ┌─────────────┐
            │ai-integrator│
            │ (AI backend)│
            └─────────────┘
```

---

## Connection Summary

| From | To | Relationship |
|------|-----|--------------|
| **luthiers-toolbox** | **sg-spec** | Imports contracts via `pip install sg-spec` |
| **sg-coach** | **sg-spec** | Uses `SessionRecord`, `CoachEvaluation` schemas |
| **sg-ai** | **sg-spec** | Consumes `CoachContextPacket`, produces `CoachingDraft` |
| **sg-coach** | **string_master** | Uses Zone-Tritone theory for harmony analysis |
| **sg-ai** | **ai-integrator** | Uses for LLM provider abstraction (cloud fallback) |
| **string_master** | — | Standalone theory library, CLI tools (`zt-gravity`, `zt-band`) |

---

## Data Flow (Practice Session)

```
1. User plays guitar
        │
        ▼
2. Device captures MIDI → SessionRecord (facts)
        │
        ▼
3. sg-coach evaluates → CoachEvaluation (rules-based, Mode 1)
        │
        ▼
4. sg-ai enriches → CoachingDraft (AI feedback, Groove Layer)
        │
        ▼
5. OTA bundle → Device displays feedback
```

---

## Key Architectural Patterns

1. **Schema-First Design** — `sg-spec` is the single source of truth
2. **Offline-First** — `sg-ai` runs entirely on-device
3. **Rules Before AI** — `sg-coach` (deterministic) runs before `sg-ai` (probabilistic)
4. **Provider Agnostic** — `ai-integrator` abstracts LLM providers
5. **Theory Engine** — `string_master` provides harmonic intelligence
