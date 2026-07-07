import os
import asyncio

async def initialize_system():
    """Initialize system directories and resources."""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # Initialize log files
    log_files = [
        "data/security_events.log",
        "data/secret_commands.log"
    ]
    for log_file in log_files:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("")
    
    print("System initialized.")

# For synchronous contexts
def initialize_system_sync():
    """Synchronous version of system initialization."""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    log_files = [
        "data/security_events.log",
        "data/secret_commands.log"
    ]
    for log_file in log_files:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("")
    
    print("System initialized.")