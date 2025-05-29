import pytest
import pandas as pd
import requests
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrappy import (
    DataScraper, ScrapingConfig, NetworkError, APILimitExceededError, 
    DataValidationError, DataNotFoundError
)


class TestDataScraper:
    """Test suite for DataScraper class."""
    
    @pytest.fixture
    def config(self):
        """Provide a test configuration."""
        return ScrapingConfig()
    
    @pytest.fixture
    def scraper(self, config):
        """Provide a DataScraper instance."""
        return DataScraper(config)
    
    @pytest.fixture
    def mock_response_success(self):
        """Mock successful HTTP response."""
        mock = Mock()
        mock.status_code = 200
        mock.json.return_value = {
            'list': [
                {
                    'instrument.name': 'Test Fund',
                    'instrument.isin': 'DE000TEST001',
                    'fundsBaseData.ongoingCharges': 0.5,
                    'fundsEvaluation.morningstarRating': 4,
                    'fundsPerformanceList.list': [],
                    'fundsRiskList.list': []
                }
            ]
        }
        mock.text = "Success"
        return mock
    
    @pytest.fixture
    def mock_response_error(self):
        """Mock error HTTP response."""
        mock = Mock()
        mock.status_code = 500
        mock.text = "Internal Server Error"
        return mock
    
    @pytest.fixture
    def mock_response_rate_limit(self):
        """Mock rate limit HTTP response."""
        mock = Mock()
        mock.status_code = 429
        mock.text = "Too Many Requests"
        return mock
    
    def test_init_with_default_config(self):
        """Test DataScraper initialization with default config."""
        scraper = DataScraper()
        assert scraper.config is not None
        assert isinstance(scraper.config, ScrapingConfig)
        assert scraper.session is None
    
    def test_init_with_custom_config(self, config):
        """Test DataScraper initialization with custom config."""
        scraper = DataScraper(config)
        assert scraper.config is config
    
    def test_setup_headers(self, scraper):
        """Test header setup from configuration."""
        assert scraper.headers == scraper.config.FONDSDISCOUNT_HEADERS
        assert scraper.search_headers == scraper.config.ONVISTA_HEADERS
        assert scraper.api_url == scraper.config.API_URLS['fondsdiscount']
        assert scraper.search_api_url == scraper.config.API_URLS['onvista']
    
    def test_restart_session(self, scraper):
        """Test session restart functionality."""
        # Initially no session
        assert scraper.session is None
        
        # Start session
        session = scraper.restart_session()
        assert session is not None
        assert scraper.session is session
        
        # Restart session
        old_session = scraper.session
        new_session = scraper.restart_session()
        assert new_session is not old_session
        assert scraper.session is new_session
    
    @patch('requests.Session.request')
    def test_get_response_success(self, mock_request, scraper, mock_response_success):
        """Test successful HTTP response."""
        mock_request.return_value = mock_response_success
        
        response = scraper.get_response('http://test.com')
        
        assert response.status_code == 200
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_get_response_connection_error_retry_success(self, mock_request, scraper, mock_response_success):
        """Test connection error with successful retry."""
        # First call raises ConnectionError, second succeeds
        mock_request.side_effect = [requests.ConnectionError(), mock_response_success]
        
        response = scraper.get_response('http://test.com')
        
        assert response.status_code == 200
        assert mock_request.call_count == 2
    
    @patch('requests.Session.request')
    def test_get_response_connection_error_retry_fails(self, mock_request, scraper):
        """Test connection error with failed retry."""
        mock_request.side_effect = [requests.ConnectionError(), requests.ConnectionError()]
        
        with pytest.raises(NetworkError, match="Failed to connect"):
            scraper.get_response('http://test.com')
    
    @patch('requests.Session.request')
    def test_get_response_timeout_error(self, mock_request, scraper):
        """Test timeout error handling."""
        mock_request.side_effect = requests.Timeout()
        
        with pytest.raises(NetworkError, match="Request timeout"):
            scraper.get_response('http://test.com')
    
    @patch('requests.Session.request')
    def test_get_response_rate_limit_error(self, mock_request, scraper, mock_response_rate_limit):
        """Test rate limit error handling."""
        mock_request.return_value = mock_response_rate_limit
        
        with pytest.raises(APILimitExceededError, match="API rate limit exceeded"):
            scraper.get_response('http://test.com')
    
    @patch('requests.Session.request')
    def test_get_response_server_error(self, mock_request, scraper, mock_response_error):
        """Test server error handling."""
        mock_request.return_value = mock_response_error
        
        with pytest.raises(NetworkError, match="HTTP 500"):
            scraper.get_response('http://test.com')
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_success(self, mock_get_response, scraper, mock_response_success):
        """Test successful funds overview download."""
        mock_get_response.return_value = mock_response_success
        
        result = scraper.download_funds_overview(filter_ids=[5634], limit=10)
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'DE000TEST001' in result.index
        assert 'name' in result.columns
        assert 'TER' in result.columns
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_empty_response(self, mock_get_response, scraper):
        """Test funds overview download with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'list': []}
        mock_get_response.return_value = mock_response
        
        with pytest.raises(DataNotFoundError, match="No fund data could be retrieved"):
            scraper.download_funds_overview()
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_missing_list_key(self, mock_get_response, scraper):
        """Test funds overview download with missing list key."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'No data'}
        mock_get_response.return_value = mock_response
        
        with pytest.raises(DataNotFoundError):
            scraper.download_funds_overview()
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_missing_isin(self, mock_get_response, scraper):
        """Test funds overview download with missing ISIN column."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'list': [{'instrument.name': 'Test Fund'}]  # Missing ISIN
        }
        mock_get_response.return_value = mock_response
        
        with pytest.raises(DataValidationError, match="ISIN column missing"):
            scraper.download_funds_overview()
    
    def test_download_funds_overview_default_parameters(self, scraper):
        """Test that default parameters are used correctly."""
        with patch.object(scraper, 'get_response') as mock_get_response:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'list': [{
                    'instrument.isin': 'DE000TEST001',
                    'instrument.name': 'Test Fund'
                }]
            }
            mock_get_response.return_value = mock_response
            
            # Test with no parameters (should use defaults)
            result = scraper.download_funds_overview()
            
            # Verify the call was made with default config values
            assert mock_get_response.called
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_benchmark_mode(self, mock_get_response, scraper, mock_response_success):
        """Test funds overview download in benchmark mode."""
        mock_get_response.return_value = mock_response_success
        
        result = scraper.download_funds_overview(benchmark=True)
        
        assert isinstance(result, pd.DataFrame)
        # In benchmark mode, should still work but with different query parameters
        mock_get_response.assert_called()
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_etf_mode(self, mock_get_response, scraper, mock_response_success):
        """Test funds overview download in ETF mode."""
        mock_get_response.return_value = mock_response_success
        
        result = scraper.download_funds_overview(etf=True)
        
        assert isinstance(result, pd.DataFrame)
        mock_get_response.assert_called()
    
    @patch.object(DataScraper, 'get_response')
    def test_download_funds_overview_large_limit(self, mock_get_response, scraper, mock_response_success):
        """Test funds overview download with limit exceeding API maximum."""
        mock_get_response.return_value = mock_response_success
        
        # Test with limit > MAX_API_LIMIT (should split into multiple requests)
        result = scraper.download_funds_overview(limit=2000)
        
        assert isinstance(result, pd.DataFrame)
        # Should make multiple calls due to splitting
        assert mock_get_response.call_count >= 2
    
    def test_download_timeseries_string_input(self, scraper):
        """Test timeseries download with string ISIN input."""
        with patch.object(scraper, 'get_response') as mock_get_response, \
             patch.object(scraper, '_parse_timeseries_data') as mock_parse:
            
            mock_response = Mock()
            mock_response.text = "mock response text"
            mock_get_response.return_value = mock_response
            
            mock_df = pd.DataFrame({'DE000TEST001': [100, 101, 102]})
            mock_parse.return_value = (mock_df, [])
            
            result_df, skipped = scraper.download_timeseries('DE000TEST001')
            
            assert isinstance(result_df, pd.DataFrame)
            assert isinstance(skipped, list)
            mock_get_response.assert_called_once()
    
    def test_download_timeseries_list_input(self, scraper):
        """Test timeseries download with list of ISINs."""
        with patch.object(scraper, 'get_response') as mock_get_response, \
             patch.object(scraper, '_parse_timeseries_data') as mock_parse:
            
            mock_response = Mock()
            mock_response.text = "mock response text"
            mock_get_response.return_value = mock_response
            
            mock_df = pd.DataFrame({'DE000TEST001': [100, 101, 102]})
            mock_parse.return_value = (mock_df, [])
            
            isins = ['DE000TEST001', 'DE000TEST002']
            result_df, skipped = scraper.download_timeseries(isins)
            
            assert isinstance(result_df, pd.DataFrame)
            assert isinstance(skipped, list)
    
    def test_download_timeseries_network_error(self, scraper):
        """Test timeseries download with network error."""
        with patch.object(scraper, 'get_response') as mock_get_response:
            mock_get_response.side_effect = NetworkError("Network failed")
            
            with pytest.raises(NetworkError):
                scraper.download_timeseries('DE000TEST001')
    
    def test_download_timeseries_empty_result(self, scraper):
        """Test timeseries download with empty result."""
        with patch.object(scraper, 'get_response') as mock_get_response, \
             patch.object(scraper, '_parse_timeseries_data') as mock_parse:
            
            mock_response = Mock()
            mock_response.text = "mock response text"
            mock_get_response.return_value = mock_response
            
            # Return None for empty result
            mock_parse.return_value = (None, ['DE000TEST001'])
            
            result_df, skipped = scraper.download_timeseries('DE000TEST001')
            
            assert result_df.empty
            assert 'DE000TEST001' in skipped


class TestScrapingConfig:
    """Test suite for ScrapingConfig class."""
    
    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = ScrapingConfig()
        
        assert config.DEFAULT_FILTER_IDS == [5634, 5703, 5582]
        assert config.DEFAULT_BATCH_SIZE == 100
        assert config.DEFAULT_LIMIT == 100
        assert config.MAX_API_LIMIT == 1000
        
        assert 'fondsdiscount' in config.API_URLS
        assert 'onvista' in config.API_URLS
        
        assert len(config.ONVISTA_COLUMNS) > 0
        assert len(config.DEFAULT_BENCHMARKS) > 0
        assert len(config.FONDSDISCOUNT_HEADERS) > 0
        assert len(config.ONVISTA_HEADERS) > 0
    
    def test_column_mappings(self):
        """Test that column mappings are correctly defined."""
        config = ScrapingConfig()
        
        # Test some key mappings
        assert config.ONVISTA_COLUMNS['instrument.name'] == 'name'
        assert config.ONVISTA_COLUMNS['instrument.isin'] == 'isin'
        assert config.ONVISTA_COLUMNS['fundsBaseData.ongoingCharges'] == 'TER'
        
        # Ensure all values are unique (no duplicate target column names)
        values = list(config.ONVISTA_COLUMNS.values())
        assert len(values) == len(set(values))
    
    def test_benchmark_isins(self):
        """Test that benchmark ISINs are valid format."""
        config = ScrapingConfig()
        
        for isin in config.DEFAULT_BENCHMARKS:
            assert isinstance(isin, str)
            assert len(isin) == 12  # Standard ISIN length
            assert isin.isalnum()  # Should be alphanumeric 