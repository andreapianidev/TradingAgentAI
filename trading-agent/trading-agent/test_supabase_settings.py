#!/usr/bin/env python3
"""
Test script to verify Supabase settings are loaded correctly.
Run: python test_supabase_settings.py
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("TESTING SUPABASE SETTINGS LOADER")
print("=" * 60)

# Test 1: Check Supabase credentials
print("\n1. Checking Supabase credentials...")
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
print(f"   SUPABASE_URL: {'✓ Set' if supabase_url else '✗ Missing'}")
print(f"   SUPABASE_SERVICE_KEY: {'✓ Set' if supabase_key else '✗ Missing'}")

# Test 2: Load settings from Supabase
print("\n2. Loading settings from Supabase...")
try:
    from config.supabase_settings import supabase_settings, load_supabase_settings

    settings_data = load_supabase_settings()
    if settings_data:
        print(f"   ✓ Loaded {len(settings_data)} settings from Supabase:")
        for key, value in sorted(settings_data.items()):
            print(f"      - {key}: {value}")
    else:
        print("   ✗ No settings loaded from Supabase")
except Exception as e:
    print(f"   ✗ Error loading Supabase settings: {e}")

# Test 3: Load main Settings class
print("\n3. Loading main Settings class (with Supabase overrides)...")
try:
    from config.settings import settings

    print(f"   Using Supabase: {settings.is_using_supabase}")
    print(f"   BOT_ACTIVE: {getattr(settings, 'BOT_ACTIVE', 'N/A')}")
    print(f"   PAPER_TRADING: {settings.PAPER_TRADING}")
    print(f"   PAPER_TRADING_INITIAL_BALANCE: {settings.PAPER_TRADING_INITIAL_BALANCE}")
    print(f"   TARGET_SYMBOLS: {settings.TARGET_SYMBOLS}")
    print(f"   symbols_list: {settings.symbols_list}")
    print(f"   MAX_LEVERAGE: {settings.MAX_LEVERAGE}")
    print(f"   DEFAULT_LEVERAGE: {settings.DEFAULT_LEVERAGE}")
    print(f"   STOP_LOSS_PCT: {settings.STOP_LOSS_PCT}")
    print(f"   TAKE_PROFIT_PCT: {settings.TAKE_PROFIT_PCT}")
    print(f"   MIN_CONFIDENCE_THRESHOLD: {settings.MIN_CONFIDENCE_THRESHOLD}")

    # Show settings source
    sources = settings.get_settings_source()
    if sources:
        print(f"\n   Settings loaded from Supabase: {list(sources.keys())}")

    print("\n   ✓ Settings loaded successfully!")
except Exception as e:
    print(f"   ✗ Error loading Settings: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
