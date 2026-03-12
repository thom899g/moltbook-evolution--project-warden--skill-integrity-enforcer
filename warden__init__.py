"""
Project Warden v2.0: Capability-First Trust Architecture
Core security layer for ClawdHub/Moltbook Evolution Ecosystem

Copyright 2024 Evolution Ecosystem. All Rights Reserved.
Version: 2.0.0-alpha
"""

__version__ = "2.0.0-alpha"
__author__ = "Project Warden Team"
__license__ = "Proprietary - Evolution Ecosystem Internal Use Only"

# Export public API
from .config import WardenConfig
from .firebase_client import FirebaseClient
from .capability_token import CapabilityToken, TokenManager
from .wasm_runtime import WASMRuntime, CapabilityHostInterface
from .reputation_graph import ReputationGraph, TrustCalculator
from .monitoring import AuditLogger, AnomalyDetector
from .telegram_alert import TelegramAlert

__all__ = [
    'WardenConfig',
    'FirebaseClient',
    'CapabilityToken',
    'TokenManager',
    'WASMRuntime',
    'CapabilityHostInterface',
    'ReputationGraph',
    'TrustCalculator',
    'AuditLogger',
    'AnomalyDetector',
    'TelegramAlert'
]