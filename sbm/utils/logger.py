"""
Logging utilities for the SBM tool.

This module provides a centralized logging system for the SBM tool.
"""

import logging
import os
import sys
from datetime import datetime


def setup_logger(name=None, log_file=None, level=logging.INFO):
    """
    Set up and configure a logger instance.
    
    Args:
        name (str, optional): Logger name. Defaults to 'sbm'.
        log_file (str, optional): Path to log file. If None, a default path is used.
        level (int, optional): Logging level. Defaults to logging.INFO.
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger name if not provided
    if name is None:
        name = 'sbm'
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Add handlers only if not already added
    if not logger.handlers:
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Create file handler if a log file is specified or use default
        if log_file is None:
            # Create logs directory if it doesn't exist
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Default log file name with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(log_dir, f'sbm_{timestamp}.log')
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
