import os
import warnings

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    warnings.warn("DEEPSEEK_API_KEY not set — FIM completion will fail until configured")