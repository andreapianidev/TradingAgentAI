"""
Supabase settings loader.
Fetches configuration from trading_settings table in Supabase.
Falls back to environment variables if Supabase is unavailable.
"""
import os
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SupabaseSettingsLoader:
    """Loads settings from Supabase trading_settings table."""

    # Mapping from Supabase setting_key to Settings class attribute
    SETTING_KEY_MAP = {
        'bot_active': 'BOT_ACTIVE',
        'paper_trading_enabled': 'PAPER_TRADING',
        'paper_trading_initial_balance': 'PAPER_TRADING_INITIAL_BALANCE',
        'target_symbols': 'TARGET_SYMBOLS',
        'timeframe': 'TIMEFRAME',
        'exchange': 'EXCHANGE',
        'alpaca_paper_trading': 'ALPACA_PAPER_TRADING',
        'max_leverage': 'MAX_LEVERAGE',
        'default_leverage': 'DEFAULT_LEVERAGE',
        'max_position_size_pct': 'MAX_POSITION_SIZE_PCT',
        'max_total_exposure_pct': 'MAX_TOTAL_EXPOSURE_PCT',
        'min_confidence_threshold': 'MIN_CONFIDENCE_THRESHOLD',
        'stop_loss_pct': 'STOP_LOSS_PCT',
        'take_profit_pct': 'TAKE_PROFIT_PCT',
        'enable_stop_loss': 'ENABLE_STOP_LOSS',
        'enable_take_profit': 'ENABLE_TAKE_PROFIT',
    }

    def __init__(self):
        self._client = None
        self._settings_cache: Dict[str, Any] = {}
        self._initialized = False

    def _get_client(self):
        """Lazy initialization of Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client, Client

                url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
                key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')

                if not url or not key:
                    logger.warning("Supabase credentials not found, using env vars only")
                    return None

                self._client = create_client(url, key)
                logger.info("Supabase client initialized successfully")
            except ImportError:
                logger.warning("supabase-py not installed, using env vars only")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                return None

        return self._client

    def load_settings(self) -> Dict[str, Any]:
        """
        Load all settings from Supabase trading_settings table.
        Returns a dictionary of setting_key -> parsed value.
        """
        if self._initialized:
            return self._settings_cache

        client = self._get_client()
        if not client:
            self._initialized = True
            return {}

        try:
            response = client.table('trading_settings').select('*').execute()

            if response.data:
                for row in response.data:
                    key = row.get('setting_key')
                    value = row.get('setting_value')

                    if key and value is not None:
                        # Parse JSON value
                        try:
                            parsed_value = json.loads(value) if isinstance(value, str) else value
                        except (json.JSONDecodeError, TypeError):
                            parsed_value = value

                        self._settings_cache[key] = parsed_value

                logger.info(f"Loaded {len(self._settings_cache)} settings from Supabase")
            else:
                logger.warning("No settings found in trading_settings table")

        except Exception as e:
            logger.error(f"Failed to load settings from Supabase: {e}")

        self._initialized = True
        return self._settings_cache

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a single setting value."""
        if not self._initialized:
            self.load_settings()
        return self._settings_cache.get(key, default)

    def get_env_overrides(self) -> Dict[str, str]:
        """
        Convert Supabase settings to environment variable format.
        Returns dict that can be used to override env vars.
        """
        if not self._initialized:
            self.load_settings()

        overrides = {}

        for supabase_key, env_key in self.SETTING_KEY_MAP.items():
            if supabase_key in self._settings_cache:
                value = self._settings_cache[supabase_key]

                # Convert to string for env var compatibility
                if isinstance(value, bool):
                    overrides[env_key] = str(value).lower()
                elif isinstance(value, list):
                    overrides[env_key] = ','.join(str(v) for v in value)
                else:
                    overrides[env_key] = str(value)

        return overrides

    def refresh(self) -> Dict[str, Any]:
        """Force refresh settings from Supabase."""
        self._initialized = False
        self._settings_cache = {}
        return self.load_settings()

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting in Supabase."""
        client = self._get_client()
        if not client:
            return False

        try:
            json_value = json.dumps(value)
            response = client.table('trading_settings').update({
                'setting_value': json_value
            }).eq('setting_key', key).execute()

            if response.data:
                self._settings_cache[key] = value
                return True

        except Exception as e:
            logger.error(f"Failed to update setting {key}: {e}")

        return False

    def update_last_run(self) -> bool:
        """Update last_run_timestamp to current time."""
        from datetime import datetime
        return self.update_setting('last_run_timestamp', datetime.utcnow().isoformat())


# Global singleton instance
supabase_settings = SupabaseSettingsLoader()


def load_supabase_settings() -> Dict[str, Any]:
    """Convenience function to load settings."""
    return supabase_settings.load_settings()


def get_env_overrides() -> Dict[str, str]:
    """Get settings as environment variable overrides."""
    return supabase_settings.get_env_overrides()
