"""
Shared singleton memory stores.

All modules — API routes, agents, cognitive plugins — import from here
so they operate on the same in-memory state within a single process.
"""
from .associative import AssociativeMemory
from .temporal import TemporalKnowledgeGraph
from .experiential import ExperientialRepository
from .working import WorkingContextMemory

associative_store  = AssociativeMemory()
temporal_store     = TemporalKnowledgeGraph()
experiential_store = ExperientialRepository()
working_store      = WorkingContextMemory()
