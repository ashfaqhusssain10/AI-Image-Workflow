# HybridAgenticPipeline_PRODUCTION.py
# Integrated Agentic Workflow: 4-Phase Pipeline with Parallel Orchestration
# Created: October 8, 2025
# Architecture: Combines WorkLaptop17 quality loop + WorkLaptop18 parallel processing

# # NEW (Matches your code):
# Image 1: Food (🔴 PRIMARY)
# Image 2: Background (🟡 SECONDARY)
# Image 3: Angle (🟢 TERTIARY)
import os
import json
import requests
import base64
import time
import re
import threading
from typing import List, Dict, Optional, Tuple
from io import BytesIO
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import pickle
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import signal
import sys
from google_images_search import GoogleImagesSearch
import requests
from requests.exceptions import SSLError, Timeout, ConnectionError, ReadTimeout
import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientSession

QUIET_MODE = False  # Set to False to see all logs

def print_log(message, **kwargs):
    """Smart logging - supports print() arguments like end=, flush="""
    if not QUIET_MODE:
        print(message, **kwargs)  # Show everything with all print() options
        return
    
    # In quiet mode, only show these important messages:
    important_keywords = [
        "ITEM ", "/774", "═══",  # Item headers and summaries
        "HUMAN REVIEW", "YOUR OPTIONS", "APPROVE", "REJECT", "SKIP",  # Review prompts
        "✓ Generated", "✓ Downloaded",  # Success messages
        "ERROR", "FAILED", "WARN",  # Errors and warnings
        "Agent decision:", "Agent Recommendation:", "⏰", "DECISION TRACE"  # Agent decisions
    ]
    
    if any(keyword in message for keyword in important_keywords):
        print(message, **kwargs)  # Pass all kwargs (end=, flush=, etc.)

import random
from collections import deque
from threading import Lock
from datetime import datetime, timedelta
import urllib3

import logging
from datetime import datetime
import os

# ============================================================================
# ENHANCED LOGGING SYSTEM
# ============================================================================

class EnhancedLogger:
    """Enhanced logging system that logs to both console and file"""

    def __init__(self, log_dir='logs', log_filename=None):
        """
        Initialize enhanced logger

        Args:
            log_dir: Directory to store log files (default: 'logs')
            log_filename: Custom log filename (default: auto-generated with timestamp)
        """
        # Create logs directory
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # Generate log filename with timestamp if not provided
        if log_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f'pipeline_execution_{timestamp}.txt'

        self.log_filepath = os.path.join(log_dir, log_filename)

        # Configure logging
        self.logger = logging.getLogger('AgenticPipeline')
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler - logs everything
        file_handler = logging.FileHandler(self.log_filepath, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler - respects QUIET_MODE
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Log initialization
        self.logger.info("=" * 80)
        self.logger.info(f"ENHANCED LOGGING SYSTEM INITIALIZED")
        self.logger.info(f"Log file: {self.log_filepath}")
        self.logger.info("=" * 80)

    def info(self, message):
        """Log info message"""
        self.logger.info(message)

    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)

    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message):
        """Log error message"""
        self.logger.error(message)

    def critical(self, message):
        """Log critical message"""
        self.logger.critical(message)

# Initialize global logger (will be used by print_log)
_global_logger = None

def initialize_global_logger(log_dir='logs', log_filename=None):
    """Initialize the global enhanced logger"""
    global _global_logger
    _global_logger = EnhancedLogger(log_dir, log_filename)
    return _global_logger

