SECURITY_PROFILES = {
    "standard": {
        "auto_lock_minutes": 10,
        "clipboard_timeout": 30,
        "clipboard_security_level": "standard",
        "accelerate_on_detection": True,
        "stealth_mode": False
    },
    "enhanced": {
        "auto_lock_minutes": 3,
        "clipboard_timeout": 15,
        "clipboard_security_level": "secure",
        "accelerate_on_detection": True,
        "stealth_mode": False
    },
    "paranoid": {
        "auto_lock_minutes": 1,
        "clipboard_timeout": 5,
        "clipboard_security_level": "paranoid",
        "accelerate_on_detection": True,
        "stealth_mode": True
    }
}

def apply_profile(config, profile_name: str):
    if profile_name in SECURITY_PROFILES:
        for key, value in SECURITY_PROFILES[profile_name].items():
            config.set(key, value)
