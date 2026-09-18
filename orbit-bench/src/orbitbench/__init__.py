"""OrbitBench AI - pluggable cache backends with honest benchmarks.

Every backend in orbit around one protocol; every number on record.
100% local on the Azure Cosmos DB emulator.
"""

from orbitbench.backends import AVAILABLE_BACKENDS, create_backend
from orbitbench.config import Settings, get_settings
from orbitbench.metrics import Stats, percentile
from orbitbench.workloads import SCENARIOS, Scenario

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "get_settings",
    "Stats",
    "percentile",
    "Scenario",
    "SCENARIOS",
    "AVAILABLE_BACKENDS",
    "create_backend",
    "__version__",
]
