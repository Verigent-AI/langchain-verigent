# langchain-verigent

Trust verification for LangChain agents, chains, and tools using [Verigent](https://verigent.ai) keys.

## The problem

Multi-agent LangChain pipelines delegate tasks to sub-agents and tools with no way to verify trust, capability, or identity. Any agent can claim any role. `langchain-verigent` adds cryptographic trust verification to your pipeline — every agent carries a VG key that declares what it is and what it can do.

## Install

```bash
pip install langchain-verigent
```

## Quick start

### Callback handler (recommended)

Attach to any agent executor to automatically verify VG keys on tool calls:

```python
from langchain_verigent import VerigentCallbackHandler

handler = VerigentCallbackHandler(
    min_tier=2,          # Require at least V2
    threshold=0.5,       # 50% composite trust minimum
    block_untrusted=True # Raise TrustDeniedError on failure
)

# Attach to your agent
result = agent_executor.invoke(
    {"input": "Research this topic"},
    config={"callbacks": [handler]}
)

# Inspect trust decisions
for entry in handler.trust_log:
    print(f"{entry['handle']}: {entry['composite']}% — {'PASS' if entry['passed'] else 'FAIL'}")
```

### Tool wrapper

Wrap any tool to attach a VG key and verify trust before execution:

```python
from langchain_verigent import VerigentToolWrapper
from langchain_community.tools import TavilySearchResults

search = TavilySearchResults()
trusted_search = VerigentToolWrapper(
    search,
    vg_key="VG:SEARCH-01:V3-SENT·Se4Op7An5Ar9Co2Ad6St8Sc3Sa5So1Br2Fo6",
    threshold=0.4
)

result = trusted_search.invoke("latest AI papers")
print(f"Trust: {trusted_search.trust_score.percent}%")
```

### Agent filter (multi-agent)

Filter and rank agents by trust score:

```python
from langchain_verigent import VerigentAgentFilter

agents = [
    {"name": "researcher", "vg_key": "VG:RES-01:V4-ANAL·Se4Op7An5Ar9Co2Ad6St8Sc3Sa5So1Br2Fo6"},
    {"name": "writer",     "vg_key": "VG:WRT-02:V2-SAGE·Se2Op3An4Ar2Co5Ad3St4Sc2Sa8So1Br3Fo2"},
    {"name": "untrusted",  "vg_key": "VG:BAD-99:V0-SENT·Se1Op1An1Ar1Co1Ad1St1Sc1Sa1So1Br1Fo1"},
]

filter = VerigentAgentFilter(min_tier=2, threshold=0.4)

# Only agents meeting threshold
trusted = filter.filter(agents)  # [researcher, writer]

# Ranked by composite score
ranked = filter.rank(agents)  # [researcher, writer, untrusted]
```

## VG Key format

```
VG:{NAME}-{SUFFIX}:{TIER}-{PRIMARY}·{12×class_code+digit}
```

- **Tier**: V0 (unverified) through V6 (sovereign-grade)
- **Primary**: 4-letter class code (e.g. ARCH, SENT, ANAL)
- **Scores**: 12 class dimensions, each 0-9

Classes: Sentinel, Operative, Analyst, Architect, Conduit, Adaptor, Steward, Scout, Sage, Sovereign, Broker, Forge.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_tier` | 0 | Minimum tier to pass (0-6) |
| `threshold` | 0.5 | Minimum composite score (0.0-1.0) |
| `required_classes` | None | Class codes to weight in scoring |
| `block_untrusted` | False | Raise error on trust failure |

## Links

- [Verigent](https://verigent.ai) — Agent trust verification
- [GitHub](https://github.com/verigentai/langchain-verigent)
- [LangChain](https://python.langchain.com)

## License

MIT
