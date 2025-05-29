import os
import requests
import dirtyjson
import re
import pandas as pd
import numpy as np
import datetime
from typing import List, Optional, Dict, Any, Union, Tuple
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import display
import logging

from .config import ScrapingConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Custom Exceptions
class ScrapingError(Exception):
    """Base exception for scraping operations."""
    pass


class DataValidationError(ScrapingError):
    """Raised when data validation fails."""
    pass


class APILimitExceededError(ScrapingError):
    """Raised when API rate limits are exceeded."""
    pass


class NetworkError(ScrapingError):
    """Raised when network operations fail."""
    pass


class DataNotFoundError(ScrapingError):
    """Raised when requested data is not found."""
    pass


class DataScraper:
    """Handles downloading of funds data."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.session = None
        self._setup_headers()
        
    def _setup_headers(self):
        """Setup HTTP headers for requests."""
        self.headers = self.config.FONDSDISCOUNT_HEADERS.copy()
        self.search_headers = self.config.ONVISTA_HEADERS.copy()
        self.api_url = self.config.API_URLS['fondsdiscount']
        self.search_api_url = self.config.API_URLS['onvista']
        self.data_template = self.config.FONDSDISCOUNT_DATA_TEMPLATE.copy()
    
    def restart_session(self) -> requests.Session:
        """Restart HTTP session."""
        if self.session is not None:
            self.session.close()
        self.session = requests.Session()
        return self.session
    
    def get_response(self, url: str, data: Optional[Dict] = None, 
                    params: Optional[Dict] = None, headers: Optional[Dict] = None, 
                    method: str = 'POST') -> requests.Response:
        """Get HTTP response with automatic retry on connection error."""
        if self.session is None:
            self.restart_session()
            
        try:
            response = self.session.request(method=method, url=url, data=data, 
                                          params=params, headers=headers)
        except requests.ConnectionError as e:
            logger.warning('ConnectionError, restarting session.')
            self.restart_session()
            try:
                response = self.session.request(method=method, url=url, data=data,
                                                params=params, headers=headers)
            except requests.ConnectionError as e:
                raise NetworkError(f"Failed to connect to {url}: {e}")
        except requests.Timeout as e:
            raise NetworkError(f"Request timeout for {url}: {e}")
        except requests.RequestException as e:
            raise NetworkError(f"Request failed for {url}: {e}")
        
        if response.status_code == 200:
            return response
        elif response.status_code == 429:
            raise APILimitExceededError(f"API rate limit exceeded for {url}")
        elif response.status_code >= 400:
            raise NetworkError(f"HTTP {response.status_code}: {response.text}")
        else:
            logger.warning(f"Unexpected status code {response.status_code} for {url}")
            return response
    
    def download_funds_overview(self, filter_ids: Optional[List[int]] = None, 
                             etf: bool = False, benchmark: bool = False, 
                             limit: int = None) -> pd.DataFrame:
        """
        Download funds overview data from the Onvista website.

        This function retrieves a data for funds based on specified filter criteria, 
        including sustainability categories, ETF status, and benchmark inclusion. 
        It pre-filters to investments with Ausgabeaufschlag < 7% and min investment < 10k.

        Parameters:
        ----------
        filter_ids : list of int, optional
            A list of filter IDs (onvista "Thema" filter) to specify categories of funds to download. 
            If None, defaults to the predefined filter IDs (sustainability, alternative energy, ecology).

        etf : bool, default=False
            If True, only includes funds that are exchange-traded funds (ETFs).

        benchmark : bool, default=False
            If True, only includes funds that are benchmarks.

        limit : int, optional
            The maximum number of funds to return. If None, defaults to 100.
            If >1000, splits requests by Ausgabeaufschlag (not ideal).

        Returns:
        -------
        pandas.DataFrame
            A DataFrame containing the downloaded funds data, including relevant columns 
            such as fund names, ISINs, TER (Total Expense Ratio), and other performance metrics.
        """
        if filter_ids is None:
            filter_ids = self.config.DEFAULT_FILTER_IDS
        if limit is None:
            limit = self.config.DEFAULT_LIMIT
            
        params = {
            'application': 'WEBSITE',
            'device': 'DESKTOP',
            'order': 'DESC',
            'page': '0',
            'perPage': '100',
            'queryParameters': '',
            'sort': 'performancePct1Y',
        }
        
        # Use configuration for column mappings
        cols = list(self.config.ONVISTA_COLUMNS.keys())
        colnames = list(self.config.ONVISTA_COLUMNS.values())
        
        if benchmark:
            # ignore other options if benchmark=True
            options = ['isExchangeTraded=true', 'idInstrumentBenchmark=16204403,4646272,83327,376508,376391,376376',
                       'idTypeReplication=2']
        else:
            options = []
            if etf:
                options.append('isExchangeTraded=true')
            
            if filter_ids is not None:
                if isinstance(filter_ids, int):
                    filter_ids = str(filter_ids)
                elif isinstance(filter_ids, list):
                    filter_ids = ','.join(map(str, filter_ids))
                options.append('idInvestmentFocus=' + filter_ids)
            
            options.append('minInitialInvestmentRange=0;10000')
        
        # Handle API limit of 1000 results: introduce additional filters
        if limit > self.config.MAX_API_LIMIT:
            params['perPage'] = self.config.MAX_API_LIMIT
            split_results_by = ['maxPctInitialFeeRange=0;4.9', 'maxPctInitialFeeRange=4.9;7']
        else:
            params['perPage'] = str(limit)
            split_results_by = ['maxPctInitialFeeRange=0;7']
        
        dfs = []
        for split in split_results_by:
            params['queryParameters'] = '&'.join(options + [split])
            
            try:
                response = self.get_response(url=self.search_api_url, params=params, 
                                           headers=self.search_headers, method='GET')
                
                response_data = response.json()
                if 'list' not in response_data:
                    logger.warning(f"No 'list' key in response for split: {split}")
                    continue
                    
                df = pd.json_normalize(response_data['list'])
                
                if df.empty:
                    logger.info(f"No data returned for split: {split}")
                    continue
                
                available_cols = [col for col in cols if col in df.columns]
                df = df[available_cols]

                opt_cols = ['fundsBaseData.minInitialInvestment', 'fundsBaseData.minFollowupInvestment']
                if etf or benchmark:
                    for opt_col in opt_cols:
                        df[opt_col] = np.nan
                
                # Map column names using configuration
                # column_mapping = {col: self.config.ONVISTA_COLUMNS[col] for col in available_cols}
                # df.rename(columns=column_mapping, inplace=True)
                df.rename(columns=self.config.ONVISTA_COLUMNS, inplace=True)
                
                df.set_index('isin', inplace=True)
                dfs.append(df)
                
            except (NetworkError, APILimitExceededError):
                raise  # Re-raise these specific errors
            except Exception as e:
                logger.error(f"Error processing split {split}: {e}")
                continue
        
        if dfs:
            df = pd.concat(dfs, axis=0)
            # Remove duplicates by index
            df = df[~df.index.duplicated(keep='last')]
            logger.info(f"Successfully downloaded {len(df)} funds")
            return df
        else:
            raise DataNotFoundError("No fund data could be retrieved")
    
    def download_timeseries(self, isins: Union[str, List[str]], 
                         batch_size: int = 100) -> Tuple[pd.DataFrame, List[str]]:
        """Download timeseries data from fondsdiscount website."""
        if isinstance(isins, str):
            isins = [isins]
        else:
            isins = list(isins)
        
        data = self.data_template.copy()
        
        dfs = []
        skipped_all = []
        batches, rem = divmod(len(isins), batch_size)
        
        for k in range(batches + 1):
            isins_batch = isins[k * batch_size:(k + 1) * batch_size]
            if len(isins_batch) > 0:
                data['isin'] = ','.join(isins_batch)
                response = self.get_response(url=self.api_url, data=data, 
                                           headers=self.headers, method='POST')
                
                if response:
                    df, skipped = self._parse_timeseries_data(response.text)
                    if df is not None:
                        dfs.append(df)
                        skipped_all.extend(skipped)
                    else:
                        logger.warning(f'No data for {isins_batch}')
                        skipped_all.extend(isins_batch)
                else:
                    logger.warning(f'No response for {isins_batch}')
                    skipped_all.extend(isins_batch)
        
        if dfs:
            return pd.concat(dfs, axis=1, join='outer'), skipped_all
        else:
            return pd.DataFrame(), skipped_all
    
    def _parse_timeseries_data(self, response_str: str) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """Parse HTTP response of timeseries into DataFrame."""
        logger.info("Parsing timeseries data...")
        reg = re.search(r"series : (\[[\s\S]+\])\s+\}\);", response_str)
        if reg is None:
            logger.error('Cannot parse response')
            return None, []
        
        json_str = reg.group(1)
        json_str = json_str.replace('Date.UTC', 'datetime.date')
        json_str = re.sub(r',0(\d)', r',\1', json_str)
        json_str = re.sub(r"data: \[?(\[[\s\S]+?\])?\]", r"data: '[\1]'", json_str)
        data = dirtyjson.loads(json_str)
        
        dfs = []
        skipped = []
        for i in data:
            try:
                # Use ast.literal_eval for safe evaluation
                import ast
                data_str = i['data']
                
                # Handle the case where data might be a string representation of a list
                if isinstance(data_str, str):
                    # Remove any extra quotes that might cause issues
                    data_str = data_str.strip("'\"")
                    X = ast.literal_eval(data_str)
                else:
                    # If it's already a list/array, use it directly
                    X = data_str if isinstance(data_str, list) else []
                    
            except (ValueError, SyntaxError, TypeError) as e:
                # Fallback to empty list if parsing fails
                logger.warning(f"Failed to parse data for {i.get('id', 'unknown')}: {e}, use eval")
                X = eval(i['data'])
            
            if len(X) > 0:
                df = pd.DataFrame.from_records(X, columns=['x', i['id']])
                df.rename(columns={'x': 'date'}, inplace=True)
                df.set_index('date', inplace=True)
                # Response data shifted by one month for some reason
                df.index = pd.to_datetime(df.index) + pd.DateOffset(months=1)
                dfs.append(df)
            else:
                skipped.append(i['id'])
        
        if len(skipped) > 0:
            logger.info(f"No data: {skipped}")
        
        if dfs:
            return pd.concat(dfs, axis=1, join='outer'), skipped
        else:
            return None, skipped


class FundsDataManager:
    """Manages funds data including loading, saving, and filtering operations."""
    
    def __init__(self, funds_overview_path: Optional[str] = None, 
                 performance_path: Optional[str] = None, 
                 timeseries_path: Optional[str] = None):
        self.funds_overview_path = funds_overview_path
        self.performance_path = performance_path
        self.timeseries_path = timeseries_path
        
        self.funds_overview = pd.DataFrame()
        self.performance = None
        self.timeseries = None
        
        self._load_data()
    
    def _str_to_list(self, s: str) -> List:
        """Convert string representation of list to actual list safely."""
        import ast
        try:
            # Use ast.literal_eval for safe evaluation of literals
            return ast.literal_eval(s)
        except (ValueError, SyntaxError) as e:
            logger.warning(f"Failed to parse list string '{s}': {e}")
            return []
    
    def _load_data(self):
        """Load data from files if paths are provided."""
        # Configuration for different data types
        data_configs = {
            'funds_overview': {
                'path_attr': 'funds_overview_path',
                'target_attr': 'funds_overview',
                'index_col': 'isin',
                'converters': {'performance': self._str_to_list, 'risk': self._str_to_list},
                'default_value': pd.DataFrame()
            },
            'performance': {
                'path_attr': 'performance_path',
                'target_attr': 'performance',
                'index_col': ['isins', 'timeSpan'],
                'converters': None,
                'default_value': None
            },
            'timeseries': {
                'path_attr': 'timeseries_path',
                'target_attr': 'timeseries',
                'index_col': 'date',
                'converters': None,
                'default_value': None,
                'post_process': lambda df: df.assign(**{df.index.name: pd.to_datetime(df.index)}).set_index(df.index.name)
            }
        }
        
        for data_type, config in data_configs.items():
            path = getattr(self, config['path_attr'])
            if path and os.path.exists(path):
                try:
                    df = pd.read_csv(
                        path,
                        index_col=config['index_col'],
                        converters=config.get('converters')
                    )
                    
                    # Apply post-processing if defined
                    if 'post_process' in config:
                        df = config['post_process'](df)
                    
                    setattr(self, config['target_attr'], df)
                    logger.info(f"Loaded {data_type} data from {path}")
                    
                except Exception as e:
                    logger.error(f"Failed to load {data_type} from {path}: {e}")
                    setattr(self, config['target_attr'], config['default_value'])
            else:
                setattr(self, config['target_attr'], config['default_value'])
    
    def add_funds_data(self, new_data: pd.DataFrame):
        """Add new funds data to existing overview."""
        self.funds_overview = pd.concat([self.funds_overview, new_data], axis=0)
        self.funds_overview = self.funds_overview[~self.funds_overview.index.duplicated(keep='last')]
    
    def add_timeseries_data(self, new_data: pd.DataFrame):
        """Add new timeseries data."""
        if self.timeseries is None:
            self.timeseries = new_data
        else:
            # Drop existing columns that are being updated
            self.timeseries = self.timeseries.drop(new_data.columns, axis=1, errors='ignore')
            self.timeseries = self.timeseries.combine_first(new_data)
    
    def join_finanzen_zero_data(self, filename: str = 'data/downloadable-instruments.csv'):
        """Join finanzen.net tradeable funds data."""
        if not os.path.exists(filename):
            logger.warning(f"Skip finanzen.net: '{filename}' not found")
            return
        
        df = pd.read_csv(filename, sep=';')
        df.index = df['ISIN']
        df['finanzen_zero'] = True
        df = df.rename(columns={'Sparplan': 'sparplan_finanzen_zero'}).drop(
            columns=['ISIN', 'WKN', 'Typ', 'Name']
        )
        df['sparplan_finanzen_zero'] = df['sparplan_finanzen_zero'] == 'Ja'
        
        self.funds_overview = self.funds_overview.drop(
            columns=['finanzen_zero', 'sparplan_finanzen_zero'], errors='ignore'
        ).join(df, how='left')
        self.funds_overview['finanzen_zero'] = self.funds_overview['finanzen_zero'].fillna(False)
    
    def filter_funds(self, conditions: Optional[Dict[str, Any]] = None, 
                    isins: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Filter funds based on multiple conditions with support for regex patterns.
        
        Parameters
        ----------
        conditions : dict, optional
            Dictionary where keys are column names and values are conditions:
            - List: filters using isin() (e.g., ['US', 'EU'])  
            - String with operator: mathematical condition (e.g., '<5', '>=10', '==True')
            - String with 'regex:' prefix: regex pattern (e.g., 'regex:ESG|Sustainable')
            - Direct value: equality filter
            - For index column, use 'index' as key for ISIN filterig
            Example: {'TER': '<1.0', 'name': 'regex:ESG|Sustainable', 'region': ['Europe', 'USA']}
        
        isins : list of str, optional
            Initial list of ISINs to filter from before applying conditions
            
        Returns
        -------
        pandas.DataFrame
            Filtered funds dataframe
        """
        # Start with base dataset
        if isins is None:
            funds = self.funds_overview.copy()
        else:
            # Filter to only include the specified ISINs
            available_isins = self.funds_overview.index.intersection(isins)
            if len(available_isins) < len(isins):
                missing = set(isins) - set(available_isins)
                logger.warning(f"ISINs not found: {missing}")
            funds = self.funds_overview.loc[available_isins].copy()
        
        # Return early if no conditions specified
        if conditions is None:
            return funds
        
        # Apply each condition consecutively
        for column, condition in conditions.items():
            if column not in funds.columns:
                logger.warning(f"Column '{column}' not found in funds data")
                continue
                
            # Handle different condition types
            if isinstance(condition, list):
                # List condition: use isin()
                mask = funds[column].isin(condition)
                
            elif isinstance(condition, str) and condition.startswith('regex:'):
                # Regex condition: extract pattern and apply
                regex_pattern = condition[6:]  # Remove 'regex:' prefix
                try:
                    mask = funds[column].str.contains(regex_pattern, regex=True, na=False)
                except Exception as e:
                    logger.warning(f"Invalid regex pattern '{regex_pattern}' for column '{column}': {e}")
                    continue
                    
            elif isinstance(condition, str) and any(condition.startswith(op) for op in ['<', '>', '=', '!']):
                # Mathematical condition: parse operator and value
                if condition.startswith('<='):
                    op, value = '<=', condition[2:]
                elif condition.startswith('>='):
                    op, value = '>=', condition[2:]
                elif condition.startswith('!='):
                    op, value = '!=', condition[2:]
                elif condition.startswith('=='):
                    op, value = '==', condition[2:]
                elif condition.startswith('<'):
                    op, value = '<', condition[1:]
                elif condition.startswith('>'):
                    op, value = '>', condition[1:]
                elif condition.startswith('='):
                    op, value = '==', condition[1:]
                else:
                    logger.warning(f"Unrecognized operator in condition: {condition}")
                    continue
                
                # Convert value to appropriate type
                try:
                    # Try to convert to float first
                    if '.' in value or 'e' in value.lower():
                        parsed_value = float(value)
                    elif value.lower() in ['true', 'false']:
                        parsed_value = value.lower() == 'true'
                    elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                        parsed_value = int(value)
                    else:
                        parsed_value = value  # Keep as string
                        
                except ValueError:
                    parsed_value = value  # Fallback to string
                
                # Apply condition
                if op == '<':
                    mask = funds[column] < parsed_value
                elif op == '<=':
                    mask = funds[column] <= parsed_value
                elif op == '>':
                    mask = funds[column] > parsed_value
                elif op == '>=':
                    mask = funds[column] >= parsed_value
                elif op == '==':
                    mask = funds[column] == parsed_value
                elif op == '!=':
                    mask = funds[column] != parsed_value
                    
            else:
                # Direct value: equality filter
                mask = funds[column] == condition
            
            # Apply the mask
            funds = funds[mask]
            logger.info(f"After filtering {column} with {condition}: {len(funds)} funds remaining")
        
        return funds
    
    def search_funds_by_pattern(self, regex_str: str, column: str = 'index') -> pd.DataFrame:
        """Search funds using regex."""
        if column == 'index':
            return self.funds_overview.filter(regex=regex_str, axis=0)
        else:
            return self.funds_overview.loc[
                self.funds_overview[column].str.contains(regex_str, regex=True), :
            ]
    
    def extract_performance(self, isins: Optional[List[str]] = None, 
                           columns: List[str] = ['performance', 'risk'], 
                           transpose: bool = False, dropna: bool = False) -> pd.DataFrame:
        """Extract and format performance data."""
        merge = len(columns) == 2
        
        if isins is None:
            isins = list(self.filter_funds().index)
        
        found_isins = []
        dfs = []
        
        for isin in isins:
            fund = self.filter_funds(isins=[isin])
            if len(fund) > 0:
                subdfs = [pd.DataFrame(fund.loc[isin, c]).set_index('timeSpan') for c in columns]
                if merge:
                    subdfs[1].rename({'nameTimeSpan': 'nameTimeSpan1'}, axis=1, inplace=True)
                    df = pd.concat(subdfs, axis=1, copy=False)
                    df['nameTimeSpan'] = df['nameTimeSpan'].fillna(subdfs[1]['nameTimeSpan1'])
                    df.drop('nameTimeSpan1', axis=1, inplace=True)
                else:
                    df = subdfs[0]
                
                if transpose:
                    df = df.T
                
                found_isins.append(isin)
                dfs.append(df)
        
        if dfs:
            self.performance = pd.concat(dfs, keys=found_isins)
            self.performance.index.rename('isins', level=0, inplace=True)
            if dropna:
                self.performance.dropna(thresh=2, inplace=True)
            return self.performance
        else:
            return pd.DataFrame()
    
    def select_timeseries(self, columns: List[str]) -> pd.DataFrame:
        """Select timeseries for specific ISINs."""
        if self.timeseries is None:
            logger.warning("No timeseries data available")
            return pd.DataFrame()
        
        skipped = []
        cols = [i for i in columns if i in self.timeseries.columns or skipped.append(i)]
        
        if skipped:
            logger.warning(f'Not in timeseries: {skipped}')
        
        return self.timeseries[cols] if cols else pd.DataFrame()
    
    def save_funds_overview(self, filename: Optional[str] = None):
        """Save funds overview to CSV."""
        filename = filename or self.funds_overview_path
        if filename and not self.funds_overview.empty:
            self.funds_overview.to_csv(filename)
    
    def save_performance(self, filename: Optional[str] = None):
        """Save performance data to CSV."""
        filename = filename or self.performance_path
        if filename and self.performance is not None:
            self.performance.to_csv(filename)
    
    def save_timeseries(self, filename: Optional[str] = None):
        """Save timeseries data to CSV."""
        filename = filename or self.timeseries_path
        if filename and self.timeseries is not None:
            self.timeseries.to_csv(filename)


