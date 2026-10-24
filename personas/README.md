# TIDOS Virtual AI Engineering Personas (`personas/`)

The `personas/` directory defines the Virtual AI Engineering Company persona specifications for TIDOS (v3.0).

---

## Directory Components

- [roles.md](/personas/roles.md): Master Virtual AI Engineering Organization matrix defining 30+ specialist roles across 7 divisions.
- [registry.md](/personas/registry.md): Persona Registry & Auto-Routing Table (intent signals, stack/project weights, threshold and tie rules).
- [tidostrade.md](/personas/tidostrade.md): TIDOSTRADE Binary Options Trading Intelligence persona (trigger: `TIDOSTRADE`).
- [tidosuiux.md](/personas/tidosuiux.md): TIDOSUIUX Universal UI/UX, Product Design & Interface Engineering persona (trigger: `TIDOSUIUX`).
- [tidosgptid.md](/personas/tidosgptid.md): GPTID ChatGPT Interface & Reasoning Relay persona — local browser bridge to the user's ChatGPT Free session, no API key (trigger: `GPTID`, engine: `engines/gptid_relay_engine.md`).
- [tidosmobile.md](/personas/tidosmobile.md): TIDOSMOBILE Mobile & Flutter Systems Architecture Specialist persona (trigger: `TIDOSMOBILE`, generated via Persona Factory v2.0).

---

## Protection Rule

```
INVARIANT: All files in personas/ are PROTECTED system files and read-only.
```
