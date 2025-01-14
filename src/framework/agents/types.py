from enum import Enum, auto

class ActionType(Enum):
    """Available actions derived from protocol handlers"""

    circleshub_MulticallCase1 = auto()
    
    circleshub_Burn = auto()
    
    circleshub_CalculateIssuanceWithCheck = auto()
    
    circleshub_GroupMint = auto()
    
    circleshub_Migrate = auto()
    
    circleshub_OperateFlowMatrix = auto()
    
    circleshub_PersonalMint = auto()
    
    circleshub_RegisterCustomGroup = auto()
    
    circleshub_RegisterGroup = auto()
    
    circleshub_RegisterHuman = auto()
    
    circleshub_RegisterOrganization = auto()
    
    circleshub_SafeBatchTransferFrom = auto()
    
    circleshub_SafeTransferFrom = auto()
    
    circleshub_SetAdvancedUsageFlag = auto()
    
    circleshub_SetApprovalForAll = auto()
    
    circleshub_Stop = auto()
    
    circleshub_Trust = auto()
    
    circleshub_Wrap = auto()
    
    ringshub_Burn = auto()
    
    ringshub_CalculateIssuanceWithCheck = auto()
    
    ringshub_GroupMint = auto()
    
    ringshub_Migrate = auto()
    
    ringshub_OperateFlowMatrix = auto()
    
    ringshub_PersonalMint = auto()
    
    ringshub_RegisterCustomGroup = auto()
    
    ringshub_RegisterGroup = auto()
    
    ringshub_RegisterHuman = auto()
    
    ringshub_RegisterOrganization = auto()
    
    ringshub_SafeBatchTransferFrom = auto()
    
    ringshub_SafeTransferFrom = auto()
    
    ringshub_SetAdvancedUsageFlag = auto()
    
    ringshub_SetApprovalForAll = auto()
    
    ringshub_Stop = auto()
    
    ringshub_Trust = auto()
    
    ringshub_Wrap = auto()
    
    wxdai_Approve = auto()
    
    wxdai_Deposit = auto()
    
    wxdai_Transfer = auto()
    
    wxdai_TransferFrom = auto()
    
    wxdai_Withdraw = auto()
    