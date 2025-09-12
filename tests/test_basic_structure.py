"""
Basic structure tests that don't require external dependencies.
These tests verify that the classes can be imported and have the expected structure.
"""

import sys
import os
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_main_classes_import():
    """Test that all main classes can be imported."""
    from scrappy import (
        ScrapingConfig, DataScraper, FundsDataManager, 
        FundsAnalyzer, FundsVisualizer, Scrappy
    )
    
    # If we get here, imports worked
    assert ScrapingConfig is not None
    assert DataScraper is not None
    assert FundsDataManager is not None
    assert FundsAnalyzer is not None
    assert FundsVisualizer is not None
    assert Scrappy is not None


def test_exception_classes_import():
    """Test that custom exception classes can be imported."""
    from scrappy import (
        ScrapingError, DataValidationError, APILimitExceededError,
        NetworkError, DataNotFoundError
    )
    
    # Verify all exception classes exist
    assert ScrapingError is not None
    assert DataValidationError is not None
    assert APILimitExceededError is not None
    assert NetworkError is not None
    assert DataNotFoundError is not None


def test_exception_hierarchy():
    """Test that exception hierarchy is correct."""
    from scrappy import (
        ScrapingError, DataValidationError, APILimitExceededError,
        NetworkError, DataNotFoundError
    )
    
    # Test exception hierarchy
    assert issubclass(DataValidationError, ScrapingError)
    assert issubclass(APILimitExceededError, ScrapingError)
    assert issubclass(NetworkError, ScrapingError)
    assert issubclass(DataNotFoundError, ScrapingError)


@pytest.fixture
def scraping_config():
    """Provide a ScrapingConfig instance for tests."""
    from scrappy import ScrapingConfig
    return ScrapingConfig()


def test_scraping_config_attributes(scraping_config):
    """Test that ScrapingConfig has expected attributes."""
    # Check that key attributes exist
    assert hasattr(scraping_config, 'FILTER_CATEGORIES')
    assert hasattr(scraping_config, 'API_URLS')
    assert hasattr(scraping_config, 'ONVISTA_COLUMNS')
    assert hasattr(scraping_config, 'DEFAULT_BENCHMARKS')
    assert hasattr(scraping_config, 'FONDSDISCOUNT_HEADERS')
    assert hasattr(scraping_config, 'ONVISTA_HEADERS')
    assert hasattr(scraping_config, 'DEFAULT_BATCH_SIZE')
    assert hasattr(scraping_config, 'MAX_API_LIMIT')


def test_scraping_config_types(scraping_config):
    """Test that ScrapingConfig attributes have correct types."""
    assert isinstance(scraping_config.FILTER_CATEGORIES, dict)
    assert isinstance(scraping_config.API_URLS, dict)
    assert isinstance(scraping_config.ONVISTA_COLUMNS, dict)
    assert isinstance(scraping_config.DEFAULT_BENCHMARKS, list)
    assert isinstance(scraping_config.FONDSDISCOUNT_HEADERS, dict)
    assert isinstance(scraping_config.ONVISTA_HEADERS, dict)
    assert isinstance(scraping_config.DEFAULT_BATCH_SIZE, int)
    assert isinstance(scraping_config.MAX_API_LIMIT, int)


def test_scraping_config_initialization():
    """Test that ScrapingConfig can be initialized."""
    from scrappy import ScrapingConfig
    
    config = ScrapingConfig()
    assert config is not None


def test_data_scraper_initialization():
    """Test that DataScraper can be initialized."""
    from scrappy import ScrapingConfig, DataScraper
    
    config = ScrapingConfig()
    scraper = DataScraper(config)
    
    assert scraper is not None
    assert scraper.config is config


def test_data_scraper_default_config():
    """Test that DataScraper can be initialized with default config."""
    from scrappy import DataScraper
    
    scraper = DataScraper()
    assert scraper is not None
    assert scraper.config is not None


@pytest.fixture
def scrappy_instance():
    """Provide a Scrappy instance for tests."""
    from scrappy import Scrappy
    return Scrappy()


def test_scrappy_core_methods(scrappy_instance):
    """Test that Scrappy has expected core methods."""
    assert hasattr(scrappy_instance, 'search_funds_by_pattern')
    assert hasattr(scrappy_instance, 'filter_funds')
    assert hasattr(scrappy_instance, 'download_funds_overview')
    assert hasattr(scrappy_instance, 'download_timeseries')
    assert hasattr(scrappy_instance, 'extract_performance')
    assert hasattr(scrappy_instance, 'filter_top_performers')


def test_scrappy_visualization_methods(scrappy_instance):
    """Test that Scrappy has expected visualization methods."""
    assert hasattr(scrappy_instance, 'plot_timeseries')
    assert hasattr(scrappy_instance, 'plot_correlations')
    assert hasattr(scrappy_instance, 'plot_risk_return')
    assert hasattr(scrappy_instance, 'plot_benchmark_comparison')


def test_scrappy_analysis_methods(scrappy_instance):
    """Test that Scrappy has expected analysis methods."""
    assert hasattr(scrappy_instance, 'rank_funds')
    assert hasattr(scrappy_instance, 'rank_funds_by_strategy')


def test_scrappy_properties(scrappy_instance):
    """Test that Scrappy has expected properties."""
    assert hasattr(scrappy_instance, 'funds_overview')
    assert hasattr(scrappy_instance, 'performance')
    assert hasattr(scrappy_instance, 'ts')
    
    # Test that properties return expected types (or None if empty)
    assert scrappy_instance.funds_overview is not None
    assert scrappy_instance.ts is None or hasattr(scrappy_instance.ts, 'columns')


def test_scrappy_methods_are_callable(scrappy_instance):
    """Test that key Scrappy methods are callable."""
    assert callable(scrappy_instance.search_funds_by_pattern)
    assert callable(scrappy_instance.filter_funds)
    assert callable(scrappy_instance.download_funds_overview)
    assert callable(scrappy_instance.download_timeseries)
    assert callable(scrappy_instance.extract_performance)
    assert callable(scrappy_instance.filter_top_performers)
