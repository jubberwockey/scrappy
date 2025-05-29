"""
Basic structure tests that don't require external dependencies.
These tests verify that the classes can be imported and have the expected structure.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_imports():
    """Test that all main classes can be imported."""
    try:
        from scrappy import (
            ScrapingConfig, DataScraper, FundsDataManager, 
            FundsAnalyzer, FundsVisualizer, Scrappy
        )
        assert True  # If we get here, imports worked
    except ImportError as e:
        assert False, f"Import failed: {e}"


def test_exception_classes():
    """Test that custom exception classes are defined."""
    try:
        from scrappy import (
            ScrapingError, DataValidationError, APILimitExceededError,
            NetworkError, DataNotFoundError
        )
        
        # Test exception hierarchy
        assert issubclass(DataValidationError, ScrapingError)
        assert issubclass(APILimitExceededError, ScrapingError)
        assert issubclass(NetworkError, ScrapingError)
        assert issubclass(DataNotFoundError, ScrapingError)
        
    except ImportError as e:
        assert False, f"Exception import failed: {e}"


def test_scraping_config_structure():
    """Test that ScrapingConfig has expected attributes."""
    try:
        from scrappy import ScrapingConfig
        
        config = ScrapingConfig()
        
        # Check that key attributes exist
        assert hasattr(config, 'DEFAULT_FILTER_IDS')
        assert hasattr(config, 'API_URLS')
        assert hasattr(config, 'ONVISTA_COLUMNS')
        assert hasattr(config, 'DEFAULT_BENCHMARKS')
        assert hasattr(config, 'FONDSDISCOUNT_HEADERS')
        assert hasattr(config, 'ONVISTA_HEADERS')
        
        # Check types
        assert isinstance(config.DEFAULT_FILTER_IDS, list)
        assert isinstance(config.API_URLS, dict)
        assert isinstance(config.ONVISTA_COLUMNS, dict)
        assert isinstance(config.DEFAULT_BENCHMARKS, list)
        
    except Exception as e:
        assert False, f"ScrapingConfig test failed: {e}"


def test_class_initialization():
    """Test that classes can be initialized without external dependencies."""
    try:
        from scrappy import ScrapingConfig, DataScraper
        
        # Test config initialization
        config = ScrapingConfig()
        assert config is not None
        
        # Test scraper initialization
        scraper = DataScraper(config)
        assert scraper is not None
        assert scraper.config is config
        
    except Exception as e:
        assert False, f"Class initialization failed: {e}"


def test_method_existence():
    """Test that expected methods exist on classes."""
    try:
        from scrappy import Scrappy
        
        scrappy = Scrappy()
        
        # Test method names exist
        assert hasattr(scrappy, 'search_funds_by_pattern')
        assert hasattr(scrappy, 'filter_funds')
        assert hasattr(scrappy, 'download_funds_overview')
        assert hasattr(scrappy, 'download_timeseries')
        assert hasattr(scrappy, 'extract_performance')
        assert hasattr(scrappy, 'filter_top_performers')
        assert hasattr(scrappy, 'plot_timeseries')
        assert hasattr(scrappy, 'plot_correlations')
        assert hasattr(scrappy, 'plot_risk_return')
        assert hasattr(scrappy, 'plot_benchmark_comparison')
        assert hasattr(scrappy, 'rank_funds')
        assert hasattr(scrappy, 'rank_funds_by_strategy')
        
        # Test backward compatibility methods exist
        assert hasattr(scrappy, 'search_funds')
        assert hasattr(scrappy, 'select_funds')
        assert hasattr(scrappy, 'get_search_results')
        assert hasattr(scrappy, 'get_timeseries')
        
    except Exception as e:
        assert False, f"Method existence test failed: {e}"


if __name__ == "__main__":
    # Run tests manually if pytest is not available
    test_functions = [
        test_imports,
        test_exception_classes,
        test_scraping_config_structure,
        test_class_initialization,
        test_method_existence
    ]
    
    print("Running basic structure tests...")
    
    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
    
    print("Basic structure tests completed.") 