"""LangChain integration — callback handler, tool wrapper, agent filter."""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import BaseTool

from .parser import VGKey, extract_vg_key, parse_vg_key
from .trust import TrustScore, evaluate_trust

logger = logging.getLogger("langchain_verigent")


class VerigentCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that intercepts tool calls and verifies VG keys.

    Attach to any agent executor or chain to log trust decisions on tool
    invocations and optionally block untrusted calls.

    Usage:
        from langchain_verigent import VerigentCallbackHandler

        handler = VerigentCallbackHandler(min_tier=2, threshold=0.5)
        agent_executor.invoke({"input": "..."}, config={"callbacks": [handler]})
    """

    def __init__(
        self,
        *,
        min_tier: int = 0,
        threshold: float = 0.5,
        required_classes: Optional[list[str]] = None,
        block_untrusted: bool = False,
    ):
        self.min_tier = min_tier
        self.threshold = threshold
        self.required_classes = required_classes
        self.block_untrusted = block_untrusted
        self.trust_log: list[dict[str, Any]] = []

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Check VG key in tool metadata before execution."""
        metadata = kwargs.get("metadata") or {}
        key = extract_vg_key(metadata=metadata)

        if key:
            score = evaluate_trust(
                key,
                required_classes=self.required_classes,
                min_tier=self.min_tier,
                threshold=self.threshold,
            )
            entry = {
                "tool": serialized.get("name", "unknown"),
                "handle": key.handle,
                "tier": key.tier_label,
                "composite": score.percent,
                "passed": score.meets_threshold,
            }
            self.trust_log.append(entry)

            if score.meets_threshold:
                logger.info("TRUST PASS: %s (%s, %d%%)", key.handle, key.tier_label, score.percent)
            else:
                logger.warning(
                    "TRUST FAIL: %s (%s, %d%%)", key.handle, key.tier_label, score.percent
                )
                if self.block_untrusted:
                    raise TrustDeniedError(
                        f"Agent {key.handle} ({key.tier_label}) below trust threshold "
                        f"({score.percent}% < {int(self.threshold * 100)}%)"
                    )
        else:
            logger.debug("No VG key found for tool: %s", serialized.get("name", "unknown"))


class TrustDeniedError(Exception):
    """Raised when an agent fails trust verification and blocking is enabled."""

    pass


class VerigentToolWrapper:
    """Wraps a LangChain tool to add VG key verification to its responses.

    The wrapper checks the tool's metadata or output for a VG key and
    annotates the result with trust information.

    Usage:
        from langchain_verigent import VerigentToolWrapper
        from langchain_community.tools import TavilySearchResults

        search = TavilySearchResults()
        trusted_search = VerigentToolWrapper(search, vg_key="VG:SEARCH-01:V3-SENT·...")
    """

    def __init__(
        self,
        tool: BaseTool,
        *,
        vg_key: Optional[str] = None,
        min_tier: int = 0,
        threshold: float = 0.5,
    ):
        self.tool = tool
        self.min_tier = min_tier
        self.threshold = threshold
        self._key: Optional[VGKey] = parse_vg_key(vg_key) if vg_key else None
        self._last_score: Optional[TrustScore] = None

    @property
    def name(self) -> str:
        return self.tool.name

    @property
    def description(self) -> str:
        return self.tool.description

    @property
    def trust_score(self) -> Optional[TrustScore]:
        return self._last_score

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        """Run the tool with trust verification."""
        if self._key:
            self._last_score = evaluate_trust(
                self._key, min_tier=self.min_tier, threshold=self.threshold
            )
            if not self._last_score.meets_threshold:
                logger.warning(
                    "Tool %s: trust below threshold (%d%%)",
                    self.tool.name,
                    self._last_score.percent,
                )

        return self.tool.invoke(input, **kwargs)


class VerigentAgentFilter:
    """Filters and ranks agents by trust score for multi-agent setups.

    Usage:
        from langchain_verigent import VerigentAgentFilter

        agents = [
            {"name": "researcher", "vg_key": "VG:RES-01:V4-ANAL·..."},
            {"name": "writer", "vg_key": "VG:WRT-02:V2-SAGE·..."},
        ]
        filter = VerigentAgentFilter(min_tier=2, threshold=0.4)
        trusted = filter.filter(agents)
        ranked = filter.rank(agents)
    """

    def __init__(
        self,
        *,
        min_tier: int = 0,
        threshold: float = 0.5,
        required_classes: Optional[list[str]] = None,
    ):
        self.min_tier = min_tier
        self.threshold = threshold
        self.required_classes = required_classes

    def evaluate(self, agent_config: dict[str, Any]) -> Optional[TrustScore]:
        """Evaluate a single agent config. Expects 'vg_key' field."""
        raw = agent_config.get("vg_key")
        if not raw:
            return None
        key = parse_vg_key(raw)
        if not key:
            return None
        return evaluate_trust(
            key,
            required_classes=self.required_classes,
            min_tier=self.min_tier,
            threshold=self.threshold,
        )

    def filter(self, agents: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only agents that meet the trust threshold."""
        result = []
        for agent in agents:
            score = self.evaluate(agent)
            if score and score.meets_threshold:
                result.append(agent)
                logger.info("AGENT PASS: %s (%d%%)", agent.get("name", "?"), score.percent)
            elif score:
                logger.warning("AGENT FAIL: %s (%d%%)", agent.get("name", "?"), score.percent)
            else:
                logger.debug("AGENT SKIP (no key): %s", agent.get("name", "?"))
        return result

    def rank(self, agents: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank agents by trust score, highest first. Unkeyed agents go last."""
        scored: list[tuple[float, dict[str, Any]]] = []
        for agent in agents:
            trust = self.evaluate(agent)
            scored.append((trust.composite if trust else -1.0, agent))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in scored]
