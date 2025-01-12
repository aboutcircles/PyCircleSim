from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import random
import secrets
from eth_account import Account
from ape import networks
from .profile import AgentProfile
from src.framework.data import BaseDataCollector
from src.framework.logging import get_logger
from dataclasses import dataclass

logger = get_logger(__name__)

@dataclass
class BalanceUpdate:
    contract: str
    account: str 
    balance: int
    timestamp: datetime
    block: int

class BaseAgent:
    """
    Base agent class providing core functionality for network simulation.
    This class should remain protocol-agnostic and contain only essential features.
    Specific behaviors should be implemented in protocol-specific agent classes.
    """
    
    def __init__(self, 
                 agent_id: str, 
                 profile: AgentProfile, 
                 data_collector: Optional['BaseDataCollector'] = None):
        """Initialize base agent with core attributes"""
        self.agent_id = agent_id
        self.profile = profile
        self.collector = data_collector
        
        # Account management - just stores raw accounts
        self.accounts: Dict[str, bytes] = {}  # address -> private_key

        # Initialize with preset addresses if provided
        if self.profile.preset_addresses:
            for address in self.profile.preset_addresses:
                self.accounts[address] = bytes()  # Empty bytes since we'll impersonate
                
            # Record if collector exists
          #  if self.collector and self.collector.current_run_id:
          #      for i, address in enumerate(self.accounts.keys()):
          #          self.collector.record_agent_address(
          #              self.agent_id,
          #              address,
          #              is_primary=(i == 0)
          #          )
        
        # Generic state management
        self.state: Dict[str, Any] = {
            'balances-ERC20': {},  # {account: {contract: balance}}
            'balances-history': [],  # List of BalanceUpdate
            'isGroup': []
        }
        
        # Action tracking
        self.last_actions: Dict[str, int] = {}  # action_name -> last block
        self.daily_action_counts: Dict[str, int] = {}  # date -> count
        self.action_history: List[Tuple[str, int]] = []  # List of (action, block)
        
        self.creation_time = datetime.now()
        
    def create_account(self) -> Tuple[str, bytes]:
        """Create a new blockchain account or use preset addresses"""
        # If using preset addresses and haven't reached target count, return None
        if self.profile.preset_addresses:
            logger.debug(f"Using preset addresses for agent {self.agent_id}")
            return None, None
            
        try:
            private_key = secrets.token_bytes(32)
            account = Account.from_key(private_key)
            
            # Store account info
            self.accounts[account.address] = private_key
            
            # Fund account if needed and not using preset addresses
            networks.provider.set_balance(account.address, int(10000e18))
            
            # Record if collector exists
            if self.collector and self.collector.current_run_id:
                self.collector.record_agent_address(
                    self.agent_id,
                    account.address,
                    is_primary=(len(self.accounts) == 1)
                )
                
            return account.address, private_key
            
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            raise

    def create_account2(self) -> Tuple[str, bytes]:
        """Create a new blockchain account"""
        try:
            private_key = secrets.token_bytes(32)
            account = Account.from_key(private_key)
            
            # Store account info
            self.accounts[account.address] = private_key
            
            # Fund account if needed
            networks.provider.set_balance(account.address, int(10000e18))
            
            # Record if collector exists
            if self.collector and self.collector.current_run_id:
                self.collector.record_agent_address(
                    self.agent_id,
                    account.address,
                    is_primary=(len(self.accounts) == 1)
                )
                
            return account.address, private_key
            
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            raise
            
    def get_accounts(self) -> List[str]:
        """Get all controlled addresses"""
        return list(self.accounts.keys())
        
    def get_random_account(self) -> Optional[Tuple[str, bytes]]:
        """Get a random controlled account"""
        if not self.accounts:
            return None
        address = random.choice(list(self.accounts.keys()))
        return address, self.accounts[address]
        
    def select_action(self, current_block: int, network_state: Dict[str, Any]) -> Tuple[Optional[str], str, Dict]:
        """
        Select an action based on profile configuration and current state
        Returns: (action_name, acting_address, params) or (None, "", {})
        """
        # Check daily action limit
        today = datetime.now().date().isoformat()
        if self.daily_action_counts.get(today, 0) >= self.profile.max_daily_actions:
            return None, "", {}
            
        # Get available actions based on configuration
        available_actions = []
        for action_name in self.profile.action_configs.keys():
            last_block = 0 if action_name not in self.last_actions else self.last_actions[action_name]
            if self.profile.can_perform_action(action_name, current_block, last_block):
                available_actions.append((action_name, self.profile.action_configs[action_name].probability))
                
        if not available_actions:
            return None, "", {}
            
        # Select action based on probabilities
        action_name = random.choices(
            [a[0] for a in available_actions],
            weights=[a[1] for a in available_actions]
        )[0]
        
        # Select acting account
        account_tuple = self.get_random_account()
        if not account_tuple:
            return None, "", {}
            
        acting_address, _ = account_tuple
        
        # Get action parameters
        params = self._get_base_params(action_name, acting_address)
        
        return action_name, acting_address, params
        
    def can_perform_action(self, action_name: str, current_block: int, network_state: Dict) -> bool:
        """Check if action can be performed based on basic constraints"""
        try:
            action = self.profile.get_action_config(action_name)
            if not action:
                return False
                
            # Check cooldown
            last_action = self.last_actions.get(action_name, 0)
            if not self.profile.can_perform_action(action_name, current_block, last_action):
                return False
                
            # Check if all base requirements are met
            # Specific requirements should be checked by handlers
            return True
            
        except Exception as e:
            logger.error(f"Error checking action eligibility: {e}")
            return False
            
    def _get_base_params(self, action_name: str, acting_address: str) -> Dict:
        """Get basic parameters needed for any action"""
        action = self.profile.get_action_config(action_name)
        if not action:
            return {}
            
        return {
            'sender': acting_address,
         #   'max_value': action.max_value,
            'risk_tolerance': self.profile.risk_tolerance
        }
        
    def record_action(self, action_name: str, block_number: int, success: bool):
        """Record action execution"""
        if success:
            self.last_actions[action_name] = block_number
            today = datetime.now().date().isoformat()
            self.daily_action_counts[today] = self.daily_action_counts.get(today, 0) + 1
            self.action_history.append((action_name, block_number))
            
    def update_state(self, key: str, value: Any):
        """Update agent's internal state"""
        self.state[key] = value
        
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from agent's state"""
        return self.state.get(key, default)
    
    def update_balance(self, account: str, contract: str, balance: int, 
                      timestamp: datetime, block: int) -> None:
        """Update the ERC20 balance for an account/contract pair"""
        # Skip if not our account
        if account not in self.accounts:
            return
            
        # Initialize if needed
        if account not in self.state['balances-ERC20']:
            self.state['balances-ERC20'][account] = {}
        
        # Only store if non-zero or updating existing entry
        if balance > 0 or contract in self.state['balances-ERC20'][account]:
            self.state['balances-ERC20'][account][contract] = balance
            
            # Add to history
            update = BalanceUpdate(
                contract=contract,
                account=account,
                balance=balance,
                timestamp=timestamp,
                block=block
            )
            self.state['balances-history'].append(update)

    def get_last_balance(self, account: str, contract: str) -> Optional[int]:
        """Get last recorded balance for account/contract pair"""
        return self.state['balances-ERC20'].get(account, {}).get(contract)

    def get_balance_history(self, account: str = None, 
                          contract: str = None) -> List[BalanceUpdate]:
        """Get balance update history, optionally filtered"""
        history = self.state['balances-history']
        
        if account:
            history = [h for h in history if h.account == account]
        if contract:
            history = [h for h in history if h.contract == contract]
            
        return history
    