"""langchain-verigent — Trust verification for LangChain agents and chains."""

from .middleware import (
    TrustDeniedError,
    VerigentAgentFilter,
    VerigentCallbackHandler,
    VerigentToolWrapper,
)
from .parser import CLASS_CODES, VGKey, extract_vg_key, parse_vg_key
from .trust import TrustScore, evaluate_trust

__all__ = [
    "CLASS_CODES",
    "TrustDeniedError",
    "TrustScore",
    "VGKey",
    "VerigentAgentFilter",
    "VerigentCallbackHandler",
    "VerigentToolWrapper",
    "evaluate_trust",
    "extract_vg_key",
    "parse_vg_key",
]

__version__ = "0.1.0"