class FundsAnalyzer:
    """Analyzes funds performance and provides recommendations."""
    
    def __init__(self, data_manager: FundsDataManager):
        self.data_manager = data_manager
        
        # Default ranking strategies
        self.strategies = {
            'balanced': {
                'performanceTimeSpanPct': 1.0,
                'sharpeRatio': 2.0,
                'volatility': -0.7,
                'maxDrawdown': -1.0,
                'TER': -0.8
            },
            'growth': {
                'performanceTimeSpanPct': 2.0,
                'sharpeRatio': 1.0,
                'volatility': -0.3,
                'maxDrawdown': -0.5,
                'TER': -0.7
            },
            'conservative': {
                'performanceTimeSpanPct': 0.5,
                'sharpeRatio': 1.0,
                'volatility': -1.5,
                'maxDrawdown': -2.0,
                'TER': -0.7
            },
            'long_term': {
                'performanceTimeSpanPct': 1.2,
                'sharpeRatio': 1.5,
                'volatility': -0.4,
                'maxDrawdown': -0.7,
                'TER': -2.0
            },
            'short_term': {
                'performanceTimeSpanPct': 1.5,
                'sharpeRatio': 1.2,
                'volatility': -0.8,
                'maxDrawdown': -1.0,
                'TER': -0.5
            }
        }

    
    def calculate_risk_return_metrics(self, timespan: str = '1Y', 
                                    isins: Optional[List[str]] = None) -> pd.DataFrame:
        """Calculate risk-return metrics for funds."""
        if isins is None:
            funds_df = self.data_manager.funds_overview
        else:
            funds_df = self.data_manager.filter_funds(isins=isins)
        
        if funds_df.empty:
            logger.warning("No fund data available for analysis.")
            return pd.DataFrame()
        
        risk_return_data = pd.DataFrame()
        
        for isin in funds_df.index:
            if 'performance' not in funds_df.columns or 'risk' not in funds_df.columns:
                continue
            
            if not isinstance(funds_df.loc[isin, 'performance'], list) or \
               not isinstance(funds_df.loc[isin, 'risk'], list):
                continue
            
            # Extract performance data for this timespan
            perf_data = next((item for item in funds_df.loc[isin, 'performance'] 
                            if item['timeSpan'] == timespan), None)
            
            # Extract risk data for this timespan
            risk_data = next((item for item in funds_df.loc[isin, 'risk'] 
                            if item['timeSpan'] == timespan), None)
            
            if perf_data is None or risk_data is None:
                continue
            
            risk_return_data.at[isin, 'return'] = perf_data.get('performanceTimeSpanPct', np.nan)
            risk_return_data.at[isin, 'volatility'] = risk_data.get('volatility', np.nan)
            risk_return_data.at[isin, 'sharpe'] = risk_data.get('sharpeRatio', np.nan)
            
            if 'name' in funds_df.columns:
                risk_return_data.at[isin, 'name'] = funds_df.at[isin, 'name']
            else:
                risk_return_data.at[isin, 'name'] = isin
        
        # Only drop rows if we have data to check
        if not risk_return_data.empty and 'return' in risk_return_data.columns and 'volatility' in risk_return_data.columns:
            return risk_return_data.dropna(subset=['return', 'volatility'])
        else:
            logger.warning("No valid risk-return data found for the specified timespan.")
            return pd.DataFrame()
    
    def _extract_ranking_metrics(self, funds_df: pd.DataFrame, timespan: str) -> pd.DataFrame:
        """Extract performance and risk metrics for ranking."""
        result_df = pd.DataFrame(index=funds_df.index)
        
        # Try to use pre-extracted performance data first
        if (self.data_manager.performance is not None and 
            not self.data_manager.performance.empty):
            
            logger.info("Using pre-extracted performance data for ranking")
            
            # Filter performance data for the specified timespan and available funds
            try:
                available_isins = funds_df.index.intersection(
                    self.data_manager.performance.index.get_level_values('isins')
                )
                
                if len(available_isins) > 0:
                    perf_data = self.data_manager.performance.loc[
                        (available_isins, timespan), :
                    ].copy()
                    
                    # Reset index to use ISIN as index
                    perf_data.reset_index(level='timeSpan', drop=True, inplace=True)
                    
                    # Add fund names and TER from funds_df
                    for isin in perf_data.index:
                        if 'name' in funds_df.columns:
                            perf_data.at[isin, 'name'] = funds_df.at[isin, 'name']
                        if 'TER' in funds_df.columns:
                            perf_data.at[isin, 'TER'] = funds_df.at[isin, 'TER']
                    
                    return perf_data
                    
            except (KeyError, IndexError) as e:
                logger.warning(f"Could not use pre-extracted performance data: {e}")
        
        # Fallback to extracting from funds_df columns
        logger.info("Extracting performance data from funds overview")
        
        for isin in funds_df.index:
            # Check if performance and risk columns exist
            if 'performance' not in funds_df.columns or 'risk' not in funds_df.columns:
                continue
                
            # Check if the columns are lists/arrays and not missing
            if (not isinstance(funds_df.loc[isin, 'performance'], list) or 
                not isinstance(funds_df.loc[isin, 'risk'], list)):
                continue
            
            try:
                # Extract performance data for this timespan
                perf_data = next((item for item in funds_df.loc[isin, 'performance'] 
                                if item.get('timeSpan') == timespan), None)
                
                # Extract risk data for this timespan
                risk_data = next((item for item in funds_df.loc[isin, 'risk'] 
                                if item.get('timeSpan') == timespan), None)
                
                # Skip if data for this timespan is missing
                if perf_data is None or risk_data is None:
                    continue
                
                # Add performance data
                for k, v in perf_data.items():
                    if k not in ['timeSpan', 'nameTimeSpan'] and v is not None:
                        result_df.at[isin, k] = v
                
                # Add risk data
                for k, v in risk_data.items():
                    if k not in ['timeSpan', 'nameTimeSpan'] and v is not None:
                        result_df.at[isin, k] = v
                
                # Add fund name and TER
                if 'name' in funds_df.columns:
                    result_df.at[isin, 'name'] = funds_df.at[isin, 'name']
                if 'TER' in funds_df.columns:
                    result_df.at[isin, 'TER'] = funds_df.at[isin, 'TER']
                    
            except Exception as e:
                logger.warning(f"Error extracting metrics for {isin}: {e}")
                continue
        
        return result_df
    

    
    def _calculate_ranking_scores(self, result_df: pd.DataFrame, 
                                 criteria: Dict[str, float]) -> pd.DataFrame:
        """Calculate ranking scores based on criteria weights."""
        result_df['score'] = 0
        
        for criterion, weight in criteria.items():
            # Skip if the criterion doesn't exist or all values are NaN
            if criterion not in result_df.columns or result_df[criterion].isna().all():
                logger.warning(f"Criterion '{criterion}' not available for scoring")
                continue
                
            # Fill NaN values with the median for scoring purposes
            # column_for_calc = result_df[criterion].fillna(result_df[criterion].median())
            column_for_calc = result_df[criterion]
            
            # Get min and max values for normalization
            min_val = column_for_calc.min()
            max_val = column_for_calc.max()
            
            # Skip normalization if min and max are the same (no variation)
            if max_val == min_val:
                logger.warning(f"No variation in criterion '{criterion}', skipping")
                continue
                
            # Normalize values based on whether higher or lower is better
            if weight > 0:  # Higher is better (e.g., performance, Sharpe ratio)
                normalized_score = weight * (column_for_calc - min_val) / (max_val - min_val)
            else:  # Lower is better (e.g., volatility, TER)
                normalized_score = abs(weight) * (max_val - column_for_calc) / (max_val - min_val)
                
            result_df['score'] += normalized_score
        
        return result_df

    def rank_funds(self, criteria: Optional[Dict[str, float]] = None, 
                   timespan: str = '1Y', isins: Optional[List[str]] = None, 
                   limit: int = 10) -> pd.DataFrame:
        """
        Rank funds based on different performance and risk criteria.
        
        Parameters
        ----------
        criteria : dict, optional
            Dictionary of criteria and weights for ranking.
            Example: {'performanceTimeSpanPct': 1, 'sharpeRatio': 2, 'volatility': -1, 'TER': -1}
            Positive weights prioritize higher values, negative weights prioritize lower values.
            If None, uses balanced criteria.
        
        timespan : str, default='1Y'
            Time period for evaluation ('1M', '3M', '1Y', '3Y', '5Y', '10Y')
            
        isins : list of str, optional
            List of ISINs to limit ranking to. If provided, only these funds will be ranked.
        
        limit : int, default=10
            Maximum number of top-ranked funds to return
        
        Returns
        -------
        pandas.DataFrame
            Ranked funds with scores and criteria values
        """
        # Default criteria if none provided
        if criteria is None:
            criteria = self.strategies['balanced'].copy()
            logger.info("Using default balanced criteria for ranking")
        
        # Start with specified ISINs or all funds
        if isins is not None:
            funds_df = self.data_manager.filter_funds(isins=isins)
            if funds_df.empty:
                logger.warning("No valid ISINs found for ranking")
                return pd.DataFrame()
        else:
            funds_df = self.data_manager.funds_overview.copy()
        
        if funds_df.empty:
            logger.warning("No funds available for ranking")
            return pd.DataFrame()
        
        # Extract performance and risk metrics
        result_df = self._extract_ranking_metrics(funds_df, timespan)
        
        if result_df.empty:
            logger.warning(f"No funds with valid data for timespan {timespan}")
            return pd.DataFrame()
        
        result_df = self._calculate_ranking_scores(result_df, criteria)

        result_df.sort_values('score', ascending=False, inplace=True)
        result_df = result_df.head(limit)
        
        # Return funds with relevant columns
        columns_to_include = ['name'] if 'name' in result_df.columns else []
        columns_to_include += [c for c in criteria.keys() if c in result_df.columns] + ['score']
        
        if not columns_to_include:
            return pd.DataFrame()
        
        logger.info(f"Ranked {len(result_df)} funds using criteria: {list(criteria.keys())}")
        return result_df[columns_to_include]
        
    def rank_funds_by_strategy(self, strategy: str, timespan: str = '3Y', 
                              isins: Optional[List[str]] = None, 
                              limit: int = 10) -> pd.DataFrame:
        """
        Rank funds using predefined investment strategies.
        
        Parameters
        ----------
        strategy : str
            Strategy name ('balanced', 'growth', 'conservative', 'long_term', 'short_term')
        timespan : str, default='3Y'
            Time period for evaluation
        isins : list of str, optional
            List of ISINs to limit ranking to. If provided, only these funds will be ranked.
        limit : int, default=10
            Maximum number of top-ranked funds to return
        
        Returns
        -------
        pandas.DataFrame
            Ranked funds for the specified strategy
        """
        if strategy not in self.strategies:
            available_strategies = list(self.strategies.keys())
            raise ValueError(f"Unknown strategy '{strategy}'. Available: {available_strategies}")
        
        # Set strategy-specific defaults for timespan
        strategy_defaults = {
            'long_term': {'timespan': '5Y'},
            'short_term': {'timespan': '1Y'}
        }
        
        # Use strategy-specific timespan if not overridden
        if strategy in strategy_defaults and 'timespan' in strategy_defaults[strategy]:
            timespan = strategy_defaults[strategy]['timespan']
        
        # Get strategy criteria
        criteria = self.strategies[strategy].copy()
        logger.info(f"Using {strategy} strategy for ranking")
        
        return self.rank_funds(
            criteria=criteria,
            timespan=timespan,
            isins=isins,
            limit=limit
        )


