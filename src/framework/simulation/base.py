# src/framework/simulation/base.py

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import yaml
from abc import ABC, abstractmethod

from ape import networks, chain
from src.framework.data import DataCollector
from src.framework.agents import AgentManager
from src.framework.core import NetworkBuilder, NetworkEvolver
from src.framework.logging import get_logger

logger = get_logger(__name__)

class BaseSimulationConfig:
    """Base configuration class that can be extended for specific simulations"""
    
    def __init__(
        self,
        network_config_path: str,
        agent_config_path: str,
        cli_params: Optional[Dict] = None
    ):
        self.network_config = self._load_config(network_config_path)
        self.agent_config = self._load_config(agent_config_path)
        self._set_default_values()
        if cli_params:
            self._apply_cli_params(cli_params)
        self._validate_config()

    def _load_config(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")
            return {}

    def _set_default_values(self):
        """Set default values for common parameters"""
        defaults = {
            'size': 20,
            'batch_size': 10,
            'iterations': 10,
            'blocks_per_iteration': 100,
            'block_time': 5
        }
        for key, value in defaults.items():
            if key not in self.network_config:
                self.network_config[key] = value

    def _apply_cli_params(self, params: Dict):
        """Apply command line parameters"""
        for key, value in params.items():
            if value is not None:
                self.network_config[key] = value

    @abstractmethod
    def _validate_config(self):
        """Validate configuration specifics"""
        pass

    @property
    def network_size(self) -> int:
        return self.network_config['size']

    @property
    def batch_size(self) -> int:
        return self.network_config['batch_size']

    @property
    def iterations(self) -> int:
        return self.network_config['iterations']

    @property
    def blocks_per_iteration(self) -> int:
        return self.network_config['blocks_per_iteration']

    @property
    def block_time(self) -> int:
        return self.network_config['block_time']

    @abstractmethod
    def get_agent_distribution(self) -> Dict[str, int]:
        """Get the distribution of agent types"""
        pass

class BaseSimulation(ABC):
    """Base simulation class that can be extended for specific simulations"""

    def __init__(
        self,
        config: BaseSimulationConfig,
        contract_configs: Dict[str, Dict[str, Any]],
        fast_mode: bool = True,
        project_root: Optional[Path] = None
    ):
        self.config = config
        self.contract_configs = contract_configs
        self.fast_mode = fast_mode
        self.project_root = project_root or Path(__file__).parents[3]
        self.simulation_start_time = datetime.now()

        # Initialize infrastructure
        self.collector = self._initialize_collector()
        self.agent_manager = self._initialize_agent_manager()
        self.clients = self._initialize_clients()
        self.builder = self._initialize_builder()
        self.evolver = self._initialize_evolver()
        
        # Call post-initialization
      #  self.post_initialize()

        # Tracking
        self.iteration_stats = []

    #def post_initialize(self):
    #    """Hook for post-initialization tasks"""
    #    pass

    def _initialize_collector(self) -> Optional[DataCollector]:
        """Initialize data collector if not in fast mode"""
        if self.fast_mode:
            return None
        return DataCollector(
            self.config.network_config.get('db_path', 'simulation.duckdb')
        )

    @abstractmethod
    def _initialize_clients(self) -> Dict[str, Any]:
        """Initialize protocol clients"""
        pass

    def _initialize_agent_manager(self) -> AgentManager:
        """Initialize agent manager"""
        manager = AgentManager(
            config=self.config.agent_config,
            data_collector=self.collector
        )
        protocols_path = str(self.project_root / "src" / "protocols")
        manager.registry.discover_actions(protocols_path)
        return manager

    def _initialize_builder(self) -> NetworkBuilder:
        """Initialize network builder"""
        return NetworkBuilder(
            clients=self.clients,
            batch_size=self.config.batch_size,
            agent_manager=self.agent_manager,
            collector=self.collector
        )

    def _initialize_evolver(self) -> NetworkEvolver:
        """Initialize network evolver"""
        return NetworkEvolver(
            clients=self.clients,
            agent_manager=self.agent_manager,
            collector=self.collector,
            gas_limits=self.config.network_config.get('gas_limits')
        )

    @abstractmethod
    def get_initial_actions(self) -> List[Dict[str, Any]]:
        """Get list of initial actions to perform when building network"""
        pass

    @abstractmethod
    def get_initial_state(self) -> Dict[str, Any]:
        """Get initial state for agents"""
        pass

    def run(self) -> bool:
        """Execute the simulation"""
        try:
            logger.info("Starting simulation")
            metadata = self._create_simulation_metadata()

            if self.collector:
                self.collector.start_simulation_run(
                    parameters=metadata,
                    description=self.get_simulation_description()
                )

            if not self._build_initial_network():
                return False
            if not self._run_iterations():
                return False

            if self.collector:
                self.collector.end_simulation_run()

            logger.info("Simulation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Simulation failed: {e}", exc_info=True)
            return False

    def _build_initial_network(self) -> bool:
        """Build the initial network"""
        try:
            logger.info(f"Building initial network with {self.config.network_size} agents")
            
            success = self.builder.build_large_network(
                target_size=self.config.network_size,
                profile_distribution=self.config.get_agent_distribution(),
                initial_actions=self.get_initial_actions(),
                initial_state=self.get_initial_state()
            )
            
            if success:
                logger.info("Successfully built initial network")
            else:
                logger.error("Failed to build initial network")
            
            return success
            
        except Exception as e:
            logger.error(f"Error building initial network: {e}")
            return False

    def _run_iterations(self) -> bool:
        """Run simulation iterations"""
        logger.info(f"Running {self.config.iterations} iterations")
        
        for i in range(self.config.iterations):
            if not self.evolver.advance_time(
                self.config.blocks_per_iteration,
                self.config.block_time
            ):
                logger.error(f"Failed to advance time at iteration {i+1}")
                return False
                
            stats = self.evolver.evolve_network(i + 1)
            self.iteration_stats.append(stats)
            self._log_iteration_summary(i + 1, stats)
            
        return True

    @abstractmethod
    def get_simulation_description(self) -> str:
        """Get description of the simulation"""
        pass

    @abstractmethod
    def _create_simulation_metadata(self) -> Dict[str, Any]:
        """Create metadata for the simulation run"""
        pass

    def _log_iteration_summary(self, iteration: int, stats: Dict[str, Any]):
        """Log iteration summary"""
        logger.info(
            f"Iteration {iteration} complete:\n"
            f"  - Total actions: {stats['total_actions']}\n"
            f"  - Successful actions: {stats['successful_actions']}\n"
            f"  - Action breakdown: {stats.get('action_counts', {})}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        total_actions = sum(s.get('total_actions', 0) for s in self.iteration_stats)
        successful_actions = sum(s.get('successful_actions', 0) for s in self.iteration_stats)
        action_counts = {}
        for s in self.iteration_stats:
            for k, v in s.get('action_counts', {}).items():
                action_counts[k] = action_counts.get(k, 0) + v

        return {
            'duration': (datetime.now() - self.simulation_start_time).total_seconds(),
            'network_size': self.config.network_size,
            'iterations_completed': len(self.iteration_stats),
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'current_block': chain.blocks.head.number,
            'action_counts': action_counts
        }