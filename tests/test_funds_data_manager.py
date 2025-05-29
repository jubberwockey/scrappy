import pytest
import pandas as pd
import numpy as np
import os
import tempfile
import sys
from unittest.mock import Mock, patch, mock_open

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrappy import FundsDataManager, DataValidationError


class TestFundsDataManager:
    """Test suite for FundsDataManager class."""
    
    @pytest.fixture
    def sample_funds_data(self):
        """Provide sample funds data."""
        return pd.DataFrame({
            'name': ['Fund A', 'Fund B', 'Fund C'],
            'TER': [0.5, 0.75, 1.0],
            'performance': [
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 10.0}],
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 15.0}],
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 8.0}]
            ],
            'risk': [
                [{'timeSpan': '1Y', 'volatility': 12.0, 'sharpeRatio': 0.8}],
                [{'timeSpan': '1Y', 'volatility': 15.0, 'sharpeRatio': 1.0}],
                [{'timeSpan': '1Y', 'volatility': 10.0, 'sharpeRatio': 0.6}]
            ]
        }, index=['DE000FUND001', 'DE000FUND002', 'DE000FUND003'])
    
    @pytest.fixture
    def sample_performance_data(self):
        """Provide sample performance data."""
        data = []
        isins = ['DE000FUND001', 'DE000FUND002']
        timespans = ['1Y', '3Y']
        
        for isin in isins:
            for timespan in timespans:
                data.append({
                    'isins': isin,
                    'timeSpan': timespan,
                    'performanceTimeSpanPct': np.random.uniform(5, 20),
                    'volatility': np.random.uniform(8, 18),
                    'sharpeRatio': np.random.uniform(0.5, 1.5)
                })
        
        df = pd.DataFrame(data)
        return df.set_index(['isins', 'timeSpan'])
    
    @pytest.fixture
    def sample_timeseries_data(self):
        """Provide sample timeseries data."""
        dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
        data = {
            'DE000FUND001': np.cumsum(np.random.randn(len(dates)) * 0.01) + 100,
            'DE000FUND002': np.cumsum(np.random.randn(len(dates)) * 0.01) + 100,
            'DE000FUND003': np.cumsum(np.random.randn(len(dates)) * 0.01) + 100
        }
        return pd.DataFrame(data, index=dates)
    
    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            funds_file = os.path.join(temp_dir, 'funds.csv')
            performance_file = os.path.join(temp_dir, 'performance.csv')
            timeseries_file = os.path.join(temp_dir, 'timeseries.csv')
            
            yield {
                'funds': funds_file,
                'performance': performance_file,
                'timeseries': timeseries_file
            }
    
    def test_init_empty(self):
        """Test initialization with no file paths."""
        manager = FundsDataManager()
        
        assert manager.funds_overview_path is None
        assert manager.performance_path is None
        assert manager.timeseries_path is None
        assert manager.funds_overview.empty
        assert manager.performance is None
        assert manager.timeseries is None
    
    def test_init_with_paths(self, temp_files):
        """Test initialization with file paths."""
        manager = FundsDataManager(
            funds_overview_path=temp_files['funds'],
            performance_path=temp_files['performance'],
            timeseries_path=temp_files['timeseries']
        )
        
        assert manager.funds_overview_path == temp_files['funds']
        assert manager.performance_path == temp_files['performance']
        assert manager.timeseries_path == temp_files['timeseries']
    
    def test_str_to_list(self):
        """Test string to list conversion."""
        manager = FundsDataManager()
        
        # Test valid list string
        result = manager._str_to_list("[1, 2, 3]")
        assert result == [1, 2, 3]
        
        # Test dictionary list string
        result = manager._str_to_list("[{'a': 1}, {'b': 2}]")
        assert result == [{'a': 1}, {'b': 2}]
    
    def test_load_data_nonexistent_files(self, temp_files):
        """Test loading data when files don't exist."""
        manager = FundsDataManager(
            funds_overview_path=temp_files['funds'],
            performance_path=temp_files['performance'],
            timeseries_path=temp_files['timeseries']
        )
        
        # Should not raise errors, just keep empty data
        assert manager.funds_overview.empty
        assert manager.performance is None
        assert manager.timeseries is None
    
    def test_load_data_existing_files(self, temp_files, sample_funds_data, 
                                    sample_performance_data, sample_timeseries_data):
        """Test loading data when files exist."""
        # Save sample data to files
        sample_funds_data.to_csv(temp_files['funds'])
        sample_performance_data.to_csv(temp_files['performance'])
        sample_timeseries_data.to_csv(temp_files['timeseries'])
        
        manager = FundsDataManager(
            funds_overview_path=temp_files['funds'],
            performance_path=temp_files['performance'],
            timeseries_path=temp_files['timeseries']
        )
        
        assert not manager.funds_overview.empty
        assert manager.performance is not None
        assert manager.timeseries is not None
        assert len(manager.funds_overview) == 3
        assert isinstance(manager.timeseries.index, pd.DatetimeIndex)
    
    def test_add_funds_data(self, sample_funds_data):
        """Test adding new funds data."""
        manager = FundsDataManager()
        
        # Add initial data
        manager.add_funds_data(sample_funds_data)
        assert len(manager.funds_overview) == 3
        
        # Add more data with overlap
        new_data = pd.DataFrame({
            'name': ['Fund D', 'Fund A Updated'],  # Fund A is duplicate
            'TER': [1.2, 0.6]
        }, index=['DE000FUND004', 'DE000FUND001'])
        
        manager.add_funds_data(new_data)
        assert len(manager.funds_overview) == 4  # 3 original + 1 new (duplicate removed)
        assert manager.funds_overview.loc['DE000FUND001', 'name'] == 'Fund A Updated'
    
    def test_add_timeseries_data(self, sample_timeseries_data):
        """Test adding timeseries data."""
        manager = FundsDataManager()
        
        # Add initial data
        manager.add_timeseries_data(sample_timeseries_data)
        assert manager.timeseries is not None
        assert len(manager.timeseries.columns) == 3
        
        # Add more data with overlap
        new_dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')
        new_data = pd.DataFrame({
            'DE000FUND001': np.random.randn(len(new_dates)) + 105,  # Overlap
            'DE000FUND004': np.random.randn(len(new_dates)) + 100   # New
        }, index=new_dates)
        
        manager.add_timeseries_data(new_data)
        assert len(manager.timeseries.columns) == 4  # 3 original + 1 new
        assert 'DE000FUND004' in manager.timeseries.columns
    
    def test_join_finanzen_zero_data_file_not_found(self):
        """Test joining finanzen zero data when file doesn't exist."""
        manager = FundsDataManager()
        
        # Should not raise error, just log warning
        manager.join_finanzen_zero_data('nonexistent_file.csv')
        
        # Data should remain unchanged
        assert manager.funds_overview.empty
    
    def test_join_finanzen_zero_data_success(self, sample_funds_data, temp_files):
        """Test successful joining of finanzen zero data."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Create mock finanzen zero data
        finanzen_data = pd.DataFrame({
            'ISIN': ['DE000FUND001', 'DE000FUND002', 'DE000FUND999'],
            'WKN': ['FUND01', 'FUND02', 'FUND99'],
            'Typ': ['ETF', 'Fund', 'ETF'],
            'Name': ['Fund A', 'Fund B', 'Fund Z'],
            'Sparplan': ['Ja', 'Nein', 'Ja']
        })
        
        finanzen_file = temp_files['funds'] + '_finanzen.csv'
        finanzen_data.to_csv(finanzen_file, sep=';', index=False)
        
        manager.join_finanzen_zero_data(finanzen_file)
        
        # Check that finanzen zero columns were added
        assert 'finanzen_zero' in manager.funds_overview.columns
        assert 'sparplan_finanzen_zero' in manager.funds_overview.columns
        
        # Check values
        assert manager.funds_overview.loc['DE000FUND001', 'finanzen_zero'] == True
        assert manager.funds_overview.loc['DE000FUND001', 'sparplan_finanzen_zero'] == True
        assert manager.funds_overview.loc['DE000FUND002', 'sparplan_finanzen_zero'] == False
        assert manager.funds_overview.loc['DE000FUND003', 'finanzen_zero'] == False
    
    def test_filter_funds_no_filter(self, sample_funds_data):
        """Test filtering funds without filter."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        result = manager.filter_funds()
        assert len(result) == 3
        assert result.equals(sample_funds_data)
    
    def test_filter_funds_by_index(self, sample_funds_data):
        """Test filtering funds by index (ISIN)."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Select single fund
        result = manager.filter_funds('DE000FUND001')
        assert len(result) == 1
        assert result.index[0] == 'DE000FUND001'
        
        # Select multiple funds
        result = manager.filter_funds(['DE000FUND001', 'DE000FUND002'])
        assert len(result) == 2
        
        # Select with non-existent ISIN
        result = manager.filter_funds(['DE000FUND001', 'DE000NONEXIST'])
        assert len(result) == 1  # Only existing one returned
    
    def test_filter_funds_by_column(self, sample_funds_data):
        """Test filtering funds by column values."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Select by name
        result = manager.filter_funds(['Fund A'], column='name')
        assert len(result) == 1
        assert result.iloc[0]['name'] == 'Fund A'
        
        # Select by TER range (this would need additional setup)
        # For now, just test the mechanism works
        result = manager.filter_funds(['Fund A', 'Fund B'], column='name')
        assert len(result) == 2
    
    def test_filter_funds_with_from_isins(self, sample_funds_data):
        """Test filtering funds with pre-filtering by ISINs."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Pre-filter to subset, then select from that
        result = manager.filter_funds(
            ['DE000FUND001'], 
            from_isins=['DE000FUND001', 'DE000FUND002']
        )
        assert len(result) == 1
        assert result.index[0] == 'DE000FUND001'
    
    def test_search_funds_by_pattern_index(self, sample_funds_data):
        """Test searching funds by index regex."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Search for funds with "FUND00" in ISIN
        result = manager.search_funds_by_pattern('FUND00')
        assert len(result) == 3  # All match
        
        # Search for specific pattern
        result = manager.search_funds_by_pattern('FUND001')
        assert len(result) == 1
        assert result.index[0] == 'DE000FUND001'
    
    def test_search_funds_by_pattern_column(self, sample_funds_data):
        """Test searching funds by column regex."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Search by name
        result = manager.search_funds_by_pattern('Fund [AB]', column='name')
        assert len(result) == 2  # Fund A and Fund B
    
    def test_extract_performance(self, sample_funds_data):
        """Test extracting performance data."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Get performance data for all funds
        result = manager.extract_performance()
        assert isinstance(result, pd.DataFrame)
        assert isinstance(result.index, pd.MultiIndex)
        assert 'performanceTimeSpanPct' in result.columns
        assert 'volatility' in result.columns
        
        # Get for specific ISINs
        result = manager.extract_performance(isins=['DE000FUND001'])
        assert len(result) == 1  # One ISIN, one timespan
    
    def test_extract_performance_single_column(self, sample_funds_data):
        """Test extracting single column performance data."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        # Get only performance data
        result = manager.extract_performance(columns=['performance'])
        assert 'performanceTimeSpanPct' in result.columns
        assert 'volatility' not in result.columns
    
    def test_select_timeseries(self, sample_timeseries_data):
        """Test selecting timeseries data."""
        manager = FundsDataManager()
        manager.add_timeseries_data(sample_timeseries_data)
        
        # Select existing columns
        result = manager.select_timeseries(['DE000FUND001', 'DE000FUND002'])
        assert len(result.columns) == 2
        assert 'DE000FUND001' in result.columns
        
        # Select with non-existent column
        result = manager.select_timeseries(['DE000FUND001', 'DE000NONEXIST'])
        assert len(result.columns) == 1
        assert 'DE000FUND001' in result.columns
    
    def test_select_timeseries_no_data(self):
        """Test selecting timeseries when no data exists."""
        manager = FundsDataManager()
        
        result = manager.select_timeseries(['DE000FUND001'])
        assert result.empty
    
    def test_save_funds_overview(self, temp_files, sample_funds_data):
        """Test saving funds overview."""
        manager = FundsDataManager(funds_overview_path=temp_files['funds'])
        manager.add_funds_data(sample_funds_data)
        
        # Save to default path
        manager.save_funds_overview()
        assert os.path.exists(temp_files['funds'])
        
        # Load and verify
        loaded = pd.read_csv(temp_files['funds'], index_col='isin')
        assert len(loaded) == 3
        assert 'name' in loaded.columns
    
    def test_save_funds_overview_custom_path(self, temp_files, sample_funds_data):
        """Test saving funds overview to custom path."""
        manager = FundsDataManager()
        manager.add_funds_data(sample_funds_data)
        
        custom_path = temp_files['funds'] + '_custom.csv'
        manager.save_funds_overview(custom_path)
        assert os.path.exists(custom_path)
    
    def test_save_performance(self, temp_files, sample_performance_data):
        """Test saving performance data."""
        manager = FundsDataManager(performance_path=temp_files['performance'])
        manager.performance = sample_performance_data
        
        manager.save_performance()
        assert os.path.exists(temp_files['performance'])
        
        # Load and verify
        loaded = pd.read_csv(temp_files['performance'], index_col=['isins', 'timeSpan'])
        assert len(loaded) > 0
    
    def test_save_timeseries(self, temp_files, sample_timeseries_data):
        """Test saving timeseries data."""
        manager = FundsDataManager(timeseries_path=temp_files['timeseries'])
        manager.add_timeseries_data(sample_timeseries_data)
        
        manager.save_timeseries()
        assert os.path.exists(temp_files['timeseries'])
        
        # Load and verify
        loaded = pd.read_csv(temp_files['timeseries'], index_col='x')
        assert len(loaded) > 0
        assert len(loaded.columns) == 3
    
    def test_save_empty_data(self, temp_files):
        """Test saving when data is empty."""
        manager = FundsDataManager(
            funds_overview_path=temp_files['funds'],
            performance_path=temp_files['performance'],
            timeseries_path=temp_files['timeseries']
        )
        
        # Should not create files for empty data
        manager.save_funds_overview()
        manager.save_performance()
        manager.save_timeseries()
        
        # Files should not be created
        assert not os.path.exists(temp_files['funds'])
        assert not os.path.exists(temp_files['performance'])
        assert not os.path.exists(temp_files['timeseries']) 