def get_logger():
    """Get the global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = initialize_global_logger()
    return _global_logger


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ============================================================================
# PRODUCTION SDK IMPORTS
# ============================================================================
try:
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage
    SDK_AVAILABLE = True
    print_log("[INIT] ✓ Google GenAI SDK loaded (production mode)")
except ImportError:
    SDK_AVAILABLE = False
    print_log("[INIT] ⚠ Google GenAI SDK not found - install with: pip install google-genai")
    print_log("[INIT] Falling back to REST API (preview mode)")
# User-Agent rotation pool
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]
# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    'auto_review_mode': True,
    'google': {
        'api_key':'AIzaSyD_yx3bDi0UGOkVvqnfhL5ffPis61mdwJQ', #from data.craftmyplate@gmail.com
        'cx_id': 'f365c3041ae674c13'
    },
     'gemini': {
        'api_key': 'AIzaSyBnPi1ws3Rtu3rQ5McCr3zooG9bDqJAbl0',
        'model_generation': 'gemini-2.5-flash-image',
        'model_analysis': 'gemini-2.5-flash-lite',
        'model_agent_brain': 'gemini-2.5-flash',
        'aspect_ratios': {
        'BEIGE': '4:3',    # Commercial food photography standard
        'MARBLE': '3:2',   # Editorial premium look
        'PAISLEY': '1:1',  # Traditional square presentation
        'PINK': '1:1'      # Social media square
    }
    },
    'paths': {
        'input_json': 'food_items_backgrounds.json',
        'output_dir': 'processed_output_1',
        'reference_dir': 'reference_images_1',
        'checkpoint_dir': 'checkpoints_1',
        'background_images_dir': '.'
    },
    'processing': {
        'max_workers': 1, #5
        'review_timeout': 180,  # 3 minutes
        'checkpoint_interval': 10,
        'max_iterations': 4,#2
        'batch_size': 1,#10
        'phase2_batch_size':3 # Items to pre-process during review
    },
    'rate_limits': {
        'google_search_per_day': 100,
        'gemini_pro_per_minute': 30,
        'flash_generation_interval': 60
    },
    'scoring': {
        'auto_approve_threshold': 70,
        'recommend_approve_threshold': 60,
        'recommend_reject_threshold': 40
    }
}

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ProcessingPhase(Enum):
    PHASE_1_SEARCH = "google_search"
    PHASE_2_FILTER = "angle_filter"
    PHASE_3_SELECT = "reference_select"
    PHASE_4_GENERATE = "ai_generation"
    PHASE_4_REVIEW = "human_review"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ItemState:
    """Complete state for a single food item"""
    item_name: str
    background_type: str
    background_image_path: str  # ← Actual background image (pink.jpg, etc.)
    reference_angle_path: str   # ← Angle reference (angle_reference_pink.jpg, etc.)
    current_phase: ProcessingPhase

    # Phase 1 outputs
    search_strategy: str = None
    candidate_urls: List[str] = None

    # Phase 2 outputs
    filtered_urls: List[Dict] = None

    # Phase 3 outputs
    selected_reference_url: str = None
    downloaded_reference_path: str = None  # ← Food reference from Phase 3

    # Phase 4 outputs
    generated_image_path: str = None
    previous_attempt_paths: List[str] = None  # ← NEW: Track all attempts
    agent_score: int = None
    agent_reasoning: str = None
    agent_recommendation: str = None

    # Human review
    human_decision: str = None
    human_feedback: str = None
    iteration_count: int = 0

    vessel_type: str = "white ceramic bowl"  # ← ADD THIS
    vessel_description: str = "Standard serving bowl"  # ← ADD THIS
    # Timestamps
    started_at: datetime = None
    completed_at: datetime = None

    # Error handling
    error_message: str = None
    retry_count: int = 0
    generation_cost: float = 0.0  # Total cost for this item
    api_calls_made: int = 0

    def __post_init__(self):
        if self.previous_attempt_paths is None:
            self.previous_attempt_paths = []

@dataclass
class PipelineState:
    """Global pipeline state for checkpoint recovery"""
    current_item_index: int = 0
    items_states: Dict[str, ItemState] = None
    total_items: int = 0
    started_at: datetime = None
    checkpoint_count: int = 0

    # Learning patterns
    disagreement_patterns: List[Dict] = None
    background_specific_issues: Dict[str, List[str]] = None

# ============================================================================
# CHECKPOINT RECOVERY SYSTEM
# ============================================================================

class CheckpointManager:
    """Handles state persistence and recovery"""

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save_checkpoint(self, state: PipelineState, checkpoint_name: str = None):
        """Save current pipeline state"""
        if checkpoint_name is None:
            checkpoint_name = f"checkpoint_{state.checkpoint_count:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        checkpoint_path = self.checkpoint_dir / checkpoint_name

        try:
            with open(checkpoint_path, 'wb') as f:
                pickle.dump(state, f)
            print_log(f"\n[CHECKPOINT] Saved: {checkpoint_path}")
            print_log(f"[CHECKPOINT] Progress: {state.current_item_index}/{state.total_items} items")
            return checkpoint_path
        except Exception as e:
            print_log(f"[ERROR] Checkpoint save failed: {e}")
            return None

    def load_latest_checkpoint(self) -> Optional[PipelineState]:
        """Load most recent checkpoint"""
        checkpoints = sorted(self.checkpoint_dir.glob("checkpoint_*.pkl"))

        if not checkpoints:
            print_log("[INFO] No checkpoints found. Starting fresh.")
            return None

        latest = checkpoints[-1]
        try:
            with open(latest, 'rb') as f:
                state = pickle.load(f)
            print_log(f"\n[RECOVERY] Loaded checkpoint: {latest}")
            print_log(f"[RECOVERY] Resuming from item {state.current_item_index}/{state.total_items}")
            return state
        except Exception as e:
            print_log(f"[ERROR] Checkpoint load failed: {e}")
            return None

# ============================================================================
# BACKGROUND-SPECIFIC PROMPT ENGINE
# ============================================================================
class BackgroundPromptEngine:
    """Generates background-specific prompts with explicit image references"""
    BACKGROUND_PROMPTS = {
        'BEIGE': """
    ═══════════════════════════════════════════════════════════════
    TASK: Generate a photorealistic image of {item_name}
    ═══════════════════════════════════════════════════════════════

    IMAGE REFERENCE GUIDE (FOLLOW EXACTLY):

    🔴 IMAGE 1 - FOOD REFERENCE (PRIMARY SOURCE):
    • This is {item_name} - YOUR MAIN REFERENCE
    • Extract ONLY the food appearance/colors/textures
    • DO NOT copy the vessel from this image
    • Ignore background and vessel - extract food only

    🟡 IMAGE 2 - BACKGROUND SURFACE:
    • Neutral beige surface (#F5F5DC to #E8DCC4)
    • Use as the base canvas

    🟢 IMAGE 3 - CAMERA ANGLE GUIDE:
    • Shows desired camera perspective (45-60° oblique)
    • Use ONLY for angle/viewpoint reference
    • DO NOT extract or copy any food/vessel from this image

    ═══════════════════════════════════════════════════════════════

    VESSEL GENERATION (CRITICAL):

    Generate a FRESH {vessel_type}:
    - Description: {vessel_description}
    - DO NOT copy vessel from Image 1 or Image 3
    - Create new vessel matching the description
    - Style: Modern, clean, commercial aesthetic
    - Size: Appropriate for single serving

    ═══════════════════════════════════════════════════════════════

    FOOD PLACEMENT PHYSICS (MOST CRITICAL):

    Natural Settling:
    - {item_name} must rest INSIDE the {vessel_type}, NOT floating
    - Food settles at bottom due to gravity
    - Fill level: 65-75% of vessel capacity
    - Food makes natural contact with vessel interior walls

    Realistic Arrangement:
    - Individual components visible and distinct
    - Natural stacking/settling (not geometric patterns)
    - Garnishes rest ON TOP of food surface
    - No hovering or floating elements

    Integration:
    - Vessel base makes full contact with beige surface
    - Vessel casts shadow (20% opacity, southeast)
    - Food and vessel form cohesive composition
    - No visible compositing artifacts

    ═══════════════════════════════════════════════════════════════

    COMPOSITION & STYLING:

    Camera: 50mm lens, f/5.6, 30cm height, 50° oblique angle
    Lighting: 3-point setup (key 60%, fill 30%, rim 10%)
    Color temp: 5000K neutral daylight
    Shadows: 20% opacity, southeast direction
    Style: Clean, professional, commercial food photography

    ═══════════════════════════════════════════════════════════════

    CRITICAL REMINDERS:
    ⚠️ Image 1 = Food appearance reference ONLY (ignore its vessel)
    ⚠️ Generate fresh {vessel_type} based on description
    ⚠️ Image 3 = Angle reference ONLY (ignore its food/vessel)
    ⚠️ Food naturally placed INSIDE vessel (no floating)
    ═══════════════════════════════════════════════════════════════
    """,

        'MARBLE': """
    ═══════════════════════════════════════════════════════════════
    TASK: Generate a photorealistic image of {item_name}
    ═══════════════════════════════════════════════════════════════

    IMAGE REFERENCE GUIDE (FOLLOW EXACTLY):

    🔴 IMAGE 1 - FOOD REFERENCE (PRIMARY SOURCE):
    • This is {item_name} - YOUR MAIN REFERENCE
    • Extract ONLY the food appearance/colors/textures
    • DO NOT copy the vessel from this image
    • Ignore background and vessel - extract food only

    🟡 IMAGE 2 - BACKGROUND SURFACE:
    • White Carrara marble with natural gray veining
    • Use as the base canvas

    🟢 IMAGE 3 - CAMERA ANGLE GUIDE:
    • Shows desired camera perspective (45-60° oblique)
    • Use ONLY for angle/viewpoint reference
    • DO NOT extract or copy any food/vessel from this image

    ═══════════════════════════════════════════════════════════════

    VESSEL GENERATION (CRITICAL):

    Generate a FRESH {vessel_type}:
    - Description: {vessel_description}
    - DO NOT copy vessel from Image 1 or Image 3
    - Create new vessel matching the description
    - Style: Premium, elegant, fine dining aesthetic
    - Material: White porcelain or ceramic with refined finish
    - Size: Appropriate for elegant presentation

    ═══════════════════════════════════════════════════════════════

    FOOD PLACEMENT PHYSICS (MOST CRITICAL):

    Natural Settling:
    - {item_name} must rest INSIDE the {vessel_type}, NOT floating
    - Food settles at bottom due to gravity
    - Fill level: 65-75% of vessel capacity
    - Food makes natural contact with vessel interior walls

    Realistic Arrangement:
    - Individual components visible and distinct
    - Natural stacking/settling (not geometric patterns)
    - Garnishes rest ON TOP of food surface
    - No hovering or floating elements

    Marble Integration:
    - Vessel base makes full contact with marble surface
    - Vessel casts shadow (20% opacity with 4px blur)
    - Subtle reflections on marble (20% opacity)
    - Marble veins visible around vessel base
    - No visible compositing artifacts

    ═══════════════════════════════════════════════════════════════

    COMPOSITION & STYLING:

    Camera: 50mm lens, f/5.6, 30cm height, 55° oblique angle
    Lighting: Enhanced rim lighting for reflections
    Color temp: 5000K neutral daylight
    Shadows: 20% opacity with 4px blur, southeast direction
    Reflections: 20% opacity following marble veins
    Style: Luxurious, elegant, fine dining aesthetic

    ═══════════════════════════════════════════════════════════════

    CRITICAL REMINDERS:
    ⚠️ Image 1 = Food appearance reference ONLY (ignore its vessel)
    ⚠️ Generate fresh {vessel_type} based on description
    ⚠️ Image 3 = Angle reference ONLY (ignore its food/vessel)
    ⚠️ Food naturally placed INSIDE vessel (no floating)
    ═══════════════════════════════════════════════════════════════
    """,

        'PAISLEY': """
    ═══════════════════════════════════════════════════════════════
    TASK: Generate a photorealistic image of {item_name}
    ═══════════════════════════════════════════════════════════════

    IMAGE REFERENCE GUIDE (FOLLOW EXACTLY):

    🔴 IMAGE 1 - FOOD REFERENCE (PRIMARY SOURCE):
    • This is {item_name} - YOUR MAIN REFERENCE
    • Extract ONLY the food appearance/colors/textures
    • DO NOT copy the vessel from this image
    • Ignore background and vessel - extract food only

    🟡 IMAGE 2 - BACKGROUND SURFACE:
    • Traditional paisley fabric pattern
    • Use as the base canvas

    🟢 IMAGE 3 - CAMERA ANGLE GUIDE:
    • Shows desired camera perspective (45-60° oblique)
    • Use ONLY for angle/viewpoint reference
    • DO NOT extract or copy any food/vessel from this image

    ═══════════════════════════════════════════════════════════════

    VESSEL GENERATION (CRITICAL):

    Generate a FRESH {vessel_type}:
    - Description: {vessel_description}
    - DO NOT copy vessel from Image 1 or Image 3
    - Create new vessel matching the description
    - Style: Traditional, ethnic, heritage aesthetic
    - Material: Brass, copper, or traditional materials
    - Size: Appropriate for cultural presentation

    ═══════════════════════════════════════════════════════════════

    FOOD PLACEMENT PHYSICS (MOST CRITICAL):

    Natural Settling:
    - {item_name} must rest INSIDE the {vessel_type}, NOT floating
    - Food settles at bottom due to gravity
    - Fill level: 65-75% of vessel capacity
    - Food makes natural contact with vessel interior walls

    Realistic Arrangement:
    - Individual components visible and distinct
    - Natural stacking/settling (not geometric patterns)
    - Garnishes rest ON TOP of food surface
    - No hovering or floating elements

    Fabric Integration:
    - Vessel base makes full contact with fabric
    - Vessel weight creates fabric depression (5-7px radial)
    - Paisley pattern warps naturally around vessel
    - Radial wrinkles from vessel weight
    - Shadow 25% opacity with warm tone

    ═══════════════════════════════════════════════════════════════

    COMPOSITION & STYLING:

    Camera: 50mm lens, f/5.6, 30cm height, 55° oblique angle
    Lighting: Warm cultural tones (4500K)
    Fabric physics: 5-7px depression, radial wrinkles
    Pattern warping: Follows fabric tension naturally
    Shadow: 25% opacity with warm tone
    Style: Traditional, ethnic, heritage presentation

    ═══════════════════════════════════════════════════════════════

    CRITICAL REMINDERS:
    ⚠️ Image 1 = Food appearance reference ONLY (ignore its vessel)
    ⚠️ Generate fresh {vessel_type} based on description
    ⚠️ Image 3 = Angle reference ONLY (ignore its food/vessel)
    ⚠️ Food naturally placed INSIDE vessel (no floating)
    ═══════════════════════════════════════════════════════════════
    """
    }


    
    @staticmethod
    def get_background_type(background_filename: str) -> str:
        """Extract background type from filename
        
        Args:
            background_filename: "pink.jpg", "white_marble.png", "paisley_cloth.png", or "beige.png"
            
        Returns:
            "PINK", "MARBLE", "PAISLEY", or "BEIGE"
        """
        bg_lower = background_filename.lower()
        
        if 'pink' in bg_lower:
            return 'PINK'
        elif 'marble' in bg_lower or 'marbel' in bg_lower:  # Handle typo in your JSON
            return 'MARBLE'
        elif 'paisley' in bg_lower:
            return 'PAISLEY'
        elif 'beige' in bg_lower:
            return 'BEIGE'
        else:
            raise ValueError(f"Unknown background type: {background_filename}. Supported: pink, marble, paisley, beige")

    @staticmethod
    def get_prompt(item_name: str, background_type: str, vessel_type: str = "white ceramic bowl", 
                vessel_description: str = "Standard serving bowl") -> str:
        """
        Get background-specific prompt for first iteration with vessel specifications
        
        Args:
            item_name: Food item name (e.g., "Chicken Biryani")
            background_type: BEIGE, MARBLE, or PAISLEY
            vessel_type: Type of vessel (e.g., "brass_handi", "white_ceramic_bowl")
            vessel_description: Detailed vessel description
        
        Returns:
            Formatted prompt string with all parameters inserted
        """
        if background_type not in BackgroundPromptEngine.BACKGROUND_PROMPTS:
            raise ValueError(f"Invalid background type: {background_type}")
        
        # Format vessel type for natural language (replace underscores with spaces)
        vessel_type_natural = vessel_type.replace('_', ' ')
        
        return BackgroundPromptEngine.BACKGROUND_PROMPTS[background_type].format(
            item_name=item_name,
            vessel_type=vessel_type_natural,
            vessel_description=vessel_description
        )


    @staticmethod
    def get_refinement_prompt(item_name: str, background_type: str, vessel_type: str, 
                            vessel_description: str, refinement_notes: str) -> str:
        """
        Get refinement prompt for iterations 2+ with vessel specifications
        
        Args:
            item_name: Food item name
            background_type: BEIGE, MARBLE, or PAISLEY  
            vessel_type: Type of vessel
            vessel_description: Detailed vessel description
            refinement_notes: Human feedback from previous iteration
        
        Returns:
            Formatted refinement prompt
        """
        # Format vessel type for natural language
        vessel_type_natural = vessel_type.replace('_', ' ')
        
        # Get base prompt with vessel info
        base_prompt = BackgroundPromptEngine.BACKGROUND_PROMPTS[background_type].format(
            item_name=item_name,
            vessel_type=vessel_type_natural,
            vessel_description=vessel_description
        )
        
        refinement_addition = f"""

    ═══════════════════════════════════════════════════════════════
    🔵 REFINEMENT ITERATION - ADDRESSING PREVIOUS ISSUES
    ═══════════════════════════════════════════════════════════════

    IMAGE 4 (IF PROVIDED) - PREVIOUS REJECTED ATTEMPT:
    • Your previous generation was REJECTED
    • This is shown for reference ONLY
    • DO NOT copy or reuse this attempt
    • Generate a COMPLETELY NEW image

    SPECIFIC ISSUES TO FIX:
    {refinement_notes}

    INSTRUCTIONS FOR THIS ITERATION:
    1. Generate a COMPLETELY NEW image (do not reuse Image 4)
    2. Address ALL specific issues listed above
    3. Still use Image 1 for food appearance, Image 2 for background, Image 3 for angle
    4. Still generate fresh {vessel_type_natural} as specified
    5. Image 4 is ONLY to understand what went wrong
    6. Make VISIBLE improvements based on the feedback

    CRITICAL: The previous version was rejected. You MUST make noticeable changes to address: {refinement_notes}

    ═══════════════════════════════════════════════════════════════
    """
        
        return base_prompt + refinement_addition


class AdaptiveRateLimiter:
    """Military-grade rate limiter designed to survive Google's detection"""
    
    def __init__(self):
        self.base_delay = 30  # ← MINIMUM 12 seconds between requests
        self.max_delay = 180.0  # ← Max 3 minutes
        self.consecutive_failures = 0
        self.request_times = deque(maxlen=50)
        self.lock = Lock()
        self.circuit_open = False
        self.circuit_open_until = None
        
    def wait_if_needed(self):
        """Enforce rate limit with jitter and circuit breaking"""
        with self.lock:
            # Circuit breaker check
            if self.circuit_open:
                if datetime.now() < self.circuit_open_until:
                    wait = (self.circuit_open_until - datetime.now()).total_seconds()
                    print_log(f"[RATE LIMIT] Circuit open, waiting {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    self.circuit_open = False
                    self.consecutive_failures = 0
                    print_log(f"[RATE LIMIT] Circuit closed, resuming...")
            
            # Clean old requests (>60s ago)
            now = datetime.now()
            while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
                self.request_times.popleft()
            
            # Calculate delay with exponential backoff + jitter
            base = self.base_delay * (1.5 ** self.consecutive_failures)
            jitter = random.uniform(0, base * 0.3)  # ± 30% jitter
            total_delay = min(base + jitter, self.max_delay)
            
            # Enforce requests per minute (max 4)
            if len(self.request_times) >= 30:
                oldest = self.request_times[0]
                time_since_oldest = (now - oldest).total_seconds()
                if time_since_oldest < 60:
                    extra_wait = 60 - time_since_oldest + random.uniform(2, 5)
                    print_log(f"[RATE LIMIT] RPM cap, waiting {extra_wait:.1f}s...")
                    time.sleep(extra_wait)
            
            # Apply delay
            if self.request_times:
                time_since_last = (now - self.request_times[-1]).total_seconds()
                if time_since_last < total_delay:
                    wait = total_delay - time_since_last
                    print_log(f"[RATE LIMIT] Enforcing {wait:.1f}s delay...")
                    time.sleep(wait)
            
            # Record this request
            self.request_times.append(datetime.now())
            
    async def wait_if_needed_async(self):
        """Async version - NON-BLOCKING waits"""
        delay_to_wait = 0
        extra_wait = 0
        
        now = datetime.now()
        
        # Clean old requests (>60s ago)
        while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
            self.request_times.popleft()
        
        # Calculate delay
        base = self.base_delay * (1.5 ** self.consecutive_failures)
        jitter = random.uniform(0, base * 0.3)
        total_delay = min(base + jitter, self.max_delay)
        
        # ✅ YOUR ACCOUNT: 200 requests per minute limit for gemini-2.5-pro
        if len(self.request_times) >= 200:
            oldest = self.request_times[0]
            time_since_oldest = (now - oldest).total_seconds()
            if time_since_oldest < 60:
                extra_wait = (60 - time_since_oldest) + random.uniform(0.5, 1.5)
                print_log(f"[RATE LIMIT ASYNC] RPM cap (200/min), waiting {extra_wait:.1f}s...")
        
        # Apply regular delay
        if self.request_times:
            time_since_last = (now - self.request_times[-1]).total_seconds()
            if time_since_last < total_delay:
                wait = total_delay - time_since_last
                delay_to_wait = wait
        
        # Async sleep
        if extra_wait > 0:
            await asyncio.sleep(extra_wait)
        elif delay_to_wait > 0:
            #print_log(f"[RATE LIMIT ASYNC] Waiting {delay_to_wait:.1f}s...")
            await asyncio.sleep(delay_to_wait)
        
        # Record this request
        self.request_times.append(datetime.now())


    
    def record_success(self):
        """Reset backoff on success"""
        with self.lock:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
    
    def record_failure(self, error_type: str):
        """Escalate backoff on failure"""
        with self.lock:
            self.consecutive_failures += 1
            
            # Open circuit breaker after 3 failures
            if self.consecutive_failures >= 3:
                self.circuit_open = True
                backoff = min(60 * (2 ** (self.consecutive_failures - 3)), 600)  # Max 10 min
                self.circuit_open_until = datetime.now() + timedelta(seconds=backoff)
                print_log(f"[RATE LIMIT] ⚠️  CIRCUIT BREAKER OPEN for {backoff}s (failures: {self.consecutive_failures})")
                print_log(f"[RATE LIMIT] Error type: {error_type}")
# ============================================================================
# PHASE 1: AGENTIC GOOGLE SEARCH
# ============================================================================

class Phase1_AgenticSearch:
    """Phase 1: Google Images search with agentic strategy selection"""

    def __init__(self, config: dict):
        self.config = config
        self.gis = GoogleImagesSearch(
            config['google']['api_key'],
            config['google']['cx_id']
        )
        self.gemini_api_key = config['gemini']['api_key']
        self.model = config['gemini']['model_agent_brain']
        self.rate_limiter = AdaptiveRateLimiter() 

    def decide_search_strategy(self, item_name: str) -> str:
        """Agent decides: standard vs extended search"""

        decision_prompt = f"""Analyze this food item and decide the optimal search strategy:

FOOD ITEM: "{item_name}"

DECISION CRITERIA:
- STANDARD SEARCH (3 queries): Common, well-known dishes (pasta, pizza, burger, curry)
- EXTENDED SEARCH (5 queries): Rare, regional, or culturally specific items

Consider:
1. Is this a common international dish?
2. Does it have regional/cultural specificity?
3. Are there multiple names or language variants?
4. Is it a fusion or uncommon item?

RESPOND WITH EXACTLY ONE WORD: "STANDARD" or "EXTENDED"
"""

        try:
            response = self._call_gemini_text(decision_prompt)
            strategy = response.strip().upper()

            if strategy not in ['STANDARD', 'EXTENDED']:
                print_log(f"[PHASE 1] Invalid strategy response, defaulting to STANDARD")
                return 'STANDARD'

            print_log(f"[PHASE 1] Agent decision: {strategy} search for '{item_name}'")
            return strategy

        except Exception as e:
            print_log(f"[PHASE 1 ERROR] Strategy decision failed: {e}, defaulting to STANDARD")
            return 'STANDARD'

    def execute_search(self, item_name: str, strategy: str) -> List[str]:
        """Execute search with AGGRESSIVE anti-detection measures"""
        
        if strategy == 'STANDARD':
            queries = self._get_standard_queries(item_name)
        else:
            queries = self._get_extended_queries(item_name)

        all_urls = []
        successful_queries = 0
        failed_queries = 0

        for query_idx, query in enumerate(queries):
            max_retries = 3
            query_succeeded = False
            
            for attempt in range(max_retries):
                try:
                    # ✅ ENFORCE RATE LIMIT BEFORE EVERY REQUEST
                    self.rate_limiter.wait_if_needed()
                    
                    print_log(f"[PHASE 1] Query {query_idx+1}/{len(queries)}: '{query}' (attempt {attempt+1})")
                    
                    search_params = {
                        'q': query,
                        'num': 3,
                        'fileType': 'jpg|png',
                        'imgSize': 'LARGE',
                        'imgType': 'photo'
                    }
                    import random
                    os.environ['USER_AGENT'] = random.choice(USER_AGENTS)

                    self.gis.search(search_params=search_params)

                    # Extract URLs
                    for image in self.gis.results():
                        if image.url and image.url not in all_urls:
                            all_urls.append(image.url)

                    # ✅ RECORD SUCCESS
                    self.rate_limiter.record_success()
                    query_succeeded = True
                    successful_queries += 1
                    print_log(f"[PHASE 1] ✓ Got {len(self.gis.results())} results")
                    break  # Success - exit retry loop
                    
                except (requests.exceptions.SSLError, 
                        requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.ReadTimeout) as e:
                    
                    error_type = type(e).__name__
                    
                    # ✅ RECORD FAILURE (triggers circuit breaker)
                    self.rate_limiter.record_failure(error_type)
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff: 15s, 30s, 60s
                        wait_time = 15 * (2 ** attempt)
                        print_log(f"[PHASE 1] ⚠️  {error_type} on '{query}'")
                        print_log(f"[PHASE 1] Retry {attempt+1}/{max_retries} after {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print_log(f"[PHASE 1] ✗ FAILED: '{query}' after {max_retries} attempts ({error_type})")
                        failed_queries += 1
                        
                except Exception as e:
                    print_log(f"[PHASE 1] ✗ Unexpected error: {type(e).__name__}: {str(e)[:100]}")
                    self.rate_limiter.record_failure("UnexpectedError")
                    failed_queries += 1
                    break  # Don't retry unexpected errors
            
            if not query_succeeded:
                print_log(f"[PHASE 1] ⚠️  Query exhausted: '{query}'")
                # Add extra cooldown after query failure
                cooldown = random.uniform(20, 40)
                print_log(f"[PHASE 1] Cooldown: {cooldown:.1f}s before next query...")
                time.sleep(cooldown)

        print_log(f"\n[PHASE 1] ═══ SEARCH SUMMARY ═══")
        print_log(f"[PHASE 1] Success: {successful_queries}/{len(queries)}")
        print_log(f"[PHASE 1] Failed: {failed_queries}/{len(queries)}")
        print_log(f"[PHASE 1] URLs collected: {len(all_urls)}")
        print_log(f"[PHASE 1] ════════════════════════\n")
        
        if len(all_urls) < 5:
            print_log(f"[PHASE 1] ⚠️  WARNING: Only {len(all_urls)} URLs - consider EXTENDED search or manual intervention")
        
        return all_urls[:20]  # Max 20 URLs

    def _get_standard_queries(self, item_name: str) -> List[str]:
        """4 standard query variations"""
        return  [
        f"{item_name} food photography",
        f"{item_name} restaurant style",
        f"{item_name} overhead view",
        f"{item_name} authentic"
    ]

    def _get_extended_queries(self, item_name: str) -> List[str]:
        """6 extended query variations with regional/cultural context"""
        standard = self._get_standard_queries(item_name)
        extended = [
            f"{item_name} traditional",
            f"{item_name} Indian cuisine"
        ]
        return standard + extended

    def _call_gemini_text(self, prompt: str) -> str:
        """Call Gemini API for text generation"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        headers = {'Content-Type': 'application/json'}
        data = {
                'contents': [{
                    'parts': [{'text': prompt}]
                }],
                'generationConfig': {
                    'temperature': 0.1,  # ← Moderate creativity for search strategy
                    'topP': 0.95,
                    'topK': 40
                }
            }
        response = requests.post(f"{url}?key={self.gemini_api_key}", headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    async def execute_search_async(self, item_name: str, strategy: str) -> List[str]:
        """Async version of execute_search - ALL queries run in parallel"""
        if strategy == 'STANDARD':
            queries = self._get_standard_queries(item_name)
        else:
            queries = self._get_extended_queries(item_name)

        print_log(f"[PHASE 1 ASYNC] Starting parallel search with {len(queries)} queries...")

        # Create single aiohttp session for all queries
        timeout = ClientTimeout(total=30, connect=15)
        async with ClientSession(timeout=timeout) as session:
            # Start all queries simultaneously
            tasks = [
                self._search_single_query_async(session, query, idx+1, len(queries))
                for idx, query in enumerate(queries)
            ]

            # Gather all results (with exception handling)
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten URLs from all results
        all_urls = []
        successful_queries = 0
        failed_queries = 0

        for idx, result in enumerate(results):
            if isinstance(result, list):
                all_urls.extend(result)
                successful_queries += 1
            elif isinstance(result, Exception):
                print_log(f"[PHASE 1 ASYNC] Query {idx+1} failed: {type(result).__name__}")
                failed_queries += 1
            else:
                failed_queries += 1

        print_log(f"\n[PHASE 1 ASYNC] ═══ SEARCH SUMMARY ═══")
        print_log(f"[PHASE 1 ASYNC] Success: {successful_queries}/{len(queries)}")
        print_log(f"[PHASE 1 ASYNC] Failed: {failed_queries}/{len(queries)}")
        print_log(f"[PHASE 1 ASYNC] URLs collected: {len(all_urls)}")
        print_log(f"[PHASE 1 ASYNC] ════════════════════════\n")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls[:20]  # Max 20 URLs


    async def _search_single_query_async(self, session: ClientSession, query: str, 
                                         query_num: int, total_queries: int) -> List[str]:
        """Search a single query with async rate limiting"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # ✅ ENFORCE RATE LIMIT (async, non-blocking)
                await self.rate_limiter.wait_if_needed_async()

                print_log(f"[PHASE 1 ASYNC] Query {query_num}/{total_queries}: '{query}' (attempt {attempt+1})")

                # Build Google Custom Search API URL
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.config['google']['api_key'],
                    'cx': self.config['google']['cx_id'],
                    'q': query,
                    'num': 3,
                    'searchType': 'image',
                    'fileType': 'jpg|png',
                    'imgSize': 'LARGE'
                }

                # Async HTTP request
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        urls = [item['link'] for item in data.get('items', [])]

                        # ✅ RECORD SUCCESS
                        self.rate_limiter.record_success()
                        print_log(f"[PHASE 1 ASYNC] ✓ Got {len(urls)} results")
                        return urls
                    else:
                        error_msg = f"HTTP_{response.status}"
                        self.rate_limiter.record_failure(error_msg)

                        if attempt < max_retries - 1:
                            wait_time = 15 * (2 ** attempt)
                            print_log(f"[PHASE 1 ASYNC] ⚠️ {error_msg} - retry after {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            print_log(f"[PHASE 1 ASYNC] ✗ FAILED after {max_retries} attempts")
                            return []

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                error_type = type(e).__name__
                self.rate_limiter.record_failure(error_type)

                if attempt < max_retries - 1:
                    wait_time = 15 * (2 ** attempt)
                    print_log(f"[PHASE 1 ASYNC] ⚠️ {error_type} - retry after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    print_log(f"[PHASE 1 ASYNC] ✗ FAILED: {error_type}")
                    return []

            except Exception as e:
                print_log(f"[PHASE 1 ASYNC] ✗ Unexpected: {type(e).__name__}: {str(e)[:100]}")
                self.rate_limiter.record_failure("UnexpectedError")
                return []

        return []


# ============================================================================
# PHASE 2: AGENTIC ANGLE FILTERING
# ============================================================================

class Phase2_AgenticAngleFilter:
    """Phase 2: Angle filtering with agentic quality scoring"""

    def __init__(self, config: dict):
        self.config = config
        self.gemini_api_key = config['gemini']['api_key']
        self.model = config['gemini']['model_analysis']

    def filter_images(self, item_name: str, candidate_urls: List[str]) -> List[Dict]:
        """Batch analyze images for angle and quality"""

        filtered_results = []

        # Process in batches of 4
        for i in range(0, len(candidate_urls), 4):
            batch_urls = candidate_urls[i:i+4]

            try:
                batch_results = self._analyze_batch(item_name, batch_urls, background_type=background_type)
                filtered_results.extend(batch_results)

                time.sleep(2)  # Rate limiting

            except Exception as e:
                print_log(f"[PHASE 2 ERROR] Batch analysis failed: {e}")
                continue

        # Filter by score threshold
        accepted = [r for r in filtered_results if r['score'] >= 75]

        print_log(f"[PHASE 2] Filtered {len(accepted)}/{len(filtered_results)} images (score ≥ 75)")
        return sorted(accepted, key=lambda x: x['score'], reverse=True)[:5]
    
    
    async def filter_images_async(self, item_name: str, candidate_urls: List[str],
                                background_type: str = 'BEIGE') -> List[Dict]:
        """Async version - processes batches in parallel with agentic threshold decision"""
        
        # Split into batches of 4 images each
        batch_size = self.config['processing']['phase2_batch_size']
        batches = [
            candidate_urls[i:i+batch_size] 
            for i in range(0, len(candidate_urls), batch_size)
        ]
        
        print_log(f"[PHASE 2 ASYNC] Processing {len(batches)} batches in parallel...")
        
        # Semaphore to limit concurrent Gemini API calls (max 3 at once)
        sem = asyncio.Semaphore(2)
        
        async def process_batch_with_limit(batch, batch_num):
            """Process single batch with rate limiting"""
            async with sem:  # Wait for semaphore
                print_log(f"[PHASE 2 ASYNC] Starting batch {batch_num}/{len(batches)}...")
                loop = asyncio.get_event_loop() 
                
                # Call sync method (Gemini SDK isn't async yet)
                # Run in executor to avoid blocking
                # SDK calls can be slow, add timeout
                try:
                    results = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self._analyze_batch,
                            item_name,
                            batch,
                            background_type
                        ),
                        timeout= 60.0  # 90 second timeout per batch i have added 10s timeout i ahave changed to the 60s
                    )
                except asyncio.TimeoutError:
                    print_log(f"[PHASE 2 ASYNC] Batch {batch_num} timed out after 90s")
                    results = []
                print_log(f"[PHASE 2 ASYNC] Batch {batch_num} complete: {len(results)} results")
                return results
        
        # Create tasks for all batches
        tasks = [
            process_batch_with_limit(batch, i+1)
            for i, batch in enumerate(batches)
        ]
        
        # Execute all batches in parallel (limited by semaphore)
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_results = []
        for result in batch_results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                print_log(f"[PHASE 2 ASYNC] Batch failed: {type(result).__name__}")
        
        if not all_results:
            print_log(f"[PHASE 2 ASYNC] No results from any batch!")
            return []
        
        # Sort by score
        all_results_sorted = sorted(all_results, key=lambda x: x.get('score', 0), reverse=True)
        
        # ═══════════════════════════════════════════════════════════════════════
        # AGENTIC THRESHOLD DECISION
        # ═══════════════════════════════════════════════════════════════════════
        
        # Calculate score distribution
        score_distribution = {
            '≥75': len([r for r in all_results if r.get('score', 0) >= 75]),
            '60-74': len([r for r in all_results if 60 <= r.get('score', 0) < 75]),
            '40-59': len([r for r in all_results if 40 <= r.get('score', 0) < 60]),
            '<40': len([r for r in all_results if r.get('score', 0) < 40])
        }
        
        top_5_scores = [r.get('score', 0) for r in all_results_sorted[:5]]
        
        # Build decision prompt for agent
        decision_prompt = f"""You are the Quality Control Agent evaluating Phase 2 filtering results.

    ITEM: "{item_name}"
    BACKGROUND: {background_type}

    FILTERING RESULTS:
    Total images analyzed: {len(all_results)}

    Score Distribution:
    - Excellent (≥75): {score_distribution['≥75']} images
    - Good (60-74): {score_distribution['60-74']} images  
    - Acceptable (40-59): {score_distribution['40-59']} images
    - Poor (<40): {score_distribution['<40']} images

    Top 5 scores: {top_5_scores}

    TASK:
    Decide the minimum score threshold to proceed to Phase 3 (reference selection).

    DECISION CRITERIA:
    1. Need at least 3 candidates for good Phase 3 selection
    2. Higher threshold = better quality, but fewer options
    3. Lower threshold = more options, but lower quality
    4. If no good candidates exist, must decide whether to proceed or abort

    THRESHOLD OPTIONS:
    - 75: STRICT (only excellent candidates)
    - 60: RELAXED (include good candidates)
    - 40: DESPERATE (include acceptable candidates)
    - 0: ABORT (no viable candidates)

    RESPOND IN THIS EXACT JSON FORMAT:
    {{
    "threshold": 75,
    "decision": "STRICT",
    "reasoning": "Your reasoning here",
    "expected_candidates": 0
    }}

    Make your decision now:"""

        try:
            # Call Gemini Pro for decision
            print_log(f"\n[PHASE 2 ASYNC] Consulting agent for threshold decision...")
            
            # Use existing _call_gemini_text method (sync, but that's fine)
            decision_response = self._call_gemini_text(decision_prompt, temperature=0)
            
            # Parse JSON response
            # Remove markdown code blocks if present
            decision_response = decision_response.strip()
            if decision_response.startswith('```'):
                decision_response = decision_response.split('```')[1]
                if decision_response.startswith('json'):
                    decision_response = decision_response[4:]
            
            decision = json.loads(decision_response.strip())
            
            threshold = decision.get('threshold', 75)
            decision_type = decision.get('decision', 'STRICT')
            reasoning = decision.get('reasoning', 'No reasoning provided')
            expected_count = decision.get('expected_candidates', 0)
            
            print_log(f"\n[PHASE 2 ASYNC] ═══ AGENT DECISION ═══")
            print_log(f"[PHASE 2 ASYNC] Decision: {decision_type}")
            print_log(f"[PHASE 2 ASYNC] Threshold: {threshold}")
            print_log(f"[PHASE 2 ASYNC] Reasoning: {reasoning}")
            print_log(f"[PHASE 2 ASYNC] Expected candidates: {expected_count}")
            print_log(f"[PHASE 2 ASYNC] ══════════════════════════\n")
            
        except Exception as e:
            print_log(f"[PHASE 2 ASYNC] Agent decision failed: {e}")
            print_log(f"[PHASE 2 ASYNC] Using fallback threshold 60")
            threshold = 60
            decision_type = "RELAXED (fallback)"
            reasoning = "Agent decision failed, using safe default"
        
        # Apply agent's threshold decision
        filtered = [r for r in all_results_sorted if r.get('score', 0) >= threshold]
        
        # Agent self-evaluation: Check if decision was good
        if len(filtered) < 2 and threshold > 0:
            print_log(f"\n[PHASE 2 ASYNC] ⚠️ WARNING: Only {len(filtered)} candidate(s) with threshold {threshold}")
            print_log(f"[PHASE 2 ASYNC] Agent reconsidering...")
            
            # Agent auto-corrects if too strict
            if threshold == 75 and score_distribution['60-74'] >= 2:
                threshold = 60
                filtered = [r for r in all_results_sorted if r.get('score', 0) >= threshold]
                print_log(f"[PHASE 2 ASYNC] ✓ Agent relaxed to 60 (found {len(filtered)} candidates)")
            elif threshold == 60 and score_distribution['40-59'] >= 2:
                threshold = 40
                filtered = [r for r in all_results_sorted if r.get('score', 0) >= threshold]
                print_log(f"[PHASE 2 ASYNC] ✓ Agent relaxed to 40 (found {len(filtered)} candidates)")
            elif threshold == 40:
                # Last resort - take top 3 regardless of score
                filtered = all_results_sorted[:3]
                print_log(f"[PHASE 2 ASYNC] ✓ Last resort: taking top {len(filtered)} candidates")
        
        # Final summary
        print_log(f"\n[PHASE 2 ASYNC] ═══ FILTERING SUMMARY ═══")
        print_log(f"[PHASE 2 ASYNC] Total analyzed: {len(all_results)}")
        print_log(f"[PHASE 2 ASYNC] Score distribution:")
        print_log(f"[PHASE 2 ASYNC]   ≥75: {score_distribution['≥75']}")
        print_log(f"[PHASE 2 ASYNC]   60-74: {score_distribution['60-74']}")
        print_log(f"[PHASE 2 ASYNC]   40-59: {score_distribution['40-59']}")
        print_log(f"[PHASE 2 ASYNC]   <40: {score_distribution['<40']}")
        print_log(f"[PHASE 2 ASYNC] Agent threshold: {threshold}")
        print_log(f"[PHASE 2 ASYNC] Selected: {len(filtered)} candidates")
        if filtered:
            scores = [r['score'] for r in filtered]
            print_log(f"[PHASE 2 ASYNC] Score range: {max(scores)}-{min(scores)}")
        print_log(f"[PHASE 2 ASYNC] ═══════════════════════════\n")
        
        return filtered


    def _analyze_batch(self, item_name: str, urls: List[str], 
                    background_type: str = 'BEIGE') -> List[Dict]:
        """Production SDK-based batch analysis with authenticity prioritization"""
        
        # COMPACT PROMPT: 180 tokens (down from 3000)
        prompt = f"""Evaluate {len(urls)} images of "{item_name}" for extraction.

    SCORING (0-100):
    - AUTHENTICITY (40%): Correct dish? Traditional prep? Recognizable as {item_name}?
    - EXTRACTION (30%): Clean background? Clear edges? No overlaps/hands?
    - ANGLE (20%): 40-70° oblique preferred (flexible guideline, not strict)
    - QUALITY (10%): Sharp focus? Good lighting? High resolution?

    AUTO-REJECT (score=0):
    - Watermarks/text overlays
    - Wrong dish entirely
    - Multiple main dishes
    - Extreme angles (<25° or >85°)

    OUTPUT FORMAT:
    IMAGE X: score=Y authenticity=A extraction=E angle=Z° reasoning="concise"

    PRIORITY: Authentic dish at 65° > wrong dish at 50°. Extraction viability critical.

    Analyze:"""
        
        # DOWNLOAD & VALIDATE IMAGES
        images_pil = []
        valid_urls = []
        
        for idx, url in enumerate(urls):
            try:
                response = requests.get(
                    url, 
                    timeout=10, 
                    headers={'User-Agent': random.choice(USER_AGENTS)},
                    verify=True
                )
                
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    from io import BytesIO
                    img = PILImage.open(BytesIO(response.content))
                    
                    # Validate image dimensions (reject tiny images)
                    if img.width < 200 or img.height < 200:
                        print_log(f"[PHASE 2] Skipped tiny image {idx+1}: {img.width}x{img.height}")
                        continue
                    
                    images_pil.append(img)
                    valid_urls.append(url)
                    
            except Exception as e:
                print_log(f"[PHASE 2] Failed to load image {idx+1}: {type(e).__name__}")
                continue
        
        if not images_pil:
            print_log(f"[PHASE 2 ERROR] No valid images downloaded from batch")
            return []
        
        print_log(f"[PHASE 2] Analyzing {len(images_pil)} valid images with SDK...")
        
        # SDK CALL WITH RETRY LOGIC
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            # Build content array: prompt + images
            content = [prompt] + images_pil
            
            # PRODUCTION CONFIG
            config = types.GenerateContentConfig(
                temperature=0.01,  # Deterministic evaluation
                top_p=0.95,
                top_k=40,
                response_mime_type="text/plain"
            )
            
            # EXECUTE WITH AUTOMATIC RETRY
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=content,
                        config=config
                    )
                    
                    response_text = response.text
                    
                    # Parse and return results
                    results = self._parse_analysis_response(response_text, valid_urls)
                    
                    if results:
                        print_log(f"[PHASE 2] ✓ SDK analysis complete: {len(results)} results")
                        return results
                    else:
                        print_log(f"[PHASE 2 WARN] SDK returned empty results, attempt {attempt+1}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        
                except Exception as e:
                    error_type = type(e).__name__
                    print_log(f"[PHASE 2] SDK error ({error_type}): {str(e)[:100]}")
                    
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt
                        print_log(f"[PHASE 2] Retrying after {wait}s...")
                        time.sleep(wait)
                    else:
                        print_log(f"[PHASE 2 ERROR] All SDK retries exhausted")
                        return []
            
            return []
            
        except ImportError:
            print_log(f"[PHASE 2 CRITICAL] SDK not available, falling back to emergency mode")
            return self._analyze_batch_rest_fallback(prompt, images_pil, valid_urls)
        
    def _analyze_batch_rest_fallback(self, prompt: str, images_pil: List, 
                                    valid_urls: List[str]) -> List[Dict]:
        """Emergency REST fallback if SDK fails (compressed payload)"""
        
        print_log(f"[PHASE 2 FALLBACK] Using REST API with compressed images...")
        
        url_api = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        
        # COMPRESS IMAGES AGGRESSIVELY
        compressed_parts = [{'text': prompt}]
        
        for img in images_pil:
            # Resize to max 800px to reduce payload
            max_size = 800
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, PILImage.Resampling.LANCZOS)
            
            # Convert to JPEG with compression
            from io import BytesIO
            buffer = BytesIO()
            img.convert('RGB').save(buffer, format='JPEG', quality=75, optimize=True)
            img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            compressed_parts.append({
                'inline_data': {'mime_type': 'image/jpeg', 'data': img_b64}
            })
        
        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{'parts': compressed_parts}],
            'generationConfig': {'temperature': 0.1, 'topP': 0.9, 'topK': 20}
        }
        
        # REST CALL WITH RETRY
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{url_api}?key={self.gemini_api_key}",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 400:
                    print_log(f"[PHASE 2 FALLBACK] 400 Bad Request - payload likely too large")
                    return []
                
                response.raise_for_status()
                
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                return self._parse_analysis_response(response_text, valid_urls)
                
            except requests.exceptions.HTTPError as e:
                if attempt < 2:
                    wait = 2 ** attempt
                    print_log(f"[PHASE 2 FALLBACK] HTTP {e.response.status_code}, retry after {wait}s")
                    time.sleep(wait)
                else:
                    print_log(f"[PHASE 2 FALLBACK ERROR] All retries failed")
                    return []
            except Exception as e:
                print_log(f"[PHASE 2 FALLBACK ERROR] {type(e).__name__}: {str(e)[:100]}")
                return []
        
        return []


    def _parse_analysis_response(self, response: str, urls: List[str]) -> List[Dict]:
        """Parse SDK/REST response with robust error handling"""
        
        results = []
        lines = response.strip().split('\n')
        
        # PATTERN MATCHING: "IMAGE X: score=Y angle=Z° reasoning="..."
        pattern = r'IMAGE\s+(\d+):\s+score=(\d+).*?angle=(\d+).*?reasoning="([^"]*)"'
        
        for match in re.finditer(pattern, response, re.IGNORECASE | re.DOTALL):
            try:
                img_num = int(match.group(1))
                score = int(match.group(2))
                angle = int(match.group(3))
                reasoning = match.group(4).strip()
                
                # Validate image index
                url_idx = img_num - 1
                if 0 <= url_idx < len(urls):
                    results.append({
                        'url': urls[url_idx],
                        'score': min(score, 100),  # Cap at 100
                        'angle': angle,
                        'reasoning': reasoning[:200]  # Truncate long reasoning
                    })
            except (ValueError, IndexError) as e:
                print_log(f"[PHASE 2 PARSE WARN] Failed to parse image {img_num}: {e}")
                continue
        
        # FALLBACK: Try simpler parsing if structured format fails
        if not results:
            print_log(f"[PHASE 2 PARSE] Structured parsing failed, trying fallback...")
            
            for i, line in enumerate(lines):
                if f"IMAGE {i+1}" in line.upper():
                    try:
                        score_match = re.search(r'score[=:\s]+(\d+)', line, re.IGNORECASE)
                        angle_match = re.search(r'angle[=:\s]+(\d+)', line, re.IGNORECASE)
                        
                        if score_match and i < len(urls):
                            results.append({
                                'url': urls[i],
                                'score': int(score_match.group(1)),
                                'angle': int(angle_match.group(1)) if angle_match else 0,
                                'reasoning': 'Fallback parsing'
                            })
                    except:
                        continue
        
        if not results:
            print_log(f"[PHASE 2 PARSE ERROR] Could not parse any results from response")
            print_log(f"[PHASE 2 PARSE DEBUG] First 500 chars: {response[:500]}")
        
        return results
    def _call_gemini_text(self, prompt: str, temperature: float = 0.1) -> str:
        """Call Gemini API for text generation (for agent decisions)"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': temperature,
                'topP': 0.95,
                'topK': 40
            }
        }
        
        response = requests.post(f"{url}?key={self.gemini_api_key}", 
                                headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']


    def _call_gemini_vision(self, prompt: str, images_data: List[Dict]) -> str:
        """Call Gemini Vision API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        # Construct parts with text + images
        parts = [{'text': prompt}]

        for img_data in images_data:
            parts.append({
                'inline_data': {
                    'mime_type': 'image/jpeg',
                    'data': img_data['base64']
                }
            })

        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{
                'parts': parts
            }]
        }

        response = requests.post(f"{url}?key={self.gemini_api_key}", headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']

# Continue in next part...


# HybridAgenticPipeline_PART2.py
# Continuation: Phase 3, Phase 4, Human Review, and Pipeline Orchestration

# ============================================================================
# PHASE 3: AGENTIC REFERENCE SELECTION
# ============================================================================

class Phase3_AgenticSelection:
    """Phase 3: Best reference selection with composite scoring"""

    def __init__(self, config: dict):
        self.config = config
        self.gemini_api_key = config['gemini']['api_key']
        self.model = config['gemini']['model_agent_brain']
        self.reference_dir = Path(config['paths']['reference_dir'])
        self.reference_dir.mkdir(exist_ok=True)

    def select_and_download(self, item_name: str, filtered_images: List[Dict], 
                           background_type: str) -> Optional[str]:
        """Select best reference and download it"""

        if not filtered_images:
            print_log(f"[PHASE 3 ERROR] No filtered images for '{item_name}'")
            return None

        # Agent selects best image
        best_image = self._agent_select_best(item_name, filtered_images, background_type)

        if not best_image:
            print_log(f"[PHASE 3 ERROR] Agent couldn't select best image")
            return None

        # Download selected reference
        download_path = self._download_reference(item_name, best_image['url'])

        if download_path:
            print_log(f"[PHASE 3] Selected and downloaded reference (score: {best_image['score']})")
            print_log(f"[PHASE 3] Reasoning: {best_image['reasoning']}")

        return download_path

    def _agent_select_best(self, item_name: str, candidates: List[Dict],
                        background_type: str) -> Optional[Dict]:
        """Agent uses multi-step framework to select best reference"""

        selection_prompt = f"""REFERENCE SELECTION TASK

    You are selecting the BEST reference image for generating "{item_name}" on a 
    {background_type} background. This is a CRITICAL decision that affects all 
    downstream generation quality.

    CANDIDATES ({len(candidates)} images after angle filtering):
    ═══════════════════════════════════════════════════════════════════════════
    """

        # Add candidate details
        for i, candidate in enumerate(candidates, 1):
            selection_prompt += f"""
    IMAGE {i}:
    - Phase 2 Score: {candidate.get('score', 0)}/100
    - Estimated Angle: {candidate.get('angle', 'unknown')}°
    - Reasoning: {candidate.get('reasoning', 'N/A')[:120]}...
    """

        selection_prompt += f"""

    DECISION FRAMEWORK (apply in order - skip no steps!):
    ═══════════════════════════════════════════════════════════════════════════

   STEP 1: AUTHENTICITY (Must-Have - 35% weight)
    ────────────────────────────────────────────────────────────────
    Does this represent authentic {item_name}?
    - Correct preparation style?
    - Traditional garnishes/accompaniments?
    - Culturally appropriate vessel and presentation?

    Question: "Which candidate looks most AUTHENTIC?"


    STEP 2: EXTRACTION VIABILITY (Critical - 25% weight)
    ─────────────────────────────────────────────────────
    This image will be used to EXTRACT the food item and composite onto {background_type}.

    Critical Checks:
    ✓ Can you clearly see food boundaries and vessel edges?
    ✓ Is the vessel cleanly separable from background?
    ✓ Are there overlapping objects (utensils, hands, garnishes)?
    ✓ Is the background simple (solid color) or complex (patterns)?
    ✓ Are edges well-defined and in focus?

    Scoring:
    • EXCELLENT: Clean isolation + simple background + sharp edges
    • GOOD: Some clutter but food is clearly separable
    • POOR: Complex background, overlaps, or blurry edges

    Question for yourself: "Which candidate is EASIEST to extract cleanly?"
    STEP 3: ANGLE PRECISION (Important - 20% weight)
    ────────────────────────────────────────────────────────────────
    Target: 40-70° range (flexible)
    Prefer authentic dish at 65° over wrong dish at 50°

    STEP 4: BACKGROUND COMPATIBILITY (Important - 20% weight)
    ──────────────────────────────────────────────────────────
    Target Background: {background_type}

    """

        # Background-specific guidance
        if background_type.upper() == 'BEIGE':
            selection_prompt += """
    BEIGE Background Preferences:
    ✓ PREFER: Clean ceramic/porcelain vessels (white, cream, neutral)
    ✓ PREFER: Modern, minimalist presentation
    ✓ PREFER: Neutral lighting, soft shadows
    ✗ AVOID: Ornate traditional brass/copper vessels
    ✗ AVOID: Patterned surfaces competing with beige texture
    ✗ AVOID: Harsh shadows or dramatic lighting
    """
        elif background_type.upper() == 'MARBLE':
            selection_prompt += """
    MARBLE Background Preferences:
    ✓ PREFER: Elegant vessels (porcelain, ceramic, glass)
    ✓ PREFER: Refined presentation with depth
    ✓ PREFER: Good lighting that will show marble reflections
    ✗ AVOID: Rustic or very casual presentation
    ✗ AVOID: Very dark vessels (won't complement marble)
    """
        elif background_type.upper() == 'PAISLEY':
            selection_prompt += """
    PAISLEY Background Preferences:
    ✓ PREFER: Traditional vessels (brass, copper, kadai, uruli, banana leaf)
    ✓ PREFER: Authentic ethnic presentation
    ✓ PREFER: Warm lighting, rich colors
    ✗ AVOID: Modern minimalist vessels (stark white ceramic)
    ✗ AVOID: Western-style plating or presentation
    """
        elif background_type.upper() == 'PINK':
            selection_prompt += """
    PINK Background Preferences:
    ✓ PREFER: Vibrant food colors (green, yellow, orange) for contrast
    ✓ PREFER: Clean modern vessels, Instagram-style
    ✓ PREFER: Bright, cheerful presentation
    ✗ AVOID: Muted or pale food colors (low contrast with pink)
    ✗ AVOID: Reddish/pink foods (will blend into background)
    """
        else:
            selection_prompt += """
    Generic Background Preferences:
    ✓ PREFER: Vessels that complement background aesthetic
    ✓ PREFER: Good color contrast between food and background
    ✗ AVOID: Elements that clash with background style
    """

        selection_prompt += f"""

    Question for yourself: "Which candidate's vessel/style BEST fits {background_type}?"

    STEP 4: AUTHENTICITY CHECK (Important - 10% weight)
    ────────────────────────────────────────────────────
    Does this represent authentic {item_name}?

    Check:
    • Is the preparation style typical for {item_name}?
    • Is portion size realistic (not too small or oversized)?
    • Is presentation culturally appropriate?
    • Would a customer immediately recognize this as {item_name}?

    Question for yourself: "Which candidate looks most authentic?"

    STEP 5: TECHNICAL QUALITY (Tiebreaker - 5% weight)
    ───────────────────────────────────────────────────
    • Resolution: High enough for generation?
    • Focus: Sharp and clear?
    • Lighting: Well-exposed, not blown out?
    • Compression: Minimal JPEG artifacts?

    ═══════════════════════════════════════════════════════════════════════════

    DECISION PROCESS:
    ─────────────────
    1. Start with candidates that have good angles (45-60°)
    2. Among those, prioritize EXTRACTION VIABILITY (most critical for success!)
    3. Check background compatibility as secondary filter
    4. Use authenticity and technical quality as final tiebreakers

    TRADE-OFF GUIDANCE:
    ───────────────────
    - 75° angle + excellent extraction > 90° angle + cluttered background
    - Prioritize "clean and extractable" over "perfect angle but complex"
    - When in doubt, choose the image that's EASIEST to extract cleanly

    OUTPUT FORMAT:
    ──────────────
    SELECTED: IMAGE X

    REASONING: [2-3 sentences explaining your decision]
    - Angle match: [Why this angle works - specific degrees]
    - Extraction viability: [Why this is cleanly extractable]
    - Background compatibility: [How vessel/style fits {background_type}]
    - Key advantage: [What made this better than other candidates]

    CONFIDENCE: [HIGH/MEDIUM/LOW]

    Begin selection:
    """

        try:
            # Call Gemini for selection
            response = self._call_gemini_text(selection_prompt)

            # Parse response
            match = re.search(r'SELECTED:\s*IMAGE\s*(\d+)', response, re.IGNORECASE)
            if match:
                selected_idx = int(match.group(1)) - 1
                if 0 <= selected_idx < len(candidates):
                    selected = candidates[selected_idx]

                    # Extract reasoning
                    reasoning_match = re.search(
                        r'REASONING:\s*(.+?)(?:CONFIDENCE:|$)', 
                        response, 
                        re.DOTALL | re.IGNORECASE
                    )
                    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"

                    print_log(f"\n[PHASE 3] ═══ AGENT SELECTION ═══")
                    print_log(f"[PHASE 3] Selected: IMAGE {selected_idx + 1}")
                    print_log(f"[PHASE 3] Score: {selected.get('score', 0)}/100")
                    print_log(f"[PHASE 3] Angle: {selected.get('angle', 'unknown')}°")
                    print_log(f"[PHASE 3] Reasoning: {reasoning[:200]}...")
                    print_log(f"[PHASE 3] ═══════════════════════\n")

                    return selected

            # Fallback: highest scored candidate
            print_log("[PHASE 3 WARN] Couldn't parse agent selection, using highest score")
            return max(candidates, key=lambda x: x.get('score', 0))

        except Exception as e:
            print_log(f"[PHASE 3 ERROR] Selection failed: {e}")
            traceback.print_exc()
            return max(candidates, key=lambda x: x.get('score', 0))


    def _download_reference(self, item_name: str, url: str, max_retries: int = 3) -> Optional[str]:
        """Download reference image with anti-block armor"""
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', item_name)
        file_path = self.reference_dir / f"{safe_name}_ref.jpg"

        # Military-grade headers that mimic real browsers
        headers = {
            'User-Agent': random.choice(USER_AGENTS),  # Rotate on each attempt
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        for attempt in range(max_retries):
            try:
                # Add random delay to appear human
                if attempt > 0:
                    delay = random.uniform(2, 5)
                    print_log(f"[PHASE 3] Retry {attempt + 1}/{max_retries} after {delay:.1f}s...")
                    time.sleep(delay)
                
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=15,
                    allow_redirects=True,
                    verify=True  # Keep SSL verification
                )
                response.raise_for_status()

                # Validate we got an actual image
                content_type = response.headers.get('Content-Type', '')
                if 'image' not in content_type:
                    print_log(f"[PHASE 3 WARN] Non-image content type: {content_type}")
                    continue

                # Save image
                with open(file_path, 'wb') as f:
                    f.write(response.content)

                # Verify file is valid
                if os.path.getsize(file_path) < 1024:  # Less than 1KB = suspicious
                    print_log(f"[PHASE 3 WARN] Suspiciously small file: {os.path.getsize(file_path)} bytes")
                    os.remove(file_path)
                    continue

                print_log(f"[PHASE 3] ✓ Downloaded: {len(response.content):,} bytes")
                return str(file_path)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print_log(f"[PHASE 3] 403 Forbidden - rotating User-Agent...")
                    headers['User-Agent'] = random.choice(USER_AGENTS)
                elif e.response.status_code == 404:
                    print_log(f"[PHASE 3] 404 Not Found - URL dead, aborting retries")
                    break
                else:
                    print_log(f"[PHASE 3] HTTP {e.response.status_code}: {str(e)[:100]}")
            
            except requests.exceptions.Timeout:
                print_log(f"[PHASE 3] Timeout after 15s")
            
            except Exception as e:
                print_log(f"[PHASE 3] Unexpected error: {type(e).__name__}: {str(e)[:100]}")

        print_log(f"[PHASE 3 ERROR] All {max_retries} attempts failed for: {url[:80]}...")
        return None
    def _call_gemini_text(self, prompt: str) -> str:
        """Call Gemini API for text generation"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': 0.5,  # ← Slightly creative for selection
                'topP': 0.90,
                'topK': 30
            }
            
        }

        response = requests.post(f"{url}?key={self.gemini_api_key}", headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']

# ============================================================================
# PHASE 4: AI GENERATION & EVALUATION
# ============================================================================
class Phase4_GenerationAndEvaluation:
    """Phase 4: Flash generation + Pro evaluation with proper image references"""

    def __init__(self, config: dict):
        self.config = config
        self.gemini_api_key = config['gemini']['api_key']
        self.model_generation = config['gemini']['model_generation']
        self.cached_backgrounds = {}
        # self.setup_context_caching()
        self.model_evaluation = config['gemini']['model_analysis']
        self.output_dir = Path(config['paths']['output_dir'])
        self.output_dir.mkdir(exist_ok=True)                
    def generate_image(self, item_state: ItemState, iteration: int = 1,
                      refinement_notes: str = None) -> Optional[str]:
        """Generate image using Flash API with proper 3-4 image references"""

        item_name = item_state.item_name
        background_type = item_state.background_type

        # Extract vessel data from item state
        vessel_type = item_state.vessel_type if hasattr(item_state, 'vessel_type') else "white ceramic bowl"
        vessel_description = item_state.vessel_description if hasattr(item_state, 'vessel_description') else "Standard serving bowl"

        # Get appropriate prompt with vessel specifications
        if iteration == 1:
            prompt = BackgroundPromptEngine.get_prompt(
                item_name, 
                background_type,
                vessel_type=vessel_type,
                vessel_description=vessel_description
            )
        else:
            prompt = BackgroundPromptEngine.get_refinement_prompt(
                item_name, 
                background_type,
                vessel_type=vessel_type,
                vessel_description=vessel_description,
                refinement_notes=refinement_notes
            )

        print_log(f"[PHASE 4] Using vessel: {vessel_type}")
        print_log(f"[PHASE 4] Vessel details: {vessel_description}")


        print_log(f"[PHASE 4] Generating {item_name} (iteration {iteration}, {background_type} background)...")

        try:
            generated_path = self._call_flash_generation(
                prompt=prompt,
                background_image_path=item_state.background_image_path,  # ← Image 1
                angle_reference_path=item_state.reference_angle_path,     # ← Image 2
                food_reference_path=item_state.downloaded_reference_path, # ← Image 3
                previous_attempt_path=item_state.previous_attempt_paths[-1] if iteration > 1 and item_state.previous_attempt_paths else None,  # ← Image 4
                item_name=item_name,
                iteration=iteration,
                vessel_type = vessel_type,
                vessel_description=vessel_description
            )

            if generated_path:
                print_log(f"[PHASE 4] ✓ Generated: {generated_path}")
                # Track this attempt
                item_state.previous_attempt_paths.append(generated_path)

            return generated_path

        except Exception as e:
            print_log(f"[PHASE 4 ERROR] Generation failed: {e}")
            traceback.print_exc()
            return None

    def _call_flash_generation(self, prompt: str, 
                              background_image_path: str,
                              angle_reference_path: str,
                              food_reference_path: str,
                              previous_attempt_path: Optional[str],
                              item_name: str, 
                              iteration: int,
                              vessel_type: str = "white ceramic bowl",  # ← ADD THIS
                              vessel_description: str = "Standard serving bowl") -> Optional[str]:
        """Call Flash API using production SDK or REST fallback"""
        
        # Try SDK approach first (production)
        if SDK_AVAILABLE:
            return self._call_flash_generation_sdk(
                prompt, background_image_path, angle_reference_path,
                food_reference_path, previous_attempt_path, item_name, iteration,vessel_type,vessel_description
            )
        else:
            # Fallback to REST (preview mode)
            return self._call_flash_generation_rest(
                prompt, background_image_path, angle_reference_path,
                food_reference_path, previous_attempt_path, item_name, iteration
            )
    def _call_flash_generation_sdk(self, prompt: str,
                                background_image_path: str,
                                angle_reference_path: str,
                                food_reference_path: str,
                                previous_attempt_path: Optional[str],
                                item_name: str,
                                iteration: int,
                               vessel_type: str = "white ceramic bowl",  # ← ADD THIS
                               vessel_description: str = "Standard serving bowl") -> Optional[str]:
        """
        Production SDK implementation with OPTIMIZED image order
        Food reference FIRST (highest priority), then background, then angle
        """
        
        try:
            from google import genai
            from google.genai import types
            from PIL import Image as PILImage
            from io import BytesIO
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            # Determine aspect ratio
            background_filename = os.path.basename(background_image_path)
            background_type = BackgroundPromptEngine.get_background_type(background_filename)
            aspect_ratio = self.config['gemini']['aspect_ratios'].get(background_type, '4:3')
            
            print_log(f"[PHASE 4] Using aspect ratio: {aspect_ratio} for {background_type} background")
            print_log(f"[PHASE 4] Implicit caching enabled (75% discount on bg+angle)")
            
            # ✅ CRITICAL FIX: Put FOOD reference FIRST (highest priority)
            content_parts = []
            
            # Image 1: FOOD SOURCE (MOST IMPORTANT - PUT FIRST!)
            content_parts.append(types.Part(
                text=f"🔴 PRIMARY IMAGE - {item_name.upper()} FOOD REFERENCE (THIS IS WHAT YOU MUST GENERATE):"
            ))
            with open(food_reference_path, 'rb') as f:
                content_parts.append(types.Part(
                    inline_data=types.Blob(
                        mime_type='image/jpeg',
                        data=f.read()
                    )
                ))
            
            # Image 2: Background canvas (secondary)
            content_parts.append(types.Part(
                text=f"🟡 BACKGROUND CANVAS - {background_type.upper()} (Use as base layer):"
            ))
            with open(background_image_path, 'rb') as f:
                bg_mime = 'image/png' if background_image_path.endswith('.png') else 'image/jpeg'
                content_parts.append(types.Part(
                    inline_data=types.Blob(
                        mime_type=bg_mime,
                        data=f.read()
                    )
                ))
            
            # Image 3: Angle reference (tertiary - ANGLE ONLY)
            content_parts.append(types.Part(
                text="🟢 ANGLE REFERENCE - (Copy camera angle ONLY, DO NOT copy the food shown here):"
            ))
            with open(angle_reference_path, 'rb') as f:
                content_parts.append(types.Part(
                    inline_data=types.Blob(
                        mime_type='image/jpeg',
                        data=f.read()
                    )
                ))
            
            # Image 4: Previous attempt (if refinement iteration)
            if previous_attempt_path and iteration > 1 and os.path.exists(previous_attempt_path):
                content_parts.append(types.Part(
                    text="🔵 PREVIOUS REJECTED ATTEMPT (For reference only):"
                ))
                with open(previous_attempt_path, 'rb') as f:
                    content_parts.append(types.Part(
                        inline_data=types.Blob(
                            mime_type='image/jpeg',
                            data=f.read()
                        )
                    ))
            
            # ✅ ENHANCED PROMPT: Very explicit instructions
            # ✅ ENHANCED PROMPT: Very explicit instructions
            enhanced_prompt = f"""
CRITICAL TASK: Generate a photorealistic image of {item_name}

⚠️ MANDATORY SYNTHESIS PROCESS:
═══════════════════════════════════════════════════════════
YOU MUST CREATE A NEW IMAGE BY COMBINING:
1. EXTRACT food appearance from Image 1 ({item_name})
2. UNDERSTAND camera angle from Image 3 (45-60° oblique)
3. PLACE extracted food onto Image 2 background ({background_type})
4. SYNTHESIZE these elements into a NEW composition

❌ AUTOMATIC FAILURE CONDITIONS:
- If output matches Image 3 (angle reference) > 60% = REJECT
- If output matches Image 1 (food reference) > 60% = REJECT
- If output is a direct copy of ANY input image = REJECT
- You MUST create a NEW COMPOSITE IMAGE
═══════════════════════════════════════════════════════════

IMAGE USAGE RULES:
🔴 Image 1 ({item_name}): Extract FOOD APPEARANCE ONLY
   - Colors, textures, garnishes of the food
   - DO NOT copy its angle, vessel, or background

🟡 Image 2 (Background): Use as CANVAS ONLY
   - This is your final background surface

🟢 Image 3 (Angle Reference): Extract CAMERA ANGLE ONLY
   - Understand the viewing perspective
   - DO NOT use any food, vessel, or elements from this image
   - This image shows DIFFERENT FOOD - ignore that food completely

SYNTHESIS REQUIREMENTS:
1. Take the {item_name} appearance from Image 1
2. Mentally rotate/transform it to match Image 3's angle
3. Generate fresh vessel: {vessel_type}
4. Place transformed food in new vessel
5. Composite onto Image 2's {background_type} surface
6. Add proper shadows and lighting

{prompt}
"""
            
         
            
            # Add enhanced prompt last
            content_parts.append(types.Part(text=enhanced_prompt))
            
            # Generate with implicit caching
            response = client.models.generate_content(
                model=self.model_generation,
                contents=[types.Content(role='user', parts=content_parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                    #image_config={"aspect_ratio": aspect_ratio},  # FIXED: Use dict not class
                    temperature=0.7,
                    top_k=50,
                    top_p=0.95
                )
            )
            
            # Check for cache hits
            if hasattr(response, 'usage_metadata') and response.usage_metadata is not None:
                cached_tokens = getattr(response.usage_metadata, 'cached_content_token_count', None)
                if cached_tokens is not None and cached_tokens > 0:
                    print_log(f"[CACHE HIT] ✓ {cached_tokens} tokens cached (75% savings)")
            
            # Add delay after image generation
            time.sleep(10)
            print_log("[RATE LIMIT] ⏸ Waiting 10s after image generation")

            # Extract and save generated image
            for part in response.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    pil_image = PILImage.open(BytesIO(image_bytes))
                    
                    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', item_name)
                    output_path = self.output_dir / f"{safe_name}_iter{iteration}_generated.jpg"
                    
                    pil_image.save(output_path, 'JPEG', quality=95, optimize=True)
                    
                    file_size = os.path.getsize(output_path)
                    
                    print_log(f"[PHASE 4] ✓ Generated: {output_path}")
                    print_log(f"[PHASE 4] ✓ Size: {file_size:,} bytes")
                    print_log(f"[PHASE 4] ✓ Aspect Ratio: {aspect_ratio}")
                    
                    return str(output_path)
            
            print_log(f"[PHASE 4 ERROR] No image in SDK response")
            return None
            
        except Exception as e:
            print_log(f"[PHASE 4 ERROR] SDK generation failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None



    def _get_cache_key_from_filename(self, background_filename: str) -> str:
        """
        Map background filenames from JSON to cache keys
        """
        mapping = {
            'paisley_cloth.png': 'PAISLEY',
            'beige.png': 'BEIGE',
            'white_marbel.png': 'WHITE_MARBLE',  # Note: includes typo from your JSON
            'whitemarble.png': 'WHITE_MARBLE',    # Alternative spelling
            'marbel.png': 'WHITE_MARBLE'          # Another variant
        }
        
        return mapping.get(background_filename, 'BEIGE')  # Default to BEIGE if not found

    def _call_flash_generation_rest(self, prompt: str,
                                   background_image_path: str,
                                   angle_reference_path: str,
                                   food_reference_path: str,
                                   previous_attempt_path: Optional[str],
                                   item_name: str,
                                   iteration: int) -> Optional[str]:
        """REST API fallback (preview mode) - KEEP YOUR EXISTING CODE HERE"""
        
        print_log(f"[PHASE 4] Using REST API fallback (preview mode)")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_generation}:generateContent"

        # Encode Image 1: Background canvas
        with open(background_image_path, 'rb') as f:
            background_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Encode Image 2: Angle reference
        with open(angle_reference_path, 'rb') as f:
            angle_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Encode Image 3: Food reference
        with open(food_reference_path, 'rb') as f:
            food_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Build parts array
        parts = [
            {'text': 'IMAGE 1 - BACKGROUND CANVAS (use as base layer):'},
            {'inline_data': {'mime_type': 'image/jpeg', 'data': background_b64}},
            {'text': 'IMAGE 2 - ANGLE REFERENCE (copy camera angle only):'},
            {'inline_data': {'mime_type': 'image/jpeg', 'data': angle_b64}},
            {'text': f'IMAGE 3 - FOOD SOURCE (extract {item_name} from here):'},
            {'inline_data': {'mime_type': 'image/jpeg', 'data': food_b64}}
        ]

        # Add Image 4 for refinement iterations
        if previous_attempt_path and iteration > 1:
            with open(previous_attempt_path, 'rb') as f:
                previous_b64 = base64.b64encode(f.read()).decode('utf-8')
            parts.extend([
                {'text': 'IMAGE 4 - PREVIOUS REJECTED ATTEMPT (reference only):'},
                {'inline_data': {'mime_type': 'image/jpeg', 'data': previous_b64}}
            ])

        parts.append({'text': prompt})

        # API request payload
        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{'parts': parts}],
            'generationConfig': {
                'temperature': 0.4,
                'topK': 32,
                'topP': 0.95
            }
        }

        try:
            response = requests.post(f"{url}?key={self.gemini_api_key}", 
                                    headers=headers, json=data, timeout=120)
            response.raise_for_status()
            
            result = response.json()

            # Extract image - handle BOTH camelCase and snake_case
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        image_field = part.get('inlineData') or part.get('inline_data')
                        
                        if image_field and 'data' in image_field:
                            image_data = base64.b64decode(image_field['data'])
                            
                            # Save generated image
                            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', item_name)
                            output_path = self.output_dir / f"{safe_name}_iter{iteration}_generated.jpg"
                            
                            with open(output_path, 'wb') as f:
                                f.write(image_data)
                            
                            print_log(f"[PHASE 4] ✓ Generated: {output_path}")
                            print_log(f"[PHASE 4] ✓ Size: {len(image_data):,} bytes")
                            print_log(f"[PHASE 4] ✓ SDK Mode: REST FALLBACK")
                            
                            return str(output_path)

            print_log(f"[PHASE 4 ERROR] No image in REST response")
            return None
            
        except Exception as e:
            print_log(f"[PHASE 4 ERROR] REST generation failed: {type(e).__name__}: {e}")
            return None

    def evaluate_image(self, generated_path: str, item_name: str, 
                    background_type: str, angle_reference_path: str = None) -> Dict:
        """Agent evaluates generated image with copy-check first"""
        
        # FIRST: Check if it's a copy
        copy_check_prompt = f"""
    CRITICAL FIRST CHECK: Is this generated image a copy?

    You are evaluating a generated image of "{item_name}".
    The image should be a NEW COMPOSITION, not a copy of reference images.

    CHECK FOR THESE RED FLAGS:
    1. Does this look EXACTLY like a reference photo?
    2. Is this just the angle reference image with minor changes?
    3. Are there elements that don't match {item_name}?
    4. Does the food look different from what {item_name} should be?

    ANSWER THESE:
    - Is this a copy of the angle reference? (YES/NO)
    - Similarity to angle reference: (0-100%)
    - Is this the correct food item? (YES/NO)
    - Copy confidence: (HIGH/MEDIUM/LOW)

    FORMAT:
    is_copy=YES/NO
    similarity_score=X
    correct_food=YES/NO
    copy_confidence=HIGH/MEDIUM/LOW
    """

        try:
            with open(generated_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # First check for copying
            copy_response = self._call_gemini_vision(copy_check_prompt, image_base64, 
                                                    temperature=0.3)
            
            # Parse copy check
            is_copy = 'is_copy=YES' in copy_response.upper()
            similarity_match = re.search(r'similarity_score=(\d+)', copy_response)
            similarity = int(similarity_match.group(1)) if similarity_match else 0
            
            # Auto-reject if copied
            if is_copy or similarity > 70:
                return {
                    'overall_score': 0,
                    'recommendation': 'REJECT',
                    'reasoning': f'Image appears to be copied from angle reference (similarity: {similarity}%)',
                    'background_score': 0,
                    'angle_score': 0,
                    'authenticity_score': 0,
                    'technical_score': 0,
                    'is_copy': True
                }
            
            # Only evaluate quality if NOT a copy
            evaluation_prompt = f"""
    Evaluate this ORIGINAL generated image of "{item_name}" on {background_type} background.

    SCORING CRITERIA (0-100):
    1. Food Authenticity (35%): Looks like real {item_name}?
    2. Synthesis Quality (25%): Clean composition, not copy-pasted?
    3. Background Integration (20%): Natural on {background_type}?
    4. Angle Accuracy (20%): Matches 45-60° target range?

    Provide scores and recommendation.

    FORMAT EXACTLY AS:
    background_score=X
    angle_score=X
    authenticity_score=X
    technical_score=X
    overall_score=X
    recommendation=APPROVE/REJECT
    reasoning="..."
    """

            response = self._call_gemini_vision(evaluation_prompt, image_base64,
                                            temperature=0.3)
            
            evaluation = self._parse_evaluation(response)
            evaluation['is_copy'] = False
            
            print_log(f"[PHASE 4] Copy Check: PASSED (similarity: {similarity}%)")
            print_log(f"[PHASE 4] Agent Evaluation:")
            print_log(f"  Overall Score: {evaluation['overall_score']}/100")
            print_log(f"  Recommendation: {evaluation['recommendation']}")
            
            return evaluation

        except Exception as e:
            print_log(f"[PHASE 4 ERROR] Evaluation failed: {e}")
            return {
                'overall_score': 0,
                'recommendation': 'REJECT',
                'reasoning': f'Evaluation error: {str(e)}',
                'background_score': 0,
                'angle_score': 0,
                'authenticity_score': 0,
                'technical_score': 0,
                'is_copy': False
            }
    def _call_gemini_vision(self, prompt: str, image_base64: str, 
                           temperature: float = 0.1) -> str:
        """Call Gemini Vision with temperature control"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_evaluation}:generateContent"

        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{
                'parts': [
                    {'inline_data': {'mime_type': 'image/jpeg', 'data': image_base64}},
                    {'text': prompt}
                ]
            }],
            'generationConfig': {
                'temperature': temperature  # ← TEMPERATURE CONTROL
                #'topP': 0.95,
                #'topK': 40
            }
        }

        response = requests.post(f"{url}?key={self.gemini_api_key}", 
                                headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']

    def _parse_evaluation(self, response: str) -> Dict:
        """Parse evaluation response"""
        try:
            background_score = int(re.search(r'background_score=(\d+)', response).group(1))
            angle_score = int(re.search(r'angle_score=(\d+)', response).group(1))
            authenticity_score = int(re.search(r'authenticity_score=(\d+)', response).group(1))
            technical_score = int(re.search(r'technical_score=(\d+)', response).group(1))
            overall_score = int(re.search(r'overall_score=(\d+)', response).group(1))

            recommendation_match = re.search(r'recommendation=(APPROVE|REJECT)', response)
            recommendation = recommendation_match.group(1) if recommendation_match else 'REJECT'

            reasoning_match = re.search(r'reasoning="([^"]+)"', response)
            reasoning = reasoning_match.group(1) if reasoning_match else 'No reasoning provided'

            return {
                'background_score': background_score,
                'angle_score': angle_score,
                'authenticity_score': authenticity_score,
                'technical_score': technical_score,
                'overall_score': overall_score,
                'recommendation': recommendation,
                'reasoning': reasoning
            }
        except Exception as e:
            print_log(f"[EVALUATION PARSE ERROR] {e}")
            return {
                'background_score': 0,
                'angle_score': 0,
                'authenticity_score': 0,
                'technical_score': 0,
                'overall_score': 0,
                'recommendation': 'REJECT',
                'reasoning': f'Parse error: {str(e)}'
            }

# ============================================================================
# HUMAN REVIEW SYSTEM
# ============================================================================

class HumanReviewSystem:
    """Manages 3-minute timed human review with threading"""

    def __init__(self, timeout: int = 180):
        self.timeout = timeout
        self.user_input = None
        self.input_received = threading.Event()

    def conduct_review(self, item_name: str, generated_path: str, evaluation: Dict, iteration: int) -> Tuple[str, Optional[str]]:
        """AUTO-APPROVE using AGENT RECOMMENDATION (smarter than threshold)"""
        print_log("=" * 80)
        print_log(f"AUTO REVIEW: {item_name} | Iteration {iteration}")
        print_log("=" * 80)
         # Check if it's a copy FIRST
        if evaluation.get('is_copy', False):
            print_log(f"🚫 AUTO-REJECT: Image is a COPY of reference")
            print_log(f"   Reason: {evaluation['reasoning']}")
            return 'reject', 'Image appears to be copied from reference - need new synthesis'
        print_log(f"Generated Image: {generated_path}")
        print_log(f"\n📊 EVALUATION:")
        print_log(f"  Overall Score: {evaluation['overall_score']}/100")
        print_log(f"  Agent Recommendation: {evaluation['recommendation']}")
        print_log(f"  Reasoning: {evaluation['reasoning']}")
        print_log("=" * 80)
        
        # ✅ USE AGENT RECOMMENDATION (not just score)
        agent_rec = evaluation['recommendation'].upper()
        score = evaluation['overall_score']
        
        if agent_rec == 'APPROVE' or score >= 75:
            print_log(f"✅ AUTO-APPROVED: Agent recommended approval (Score: {score}/100)")
            return 'approve', None
        else:
            print_log(f"🔄 AUTO-REJECT: Agent recommended rejection (Score: {score}/100)")
            print_log(f"   Reason: {evaluation['reasoning']}")
            return 'reject', evaluation['reasoning']



    def _countdown_timer(self):
        """Display countdown timer"""
        for remaining in range(self.timeout, 0, -10):
            if self.input_received.is_set():
                break
            print_log(f"\r⏰ {remaining} seconds remaining...", end='', flush=True)
            time.sleep(10)

    # Lines 1132-1174 - REPLACE WITH THIS
    def _get_user_input(self):
        """Get user input with proper normalization"""
        
        # ✅ NORMALIZATION MAP
        DECISION_MAP = {
            'a': 'approve',
            'r': 'reject',
            's': 'skip',
            'f': 'feedback'
        }
        
        try:
            raw_input = input("\nYour decision [a/r/s/f]: ").strip().lower()
            
            # ✅ VALIDATE AND NORMALIZE
            if raw_input not in DECISION_MAP:
                print_log(f"\n[INPUT ERROR] Invalid input '{raw_input}'. Defaulting to REJECT.")
                normalized_decision = 'reject'
            else:
                normalized_decision = DECISION_MAP[raw_input]
            
            feedback = None
            if normalized_decision == 'feedback':
                feedback = input("Enter your feedback: ").strip()
                if not feedback:
                    print_log("[INPUT WARN] Empty feedback. Using generic refinement.")
                    feedback = "Improve overall quality, angle accuracy, and background integration."
                normalized_decision = 'reject'  # Feedback implies rejection
            
            # ✅ STORES FULL WORD: 'approve', 'reject', or 'skip'
            self.user_input = {
                'decision': normalized_decision,
                'feedback': feedback
            }
            self.input_received.set()
            
        except EOFError:
            print_log("\n[INPUT ERROR] EOF detected. Auto-rejecting.")
            self.user_input = {'decision': 'reject', 'feedback': 'EOF error'}
            self.input_received.set()
        except KeyboardInterrupt:
            print_log("\n[INPUT ERROR] Keyboard interrupt. Auto-rejecting.")
            self.user_input = {'decision': 'reject', 'feedback': 'Interrupted'}
            self.input_received.set()
        except Exception as e:
            print_log(f"\n[INPUT ERROR] {type(e).__name__}: {e}. Auto-rejecting.")
            self.user_input = {'decision': 'reject', 'feedback': f'Error: {str(e)}'}
            self.input_received.set()

    def _auto_decide(self, score: int) -> str:
        """Auto-decide based on score if timeout"""
        if score >= 90:
            return 'approve'
        else:
            return 'reject'

# Continue in next part...


# HybridAgenticPipeline_PART3.py
# Final Part: Pipeline Orchestration, Parallel Processing, Main Execution

# ============================================================================
# DISAGREEMENT RESOLUTION ENGINE
# ============================================================================

class DisagreementResolutionEngine:
    """Handles human-agent disagreements with forensic analysis"""

    def __init__(self, config: dict):
        self.config = config
        self.gemini_api_key = config['gemini']['api_key']
        self.model = config['gemini']['model_agent_brain']

    def analyze_disagreement(self, item_name: str, agent_recommendation: str,
                            human_decision: str, evaluation: Dict,
                            background_type: str, generated_path: str) -> str:
        """Forensic analysis of why human disagreed with agent"""

        print_log(f"\n[DISAGREEMENT] Agent said {agent_recommendation}, Human chose {human_decision}")
        print_log(f"[DISAGREEMENT] Conducting forensic analysis...")

        analysis_prompt = f"""FORENSIC DISAGREEMENT ANALYSIS

ITEM: {item_name}
BACKGROUND: {background_type}
AGENT RECOMMENDATION: {agent_recommendation}
HUMAN DECISION: {human_decision}

AGENT SCORES:
- Background: {evaluation['background_score']}/100
- Angle: {evaluation['angle_score']}/100
- Authenticity: {evaluation['authenticity_score']}/100
- Technical: {evaluation['technical_score']}/100
- Overall: {evaluation['overall_score']}/100

AGENT REASONING: {evaluation['reasoning']}

ANALYZE:
1. Why might the human have disagreed?
2. What specific aspect did the agent misjudge?
3. Is this a background-specific failure pattern?
4. What refinement instructions should be provided?

Provide concise refinement instructions (2-3 sentences) for regeneration.

FORMAT:
failure_reason="..."
refinement_instructions="..."
"""

        try:
            # Encode generated image for visual analysis
            with open(generated_path, 'rb') as f:
                image_b64 = base64.b64encode(f.read()).decode('utf-8')

            response = self._call_gemini_vision(analysis_prompt, image_b64)

            # Parse refinement instructions
            refinement_match = re.search(r'refinement_instructions="([^"]+)"', response)
            refinement = refinement_match.group(1) if refinement_match else "Please improve overall quality."

            reason_match = re.search(r'failure_reason="([^"]+)"', response)
            reason = reason_match.group(1) if reason_match else "Unknown"

            print_log(f"[DISAGREEMENT] Failure Reason: {reason}")
            print_log(f"[DISAGREEMENT] Refinement: {refinement}")

            return refinement

        except Exception as e:
            print_log(f"[DISAGREEMENT ERROR] Analysis failed: {e}")
            return "Please improve the image quality, angle accuracy, and background consistency."

    def _call_gemini_vision(self, prompt: str, image_base64: str) -> str:
        """Call Gemini Vision"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{
                'parts': [
                    {'inline_data': {'mime_type': 'image/jpeg', 'data': image_base64}},
                    {'text': prompt}
                ]
                
            }],
            'generationConfig': {
                'temperature': 0.2,  # ← Slightly creative for selection
                'topP': 0.95,
                'topK': 40
            }
        }

        response = requests.post(f"{url}?key={self.gemini_api_key}", headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']

# ============================================================================
# PARALLEL TASK ORCHESTRATOR
# ============================================================================

class ParallelTaskOrchestrator:
    """Manages parallel processing during human review windows"""

    def __init__(self, config: dict):
        self.config = config
        self.max_workers = config['processing']['max_workers']
        self.phase1 = Phase1_AgenticSearch(config)
        self.phase2 = Phase2_AgenticAngleFilter(config)
        self.phase3 = Phase3_AgenticSelection(config)
        self.ready_queue = Queue()

    def process_batch_during_review(self, items_batch: List[Dict]) -> List[ItemState]:
        """Process Phases 1-3 for multiple items in parallel"""

        print_log(f"\n[PARALLEL] Processing {len(items_batch)} items during review window...")

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_item_phases_1_3, item): item 
                for item in items_batch
            }

            for future in as_completed(futures):
                item = futures[future]
                try:
                    item_state = future.result()
                    results.append(item_state)
                    print_log(f"[PARALLEL] ✓ Completed Phases 1-3 for {item_state.item_name}")
                except Exception as e:
                    print_log(f"[PARALLEL ERROR] Failed for {item['item_name']}: {e}")
                    # Create failed state
                    failed_state = self._create_failed_state(item, str(e))
                    results.append(failed_state)

        return results

    def _process_item_phases_1_3(self, item: Dict) -> ItemState:
        """Execute Phases 1-3 for a single item"""

        item_name = item['item_name']
        background_image = item['Background image']
        reference_img = item['reference_img']

        # ✅ STEP 7: Extract vessel information from JSON
        vessel_type = item.get('vessel_type', 'white_ceramic_bowl')
        vessel_description = item.get('vessel_description', 'Standard serving bowl')
        
        print_log(f"[INIT] Item: {item_name}, Vessel: {vessel_type}")
# Determine background type
        background_type = BackgroundPromptEngine.get_background_type(background_image)
        # Initialize state
        state = ItemState(
            item_name=item_name,
            background_type=background_type,
            background_image_path=os.path.join(self.config['paths']['background_images_dir'], background_image),
            reference_angle_path=os.path.join(self.config['paths']['background_images_dir'], reference_img),
            vessel_type = vessel_type,
            vessel_description = vessel_description,
            current_phase=ProcessingPhase.PHASE_1_SEARCH,
            started_at=datetime.now()
        )

        try:
            # PHASE 1: Search
            # PHASE 1: Search (ASYNC VERSION)
            print_log(f" [{item_name}] Phase 1: Search (Async)...")
            strategy = self.phase1.decide_search_strategy(item_name)

            # Run async function from synchronous context
            candidate_urls = asyncio.run(
                self.phase1.execute_search_async(item_name, strategy))


            state.search_strategy = strategy
            state.candidate_urls = candidate_urls
            state.current_phase = ProcessingPhase.PHASE_2_FILTER

            if not candidate_urls:
                raise Exception("No candidate URLs found")

            # # PHASE 2: Filter
            # print_log(f"  [{item_name}] Phase 2: Angle Filter...")
            # filtered_images = self.phase2.filter_images(item_name, candidate_urls)
            
             # PHASE 2: Filter (ASYNC VERSION)
            print_log(f" [{item_name}] Phase 2: Filtering (Async)...")
            filtered_images = asyncio.run(
                self.phase2.filter_images_async(item_name, candidate_urls, background_type)
            )


            state.filtered_urls = filtered_images
            state.current_phase = ProcessingPhase.PHASE_3_SELECT

            if not filtered_images:
                raise Exception("No images passed angle filter")

            # PHASE 3: Select & Download
            print_log(f"  [{item_name}] Phase 3: Reference Selection...")
            reference_path = self.phase3.select_and_download(
                item_name, filtered_images, background_type
            )

            state.selected_reference_url = filtered_images[0]['url'] if filtered_images else None
            state.downloaded_reference_path = reference_path
            state.current_phase = ProcessingPhase.PHASE_4_GENERATE

            if not reference_path:
                raise Exception("Failed to download reference")

            return state

        except Exception as e:
            state.current_phase = ProcessingPhase.FAILED
            state.error_message = str(e)
            return state

    def create_failed_state(self, item: Dict, error: str) -> ItemState:
        """Create a failed state for an item"""
        background_type = BackgroundPromptEngine.get_background_type(item['Background image'])
        
        # ✅ STEP 7: Extract vessel info even for failed states
        vessel_type = item.get('vessel_type', 'white_ceramic_bowl')
        vessel_description = item.get('vessel_description', 'Standard serving bowl')
        
        return ItemState(
            item_name=item['item_name'],
            background_type=background_type,
            background_image_path=os.path.join(self.config['paths']['backgroundimagesdir'], item['Background image']),
            reference_angle_path=os.path.join(self.config['paths']['backgroundimagesdir'], item['reference_img']),
            vessel_type=vessel_type,  # ✅ ADD THIS
            vessel_description=vessel_description,  # ✅ ADD THIS
            current_phase=ProcessingPhase.FAILED,
            error_message=error,
            started_at=datetime.now()
        )

# ============================================================================
# MAIN PIPELINE ORCHESTRATOR
# ============================================================================

class HybridAgenticPipeline:
    """Main pipeline orchestrator integrating all phases"""

    def __init__(self, config: dict):
        self.config = config

        # Initialize components
        self.checkpoint_manager = CheckpointManager(config['paths']['checkpoint_dir'])
        self.phase4_generator = Phase4_GenerationAndEvaluation(config)
        self.human_review = HumanReviewSystem(config['processing']['review_timeout'])
        self.disagreement_engine = DisagreementResolutionEngine(config)
        self.parallel_orchestrator = ParallelTaskOrchestrator(config)

        # Create output directories
        self._setup_directories()

        # State
        self.pipeline_state = None

    def _setup_directories(self):
        """Create all necessary directories"""
        Path(self.config['paths']['output_dir']).mkdir(exist_ok=True)
        Path(self.config['paths']['reference_dir']).mkdir(exist_ok=True)
        Path(self.config['paths']['checkpoint_dir']).mkdir(exist_ok=True)

        # Create background-specific output folders
        for bg in ['pink', 'marble', 'paisley']:
            (Path(self.config['paths']['output_dir']) / bg).mkdir(exist_ok=True)

    def run(self, resume: bool = False):
        """Main execution loop with TRUE PARALLEL PROCESSING"""
        print("=" * 80)
        print("HYBRID AGENTIC PIPELINE - PRODUCTION RUN")
        print("=" * 80)
        
        # Load or initialize state
        if resume:
            self.pipeline_state = self.checkpoint_manager.load_latest_checkpoint()
        if self.pipeline_state is None:
            self.pipeline_state = self._initialize_pipeline_state()
        
        # Create background-specific output folders
        for bg in ['beige', 'marble', 'paisley']:
            (Path(self.config['paths']['output_dir']) / bg).mkdir(exist_ok=True)
        
        # Load food items
        vessel_json_path = "food_items_with_vessels.json"
        if os.path.exists(vessel_json_path):
            print_log(f"INIT: Loading items with vessel specifications from {vessel_json_path}")
            with open(vessel_json_path, 'r') as f:
                food_items = json.load(f)
        else:
            print_log(f"INIT: Vessel JSON not found, falling back to {self.config['paths']['input_json']}")
            with open(self.config['paths']['input_json'], 'r') as f:
                food_items = json.load(f)
        
        total_items = len(food_items)
        start_index = self.pipeline_state.current_item_index
        
        print_log(f"PIPELINE: Processing {total_items} items")
        print_log(f"PIPELINE: Starting from index {start_index}")
        print_log(f"PIPELINE: Using {self.config['processing']['max_workers']} parallel workers")
        
        # ✅ PARALLEL PROCESSING - ALL ITEMS AT ONCE
        with ThreadPoolExecutor(max_workers=self.config['processing']['max_workers']) as executor:
            # Submit all items for parallel processing
            futures = {
                executor.submit(self.process_single_item_fully, item, idx): (item, idx) 
                for idx, item in enumerate(food_items[start_index:], start=start_index)
            }
            
            # Process results as they complete
            completed = 0
            for future in as_completed(futures):
                item, idx = futures[future]
                try:
                    item_state = future.result()
                    completed += 1
                    
                    status = "✅" if item_state.current_phase == ProcessingPhase.COMPLETED else "❌"
                    print_log(f"{status} [{completed}/{total_items}] {item_state.item_name}")
                    
                    # Checkpoint every 10 items
                    if completed % 10 == 0:
                        self.pipeline_state.checkpoint_count += 1
                        self.checkpoint_manager.save_checkpoint(self.pipeline_state, f"checkpoint_{completed}.pkl")
                        print_log(f"💾 Checkpoint saved at {completed} items")
                    
                except Exception as e:
                    print_log(f"❌ Error processing {item['item_name']}: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Final checkpoint
        self.pipeline_state.checkpoint_count += 1
        self.checkpoint_manager.save_checkpoint(self.pipeline_state, "checkpoint_FINAL.pkl")
        
        print("=" * 80)
        print("PIPELINE COMPLETED")
        print("=" * 80)
        self._print_summary()


    def process_single_item_fully(self, item: Dict, index: int) -> ItemState:
        """Process one item through all 4 phases (runs in parallel worker)"""
        print_log("=" * 80)
        print_log(f"ITEM {index + 1}: {item['item_name']}")
        print_log("=" * 80)
        
        # Initialize state for this item
        if item['item_name'] not in self.pipeline_state.items_states:
            self.pipeline_state.items_states[item['item_name']] = ItemState(
                item_name=item['item_name'],
                background_type=item.get('Background image', 'beige.png').replace('.png', '').upper(),
                background_image_path=item.get('Background image', 'beige.png'),
                reference_angle_path=item.get('reference_img', 'angle_reference_beige.png'),
                vessel_type=item.get('vessel_type', 'white_ceramic_bowl'),
                vessel_description=item.get('vessel_description', 'Standard serving bowl'),
                current_phase=ProcessingPhase.PHASE_1_SEARCH
            )
        
        item_state = self.pipeline_state.items_states[item['item_name']]
        
        # Skip if already completed or failed
        if item_state.current_phase in [ProcessingPhase.COMPLETED, ProcessingPhase.FAILED, ProcessingPhase.SKIPPED]:
            print_log(f"PIPELINE: Skipping {item['item_name']} - Already {item_state.current_phase.name}")
            return item_state
        
        try:
            # Phase 1-3: Search, filter, reference selection
            item_state = self.parallel_orchestrator._process_item_phases_1_3(item)
            
            # Check if Phases 1-3 succeeded
            if item_state.current_phase == ProcessingPhase.FAILED:
                print_log(f"PIPELINE: Skipping {item['item_name']} - Phases 1-3 failed")
                print_log(f"PIPELINE: Error: {item_state.error_message}")
                return item_state
            
            # Phase 4: Image generation with refinement loop
            final_decision = self._execute_phase4_with_review(item_state)
            
            # Handle final decision
            if final_decision == 'approve':
                self.save_final_output(item_state)
                item_state.current_phase = ProcessingPhase.COMPLETED
                item_state.completed_at = datetime.now()
            elif final_decision == 'skip':
                item_state.current_phase = ProcessingPhase.SKIPPED
                item_state.completed_at = datetime.now()
            else:
                item_state.current_phase = ProcessingPhase.FAILED
                item_state.completed_at = datetime.now()
            
            return item_state
            
        except Exception as e:
            print_log(f"ERROR: Failed to process {item['item_name']}: {e}")
            item_state.current_phase = ProcessingPhase.FAILED
            item_state.error_message = str(e)
            return item_state





    def _background_process_batch(self, items_batch: List[Dict]):
        """Background processing wrapper"""
        results = self.parallel_orchestrator.process_batch_during_review(items_batch)

        # Update pipeline state
        for state in results:
            self.pipeline_state.items_states[state.item_name] = state

    def _execute_phase4_with_review(self, item_state: ItemState) -> str:
        """Execute Phase 4 with iterative refinement loop"""

        max_iterations = self.config['processing']['max_iterations']
        refinement_notes = None

        for iteration in range(1, max_iterations + 1):
            print_log(f"\n[PHASE 4] Iteration {iteration}/{max_iterations}")

            # Generate image with proper 3-4 image references
            generated_path = self.phase4_generator.generate_image(
                item_state=item_state,        # ← Pass entire state (has all paths)
                iteration=iteration,
                refinement_notes=refinement_notes
            )

            if not generated_path:
                print_log(f"[PHASE 4] Generation failed at iteration {iteration}")
                if iteration < max_iterations:
                    print_log(f"[PHASE 4] Retrying...")
                    time.sleep(5)
                    continue
                else:
                    return 'reject'

            item_state.generated_image_path = generated_path
            item_state.iteration_count = iteration

            # Agent evaluation
            evaluation = self.phase4_generator.evaluate_image(
                generated_path=generated_path,
                item_name=item_state.item_name,
                background_type=item_state.background_type
            )

            item_state.agent_score = evaluation['overall_score']
            item_state.agent_reasoning = evaluation['reasoning']
            item_state.agent_recommendation = evaluation['recommendation'].lower()

            # Lines 1325-1360 - REPLACE WITH THIS
            decision, feedback = self.human_review.conduct_review(
                item_name=item_state.item_name,
                generated_path=generated_path,
                evaluation=evaluation,
                iteration=iteration
            )

            # ✅ CRITICAL VALIDATION LAYER
            valid_decisions = ['approve', 'reject', 'skip']
            if decision not in valid_decisions:
                print_log(f"\n[CRITICAL ERROR] Invalid decision '{decision}' received!")
                print_log(f"[CRITICAL ERROR] Valid options: {valid_decisions}")
                print_log(f"[CRITICAL ERROR] Forcing REJECT for safety.")
                decision = 'reject'
                feedback = f"System error: invalid decision '{decision}' auto-corrected"

            # ✅ DECISION TRACE LOGGING
            print_log(f"\n[DECISION TRACE] ====================================")
            print_log(f"[DECISION TRACE] User Decision: {decision.upper()}")
            print_log(f"[DECISION TRACE] Agent Recommended: {item_state.agent_recommendation.upper()}")
            print_log(f"[DECISION TRACE] Agent Score: {evaluation['overall_score']}/100")
            if feedback:
                print_log(f"[DECISION TRACE] Feedback: {feedback[:80]}...")
            print_log(f"[DECISION TRACE] ====================================")

            item_state.human_decision = decision
            item_state.human_feedback = feedback

            # Process decision with explicit logging
            if decision == 'approve':
                print_log(f"[ACTION] ✓ FINALIZING - Saving to final outputs")
                return 'approve'
                
            elif decision == 'skip':
                print_log(f"[ACTION] ⊗ SKIPPING - Moving to next item")
                return 'skip'
                
            elif decision == 'reject':
                if iteration < max_iterations:
                    print_log(f"[ACTION] ↻ REFINING - Iteration {iteration+1}/{max_iterations}")
                    
                    # Disagreement resolution
                    if item_state.agent_recommendation == 'approve':
                        print_log(f"[DISAGREEMENT] Agent approved but human rejected - analyzing...")
                        refinement_notes = self.disagreement_engine.analyze_disagreement(
                            item_name=item_state.item_name,
                            agent_recommendation=item_state.agent_recommendation,
                            human_decision=decision,
                            evaluation=evaluation,
                            background_type=item_state.background_type,
                            generated_path=generated_path
                        )
                    else:
                        refinement_notes = feedback if feedback else evaluation['reasoning']

                    print_log(f"[REFINEMENT] Instructions: {refinement_notes[:100]}...")
                    time.sleep(2)
                else:
                    print_log(f"[ACTION] ✗ FAILED - Max iterations ({max_iterations}) reached")
                    return 'reject'
            else:
                # Should never hit due to validation above
                print_log(f"[FATAL ERROR] Unknown decision state: {decision}")
                return 'reject'


    def save_final_output(self, item_state: ItemState):
        """Save approved image to final outputs organized by background"""
        background_folder = item_state.background_type.lower()
        output_dir = Path(self.config["paths"]["output_dir"]) / background_folder
        
        # ✅ ADD THIS LINE - Create folder if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', item_state.item_name)
        final_path = output_dir / f"{safe_name}.jpg"
        
        try:
            import shutil
            print_log(f"[SAVE] Copying from: {item_state.generated_image_path}")
            print_log(f"[SAVE] Destination: {final_path}")
            shutil.copy2(item_state.generated_image_path, final_path)
            print_log(f"[SAVE] ✓ Successfully saved to {final_path}")
        except Exception as e:
            print_log(f"[SAVE ERROR] Failed to save final output: {e}")
            import traceback
            traceback.print_exc()

    def _initialize_pipeline_state(self) -> PipelineState:
        """Initialize fresh pipeline state"""
        return PipelineState(
            current_item_index=0,
            items_states={},
            total_items=0,
            started_at=datetime.now(),
            checkpoint_count=0,
            disagreement_patterns=[],
            background_specific_issues={
                'PINK': [],
                'MARBLE': [],
                'PAISLEY': []
            }
        )

    def _print_summary(self):
        """Print execution summary"""
        completed = sum(1 for s in self.pipeline_state.items_states.values() 
                       if s.current_phase == ProcessingPhase.COMPLETED)
        failed = sum(1 for s in self.pipeline_state.items_states.values() 
                    if s.current_phase == ProcessingPhase.FAILED)
        skipped = sum(1 for s in self.pipeline_state.items_states.values() 
                     if s.current_phase == ProcessingPhase.SKIPPED)

        print_log(f"\nCompleted: {completed}")
        print_log(f"Failed: {failed}")
        print_log(f"Skipped: {skipped}")
        print_log(f"Total: {len(self.pipeline_state.items_states)}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Hybrid Agentic Image Generation Pipeline')
    parser.add_argument('--resume', action='store_true', help='Resume from latest checkpoint')
    parser.add_argument('--log-dir', type=str, default='logs', help='Directory for log files')
    parser.add_argument('--log-file', type=str, default=None, help='Custom log filename')
    args = parser.parse_args()

    # Initialize enhanced logging system
    logger = initialize_global_logger(log_dir=args.log_dir, log_filename=args.log_file)
    print_log("=" * 80)
    print_log("HYBRID AGENTIC PIPELINE - STARTING")
    print_log(f"Log Directory: {args.log_dir}")
    print_log(f"Log File: {logger.log_filepath}")
    print_log("=" * 80)

    # Initialize and run pipeline
    pipeline = HybridAgenticPipeline(CONFIG)

    try:
        pipeline.run(resume=args.resume)
    except KeyboardInterrupt:
        print_log("\n\n[INTERRUPT] Pipeline interrupted. Saving checkpoint...")
        pipeline.checkpoint_manager.save_checkpoint(
            pipeline.pipeline_state,
            "checkpoint_INTERRUPTED.pkl"
        )
        print_log("[INTERRUPT] Checkpoint saved. Resume with --resume flag")
        sys.exit(0)
    except Exception as e:
        print_log(f"\n\n[FATAL ERROR] {e}")
        traceback.print_exc()
        print_log("\nSaving emergency checkpoint...")
        pipeline.checkpoint_manager.save_checkpoint(
            pipeline.pipeline_state,
            "checkpoint_EMERGENCY.pkl"
        )
        sys.exit(1)
