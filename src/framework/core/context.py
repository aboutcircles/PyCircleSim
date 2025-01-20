from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from src.framework.agents import AgentManager, BaseAgent
import time
from src.framework.logging import get_logger
import logging

logger = get_logger(__name__,logging.DEBUG)

@dataclass
class CacheEntry:
    """Represents a cached value with timestamp"""
    value: Any
    timestamp: float
    
class SimulationContext:
    """Encapsulates the context needed for simulation actions with caching"""
    def __init__(
        self,
        agent: BaseAgent,
        agent_manager: AgentManager,
        clients: Dict[str, Any],
        chain: Any,
        network_state: Dict[str, Any],
        simulation: 'BaseSimulation', 
        iteration: int,
        iteration_cache: Dict[str, Any]
    ):
        self.agent = agent
        self.agent_manager = agent_manager
        self.clients = clients
        self.chain = chain
        self.network_state = network_state
        self.simulation = simulation
        self.iteration = iteration
        self._cache = iteration_cache

    def get_client(self, contract_id: str) -> Any:
        """Get client for specific contract"""
        return self.clients.get(contract_id)

    def get_contract_state(self, contract_id: str, var_name: str, default: Any = None) -> Any:
        """Helper to get contract state"""
        return self.network_state.get('contract_states', {}).get(contract_id, {}).get('state', {}).get(var_name, default)

    def get_running_state(self, key: str, default: Any = None) -> Any:
        """Helper to get running state"""
        return self.network_state.get('running_state', {}).get(key, default)

    def update_running_state(self, updates: Dict[str, Any]):
        """Helper to update running state"""
        if 'running_state' not in self.network_state:
            self.network_state['running_state'] = {}
        self.network_state['running_state'].update(updates)


    def get_cache_key(self, base_key: str, identifiers: Dict[str, Any] = None) -> str:
        """Generate consistent cache keys"""
        if not identifiers:
            return base_key
            
        # For block-dependent data, use block ranges instead of exact blocks
        if 'block' in identifiers:
            # Cache for 10 blocks
            block_range = identifiers['block'] // 10
            return f"{base_key}_block_{block_range}"
            
        # For agent data, use short identifier
        if 'agent_id' in identifiers:
            short_id = identifiers['agent_id'][:8]
            return f"{base_key}_agent_{short_id}"
            
        return base_key

    def get_cached(self, key: str) -> Optional[Any]:
        """Get a cached value if still valid"""
        entry = self._cache.get(key)
        if not entry:
            return None
        
        if time.time() - entry.timestamp > self.cache_ttl:
            del self._cache[key]
            return None
            
        return entry.value
    

    def get_or_cache(self, key: str, generator_func):
        iteration_key = f"{key}_iter_{self.iteration}"
        if iteration_key in self._cache.keys():
            logger.debug(f"Cache hit for {key}")
            return self._cache[iteration_key]
                
        logger.debug(f"Cache miss for {key}")
        result = generator_func()
        self._cache[iteration_key] = result
        return result
        
    # Helper methods for common cached operations
    def get_filtered_addresses(self, predicate_func, cache_key: Optional[str] = None) -> List[str]:
        """Get filtered addresses with iteration-based caching"""
        if not cache_key:
            return [addr for addr in self.agent_manager.address_to_agent.keys() 
                   if predicate_func(addr)]
                   
        iteration_key = f"{cache_key}_iter_{self.iteration}"
        
        if iteration_key in self._cache:
            logger.debug(f"Cache hit for {iteration_key}")
            return self._cache[iteration_key]
            
        logger.debug(f"Cache miss for {cache_key}")
        result = [addr for addr in self.agent_manager.address_to_agent.keys() 
                 if predicate_func(addr)]
        self._cache[iteration_key] = result
        return result