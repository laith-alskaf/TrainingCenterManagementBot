"""
Localization service for multilingual support.
"""
import json
import os
from typing import Dict, Optional
from pathlib import Path

from  domain.entities import Language


class LocalizationService:
    """
    Service for loading and retrieving localized strings.
    Supports Arabic (ar) and English (en).
    """
    
    def __init__(self, localization_dir: Optional[str] = None):
        """
        Initialize the localization service.
        
        Args:
            localization_dir: Path to directory containing localization JSON files
        """
        if localization_dir is None:
            # Default to the localization directory relative to this file
            localization_dir = os.path.dirname(__file__)
        
        self._dir = Path(localization_dir)
        self._cache: Dict[str, dict] = {}
        self._load_all()
    
    def _load_all(self) -> None:
        """Load all localization files."""
        for lang in Language:
            file_path = self._dir / f"{lang.value}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._cache[lang.value] = json.load(f)
    
    def get(
        self,
        key: str,
        language: Language = Language.ARABIC,
        **kwargs
    ) -> str:
        """
        Get a localized string by key.
        
        Args:
            key: Dot-separated key path (e.g., "welcome.greeting")
            language: Target language
            **kwargs: Format parameters for string interpolation
            
        Returns:
            Localized string, or the key if not found
        """
        strings = self._cache.get(language.value, {})
        
        # Navigate nested keys
        value = strings
        for part in key.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        
        if value is None:
            # Fallback to English
            if language != Language.ENGLISH:
                return self.get(key, Language.ENGLISH, **kwargs)
            return key
        
        # Format with provided kwargs
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value if isinstance(value, str) else str(value)
    
    def get_dict(
        self,
        key: str,
        language: Language = Language.ARABIC,
    ) -> dict:
        """
        Get a dictionary of localized strings.
        
        Args:
            key: Dot-separated key path
            language: Target language
            
        Returns:
            Dictionary of strings, or empty dict if not found
        """
        strings = self._cache.get(language.value, {})
        
        value = strings
        for part in key.split('.'):
            if isinstance(value, dict):
                value = value.get(part, {})
            else:
                return {}
        
        return value if isinstance(value, dict) else {}


# Global localization instance
_localization: Optional[LocalizationService] = None


def get_localization() -> LocalizationService:
    """Get the global localization service instance."""
    global _localization
    if _localization is None:
        localization_dir = os.path.join(
            os.path.dirname(__file__),
            'localization'
        )
        _localization = LocalizationService(localization_dir)
    return _localization


def t(key: str, language: Language = Language.ARABIC, **kwargs) -> str:
    """
    Shorthand for getting a localized string.
    
    Args:
        key: Dot-separated key path
        language: Target language
        **kwargs: Format parameters
        
    Returns:
        Localized string
    """
    return get_localization().get(key, language, **kwargs)