class FundsVisualizer:
    """Creates visualizations for funds analysis."""
    
    def __init__(self, data_manager: FundsDataManager, analyzer: FundsAnalyzer):
        self.data_manager = data_manager
        self.analyzer = analyzer
    
    def plot_timeseries(self, columns: Optional[List[str]] = None, 
                       transform: Optional[Union[str, callable]] = None, 
                       legend: bool = False, name_column: Optional[str] = None,
                       title: str = "Fund Performance Over Time"):
        """Plot timeseries with optional transformation and normalization."""
        if columns is not None:
            if isinstance(columns, str):
                columns = [columns]
            ts = self.data_manager.select_timeseries(columns)
        else:
            ts = self.data_manager.timeseries
        
        if ts is None or ts.empty:
            logger.warning("No timeseries data available for plotting")
            return
        
        if name_column is not None:
            try:
                ts.columns = self.data_manager.funds_overview.loc[ts.columns, name_column]
            except KeyError:
                ts.columns = [self.data_manager.funds_overview[name_column].get(i, i) 
                            for i in ts.columns]
        
        if transform is not None:
            if isinstance(transform, str):
                if transform == 'yesterday':
                    date = datetime.date.today() - pd.tseries.offsets.BusinessDay(1)
                else:
                    date = transform
                
                # Convert date string to datetime if needed
                if isinstance(date, str):
                    date = pd.to_datetime(date)
                                
                transform_func = lambda s: s / s.loc[date] * 100
            else:
                transform_func = transform
            
            ts = ts.interpolate('time').apply(transform_func, result_type=None)
        
        # Convert to long format for plotly
        ts_long = ts.reset_index().melt(id_vars=ts.index.name, 
                                       var_name='Fund', value_name='Value').dropna()
        
        fig = px.line(ts_long, x=ts.index.name, y='Value', color='Fund', title=title)
        fig.update_layout(showlegend=legend)
        fig.show()
    
    def plot_correlations(self, isins: Optional[List[str]] = None, 
                         min_periods: int = 30, method: str = 'pearson',
                         title: str = 'Fund Return Correlations'):
        """Plot correlation matrix of fund returns."""
        if isins is not None:
            ts_data = self.data_manager.select_timeseries(isins)
        else:
            ts_data = self.data_manager.timeseries
        
        if ts_data is None or ts_data.empty:
            logger.warning("No timeseries data available for correlation analysis.")
            return
        
        # Calculate daily returns
        returns = ts_data.pct_change(fill_method=None).dropna()
        
        # Compute correlation matrix
        corr_matrix = returns.corr(method=method, min_periods=min_periods)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu',
            zmid=0,
            text=corr_matrix.round(2).values,
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Funds",
            yaxis_title="Funds",
            width=800,
            height=600
        )
        
        fig.show()
        return corr_matrix
    
    def plot_risk_return(self, timespan: str = '1Y', 
                               isins: Optional[List[str]] = None,
                               benchmark_isins: Optional[List[str]] = None,
                               title: str = "Risk vs Return Analysis"):
        """Create risk-return scatter plot."""
        risk_return_data = self.analyzer.calculate_risk_return_metrics(timespan, isins)
        
        if risk_return_data.empty:
            logger.warning(f"No risk-return data available for timespan {timespan}.")
            return
        
        # Create scatter plot
        fig = px.scatter(
            risk_return_data, 
            x='volatility', 
            y='return',
            color='sharpe',
            hover_data=['name'],
            title=f'{title} ({timespan})',
            labels={
                'volatility': 'Volatility (Risk) %',
                'return': 'Return %',
                'sharpe': 'Sharpe Ratio'
            },
            color_continuous_scale='viridis'
        )
        
        # Highlight benchmarks if provided
        if benchmark_isins is not None:
            benchmark_data = risk_return_data.loc[
                risk_return_data.index.isin(benchmark_isins)
            ]
            if not benchmark_data.empty:
                fig.add_scatter(
                    x=benchmark_data['volatility'],
                    y=benchmark_data['return'],
                    mode='markers',
                    marker=dict(size=15, symbol='star', color='red'),
                    name='Benchmarks',
                    hovertext=benchmark_data['name']
                )
        
        # Add efficient frontier line (simplified)
        if len(risk_return_data) > 1:
            mean_sharpe = risk_return_data['sharpe'].mean()
            if not np.isnan(mean_sharpe) and mean_sharpe > 0:
                vol_range = np.linspace(
                    risk_return_data['volatility'].min(),
                    risk_return_data['volatility'].max(),
                    100
                )
                fig.add_scatter(
                    x=vol_range,
                    y=mean_sharpe * vol_range,
                    mode='lines',
                    line=dict(dash='dash', color='red'),
                    name=f'Avg Sharpe Ratio = {mean_sharpe:.2f}'
                )
        
        fig.update_layout(
            width=900,
            height=600,
            showlegend=True
        )
        
        fig.show()
        return risk_return_data
    
    def plot_benchmark_comparison(self, fund_isins: List[str], 
                                benchmark_isins: Optional[List[str]] = None,
                                start_date: Optional[str] = None, 
                                end_date: Optional[str] = None,
                                normalize_date: Optional[str] = None,
                                plot_difference: bool = True):
        """Compare fund performance against benchmarks."""
        # Default benchmarks
        if benchmark_isins is None:
            benchmark_isins = [
                'IE00B5BMR087',  # iShares Core S&P 500 UCITS ETF
                'DE000A0F5UF5',  # iShares STOXX Europe 600 UCITS ETF
                'IE0005042456',  # iShares MSCI EM UCITS ETF
                'DE0006289390',  # iShares MSCI Japan UCITS ETF
                'DE0005933931',  # iShares Core DAX UCITS ETF
                'LU0340285161'   # Xtrackers MSCI World UCITS ETF
            ]
        
        all_isins = list(set(fund_isins + benchmark_isins))
        ts_data = self.data_manager.select_timeseries(all_isins)
        
        if ts_data.empty:
            logger.warning("No timeseries data available for comparison.")
            return None, None
        
        # Filter by date range
        if start_date:
            ts_data = ts_data[ts_data.index >= start_date]
        if end_date:
            ts_data = ts_data[ts_data.index <= end_date]
        
        # Set normalize date
        if normalize_date is None:
            normalize_date = ts_data.index.min()
        elif normalize_date not in ts_data.index:
            closest_date = ts_data.index[
                ts_data.index.get_indexer([normalize_date], method='nearest')[0]
            ]
            logger.info(f"Using closest date {closest_date} instead of {normalize_date}")
            normalize_date = closest_date
        
        # Normalize data
        normalized_ts = ts_data.div(ts_data.loc[normalize_date], axis=1) * 100
        
        # Create comparison plot
        fig = go.Figure()
        
        # Plot funds
        for isin in fund_isins:
            if isin in normalized_ts.columns:
                label = self._get_fund_name(isin)
                fig.add_trace(go.Scatter(
                    x=normalized_ts.index,
                    y=normalized_ts[isin],
                    mode='lines',
                    name=label,
                    line=dict(width=2)
                ))
        
        # Plot benchmarks
        for isin in benchmark_isins:
            if isin in normalized_ts.columns:
                label = f"Benchmark: {self._get_fund_name(isin)}"
                fig.add_trace(go.Scatter(
                    x=normalized_ts.index,
                    y=normalized_ts[isin],
                    mode='lines',
                    name=label,
                    line=dict(dash='dash', width=1.5),
                    opacity=0.7
                ))
        
        fig.update_layout(
            title=f'Fund Performance vs Benchmarks (Normalized to {normalize_date.strftime("%Y-%m-%d")})',
            xaxis_title='Date',
            yaxis_title='Normalized Value (%)',
            width=1000,
            height=600,
            hovermode='x unified'
        )
        
        fig.show()
        
        # Plot difference from benchmarks
        if plot_difference and benchmark_isins:
            benchmark_cols = [col for col in normalized_ts.columns if col in benchmark_isins]
            if benchmark_cols:
                avg_benchmark = normalized_ts[benchmark_cols].mean(axis=1)
                
                fig_diff = go.Figure()
                
                for isin in fund_isins:
                    if isin in normalized_ts.columns:
                        diff = normalized_ts[isin] - avg_benchmark
                        label = self._get_fund_name(isin)
                        fig_diff.add_trace(go.Scatter(
                            x=normalized_ts.index,
                            y=diff,
                            mode='lines',
                            name=label,
                            line=dict(width=2)
                        ))
                
                # Add zero line
                fig_diff.add_hline(y=0, line_dash="solid", line_color="red", opacity=0.5)
                
                fig_diff.update_layout(
                    title='Outperformance/Underperformance vs Average Benchmark',
                    xaxis_title='Date',
                    yaxis_title='Difference (%)',
                    width=1000,
                    height=600,
                    hovermode='x unified'
                )
                
                fig_diff.show()
                
                return normalized_ts, normalized_ts[fund_isins].subtract(avg_benchmark, axis=0)
        
        return normalized_ts, None
    
    def _get_fund_name(self, isin: str) -> str:
        """Get fund name from ISIN, with fallback to ISIN."""
        if ('name' in self.data_manager.funds_overview.columns and 
            isin in self.data_manager.funds_overview.index):
            name = self.data_manager.funds_overview.loc[isin, 'name']
            if isinstance(name, str) and len(name) > 30:
                return name[:28] + '...'
            return name
        return isin


class Scrappy:
    """Main class that orchestrates all fund analysis operations."""
    
    def __init__(self, funds_overview_path: Optional[str] = None, 
                 performance_path: Optional[str] = None, 
                 timeseries_path: Optional[str] = None):
        self.data_manager = FundsDataManager(funds_overview_path, performance_path, timeseries_path)
        self.scraper = DataScraper()
        self.analyzer = FundsAnalyzer(self.data_manager)
        self.visualizer = FundsVisualizer(self.data_manager, self.analyzer)
    
    # Delegate methods to appropriate components
    def search_funds_by_pattern(self, *args, **kwargs):
        """Search for funds using regex pattern matching."""
        return self.data_manager.search_funds_by_pattern(*args, **kwargs)
    
    def filter_funds(self, *args, **kwargs):
        """Filter funds based on specific criteria."""
        return self.data_manager.filter_funds(*args, **kwargs)
    
    def download_funds_overview(self, *args, **kwargs):
        """Download and integrate funds overview data."""
        new_data = self.scraper.download_funds_overview(*args, **kwargs)
        self.data_manager.add_funds_data(new_data)
        self.data_manager.join_finanzen_zero_data()
        return self.data_manager.funds_overview
    
    def download_timeseries(self, *args, **kwargs):
        """Download and integrate timeseries data for funds."""
        new_data, skipped = self.scraper.download_timeseries(*args, **kwargs)
        self.data_manager.add_timeseries_data(new_data)
        return new_data
    
    def extract_performance(self, *args, **kwargs):
        """Extract and format performance metrics from funds data."""
        return self.data_manager.extract_performance(*args, **kwargs)
    
    def filter_top_performers(self, *args, **kwargs):
        """Identify and rank top performing funds based on specified metrics."""
        return self.analyzer.filter_top_performers(*args, **kwargs)
    
    def plot_timeseries(self, *args, **kwargs):
        """Create interactive timeseries visualization of fund prices."""
        return self.visualizer.plot_timeseries(*args, **kwargs)
    
    def plot_correlations(self, *args, **kwargs):
        """Create correlation heatmap showing relationships between funds."""
        return self.visualizer.plot_correlations(*args, **kwargs)
    
    def plot_risk_return(self, *args, **kwargs):
        """Create risk-return scatter plot for fund analysis."""
        return self.visualizer.plot_risk_return(*args, **kwargs)
    
    def plot_benchmark_comparison(self, *args, **kwargs):
        """Compare fund performance against market benchmarks."""
        return self.visualizer.plot_benchmark_comparison(*args, **kwargs)
    
    def save_funds_overview(self, *args, **kwargs):
        """Save funds overview data to file."""
        return self.data_manager.save_funds_overview(*args, **kwargs)
    
    def save_performance(self, *args, **kwargs):
        """Save performance metrics data to file."""
        return self.data_manager.save_performance(*args, **kwargs)
    
    def save_timeseries(self, *args, **kwargs):
        """Save timeseries price data to file."""
        return self.data_manager.save_timeseries(*args, **kwargs)
    
    def rank_funds(self, *args, **kwargs):
        """Rank funds based on performance and risk criteria."""
        return self.analyzer.rank_funds(*args, **kwargs)
    
    def rank_funds_by_strategy(self, *args, **kwargs):
        """Rank funds using predefined investment strategies."""
        return self.analyzer.rank_funds_by_strategy(*args, **kwargs)
    
    # Properties for backward compatibility
    @property
    def funds_overview(self):
        return self.data_manager.funds_overview
    
    @property
    def performance(self):
        return self.data_manager.performance
    
    @property
    def ts(self):
        return self.data_manager.timeseries

