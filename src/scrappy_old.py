import os
import requests
# import json
import dirtyjson
import re
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
from IPython.display import display


class Scrappy():
    
    def __init__(self, funds_overview_path=None, performance_path=None, timeseries_path=None):
        """
        Parameters
        ----------
        funds_overview_path: str, optional
            (relative) path to funds summary file
            
        timeseries_path: str, optional
            (relative) path to timeseries data file
            
        Returns
        -------
        None
        """
        def str_to_list(s):
            return list(eval(s))
        
        if not funds_overview_path:
            self.funds_overview = pd.DataFrame()
        else:
            self.funds_overview_path = funds_overview_path
            self.funds_overview = pd.read_csv(funds_overview_path, index_col='isin',
                                              converters={'performance': str_to_list, 'risk': str_to_list})
        
        if not performance_path:
            self.performance = None
        else:
            self.performance_path = performance_path
            self.performance = pd.read_csv(performance_path, index_col=['isins', 'timeSpan'])
            
        if not timeseries_path:
            self.ts = None
        else:
            self.timeseries_path = timeseries_path
            self.ts = pd.read_csv(timeseries_path, index_col='x')
            self.ts.index = pd.to_datetime(self.ts.index)
            
        self.api_url = 'https://www.fondsdiscount.de/themes/barcelona/content/module/chart/getChartData.php'
        self.headers = {
            'Host': 'www.fondsdiscount.de',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Length': '68',
            'Origin': 'https://www.fondsdiscount.de',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': '',
            'Cookie': '',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'trailers',
        }
        self.data_template = {
            'function': 'getMultiChartIsin',
            'isin': 'DE000A0KEYM4',
            #'pg': '19-3', # benchmark time series
            'fondsname': '',
            #'pg_name': 'Aktienfonds+All+Cap+Welt',
            'range': '4',
            'org_currency': 'true',
            'charttyp': 'p',
            'maxNameLength': '40',
            'chart': 'chart_p',
        }
        
        self.session = None
        
    def select_funds(self, filter_lst=None, column='index', from_isins=None):
        """returns full or filtered funds overview from previous search or import of funds overview.
        
        Parameters
        ----------
        filter_lst: {str, list(str)}, optional
            filter fonds summary by string or list of strings. if not specified, gives full fonds summary
        
        column: str, default='index'
            which column in self.fonds_overview to filter by. if 'index', filter by index
            
        from_isins: list(str), optional
            preselect isins from which to filter. Useful for narrowing down filtered results.
        
        Returns
        -------
        pandas.DataFrame
            full or filtered fonds summary
        
        """
        if from_isins is None:
            funds = self.funds_overview
        else:
            funds = self.funds_overview.loc[from_isins]
        
        if filter_lst is None:
            return funds
        else:
            if isinstance(filter_lst, str):
                filter_lst = [filter_lst]
                
            if column == 'index':
                try:
                    return funds.loc[filter_lst]
                except KeyError:
                    skipped = list(set(filter_lst)- set(funds.index))
                    print("Not found:", skipped)
                    return funds.loc[funds.index.intersection(filter_lst)]
            else:
                return funds[funds[column].isin(filter_lst)]
            
    def summary(self, filter_lst, show_columns=['name', 'TER', 'initial_fee'], column='index', from_isins=None):
        """
        Show condensed summary of filtered funds
        
        Parameters
        ----------
        filter_lst: {str, list(str)}, optional
            filter fonds summary by string or list of strings. if not specified, gives full fonds summary
            
        show_columns: list
            columns which should be displayed
        
        column: str, default='index'
            which column in self.fonds_overview to filter by. if 'index', filter by index
            
        from_isins: list(str), optional
            preselect isins from which to filter. Useful for narrowing down filtered results.
        
        Returns
        -------
        pandas.DataFrame
            full or filtered fonds summary
        """
        return self.select_funds(filter_lst, column, from_isins)[show_columns]
        
    def get_performance(self, isins=None, columns=['performance', 'risk'], transpose=False, dropna=False):
        """
        
        Parameters
        ----------
        isins: list, optional
            isins for which to get performance data
            
        columns: list, default=['performance', 'risk']
            get performance, and/or risk data
            
        transpose: bool, default=False
            whether to have performance data columns (False) or time data columns
        
        dropna: bool, default=False
            drop columns which don't have numerical data
        
        Returns
        -------
        pandas.DataFrame
            multi-index dataframe with first level isin and second level performance or time
        """
        merge = True if len(columns) == 2 else False

        if isins is None:
            isins = list(self.select_funds().index)

        found_isins = []
        dfs = []
        for isin in isins:
            fund = self.select_funds(isin)
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
        
        self.performance = pd.concat(dfs, keys=found_isins)
        self.performance.index.rename('isins', level=0, inplace=True)
        if dropna:
            self.performance.dropna(thresh=2, inplace=True)
        return self.performance
    
    def save_performance(self, filename=None):
        if filename is None:
            filename = self.performance_path
        if self.performance is not None:
            self.performance.to_csv(filename)
            
    def select_perf(self, isins=None, by='sharpeRatio', timespan='1Y', limit=50):
        def order_columns(cols, order):
            correspondence = {i:n for n, i in enumerate(order)}
            return cols.map(correspondence)

        ascending = True if by == 'volatility' else False

        top_perf = self.performance.loc[self.select_funds(isins).index].xs(timespan, level='timeSpan').sort_values(by=by, ascending=ascending).head(limit)

        display(top_perf)

        return self.select_funds(top_perf.index).sort_index(key=lambda c: order_columns(c, top_perf.index))
            
    def search_funds(self, regex_str, column='index'):
        if column == 'index':
            return self.funds_overview.filter(regex=regex_str, axis=0)
        else:
            return self.funds_overview.loc[self.funds_overview[column].str.contains(regex_str, regex=True), :]
        
    def restart_session(self):
        if self.session is not None:
            self.session.close()
            
        self.session = requests.Session()
        return self.session
        
    def get_response(self, url, data=None, params=None, headers=None, method='POST'):
        """returns HTTP response of successful request. Automatic retry on ConnectionError
        
        Parameters
        ----------
        url, data, params, headers, method='POST'
            see requests.request
            
        Returns
        -------
        requests.Response, None
            if successful (status_code = 200)
        """
        if self.session is None:
            self.restart_session()
        try:
            response = self.session.request(method=method, url=url, data=data, params=params, headers=headers)
        except requests.ConnectionError:
            print('ConnectionError, restarting session.')
            self.restart_session()
            response = self.session.request(method=method, url=url, data=data, params=params, headers=headers)
        
        if response.status_code == 200:
            return response


    def get_search_results(self, filter_ids=[5634,5703,5582], etf=False, benchmark=False, limit=100):
        """Gets funds and ETF summary data from onvista website. Appends results to self.funds_overview.
        Filters for initial investments up to 5000€.
        
        Parameters
        ----------
        filter_ids: int, list(int), None, default=[5634,5703,5582]
            onvista IDs to filter for, e.g.
            5634: Aktien Nachhaltigkeit
            5703: Aktien Branche Alternative Energien
            5582: Aktien Branche Ökologie, Umwelttechnologien
            
        etf: bool, default=False
            if True, returns ETFs. if False, returns funds
            
        benchmark: bool, default=False
            if True, returns benchmark indices for S&P500, NASDAQ, FTSE100, Dow Jones, DAX & MSCI World as ETF
            
        limit: int, default=100
            maximum search results
            
        Returns
        -------
        pandas.DataFrame
            results of current search query
        """
        
        self.search_api_url = 'https://api.onvista.de/api/v1/funds/finder/configuration_query'
        params = {
            'application': 'WEBSITE',
            'device': 'DESKTOP',
            'order': 'DESC',
            'page': '0',
            'perPage': '100',
            'queryParameters': '',
            'sort': 'performancePct1Y',}
        headers = {
            'Host': 'api.onvista.de',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': 'https://www.onvista.de',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'Trailers',}
        
        cols = ['instrument.name', 'instrument.entitySubType', 'fundsDetails.nameInvestmentFocus',
                'fundsDetails.fundsInvestmentRegion.name', 'issuer.nameGroupIssuer', 'benchmark.instrument.name',
                'instrument.isin', 'fundsBaseData.nameCountry', 'fundsBaseData.isoCurrencyFund',
                'fundsBaseData.volumeFund', 'fundsDetails.fundsTypeCapitalisation.name',
                'fundsBaseData.maxPctInitialFee', 'fundsBaseData.ongoingCharges',
                'fundsEvaluation.morningstarRating', 'fundsEvaluation.morningstarRating3y', 'fundsEvaluation.morningstarRating5y',
                'fundsEvaluation.feriRating', 'fundsEvaluation.riskClass',
                'fundsPerformanceList.list', 'fundsRiskList.list', 'instrument.wkn', 'fundsBaseData.allInFee', 'fundsBaseData.isoCurrencyFees', 'fundsBaseData.custodianBankFeePct',
                'fundsBaseData.switchingFee', 'fundsBaseData.maxPctDistributionFee', 'fundsBaseData.maxPctRedemptionFee',]
        colnames = ['name', 'type', 'investment_focus', 'region', 'issuer', 'benchmark', 'isin', 'country', 'currency', 'volume',
                    'fund_type', 'initial_fee', 'TER', 'morningstar', 'morningstar_3y', 'morningstar_5y', 'feri', 'risk_class',
                    'performance', 'risk', 'wkn', 'all_in_fee', 'currency_fee', 'depot_bank_fee', 'switching_fee', 'distribution_fee',
                    'redemption_fee', 'min_initial_investment', 'min_followup_investment']
        
        if benchmark:
            # ignore other options if benchmark=True
            options = ['isExchangeTraded=true', 'idInstrumentBenchmark=16204403,4646272,83327,376508,376391,376376',
                       'idTypeReplication=2']
        else:
            options = list()
            if etf:
                options.append('isExchangeTraded=true')

            if filter_ids is not None:
                if isinstance(filter_ids, int):
                    filter_ids = str(filter_ids)
                elif isinstance(filter_ids, list):
                    filter_ids = ','.join(map(str, filter_ids))
                options.append('idInvestmentFocus=' + filter_ids)

            options.append('minInitialInvestmentRange=0;5000')
            
        # API doesn't support more than 1000 results, do some artifical filtering
        if limit > 1000:
            params['perPage'] = 1000
            split_results_by = ['maxPctInitialFeeRange=0;4.9', 'maxPctInitialFeeRange=4.9;7']
        else:
            params['perPage'] = str(limit)
            split_results_by = ['maxPctInitialFeeRange=0;7']
                
        dfs = []
        for split in split_results_by:
            params['queryParameters'] = '&'.join(options + [split])
                
            response = self.get_response(url=self.search_api_url, params=params, headers=headers, method='GET')

            df = pd.json_normalize(response.json()['list'])
            
            opt_cols = ['fundsBaseData.minInitialInvestment', 'fundsBaseData.minFollowupInvestment']
            if etf or benchmark:
                df = df[cols]
                df[opt_cols] = (np.nan, np.nan)
            else:
                df = df[cols + opt_cols]
            df.columns = colnames
            df.set_index('isin', inplace=True)
            dfs.append(df)
        
        df = pd.concat(dfs, axis=0)
        self.funds_overview = pd.concat([self.funds_overview, df], axis=0)
        
        # remove duplicates by index:
        self.funds_overview = self.funds_overview[~self.funds_overview.index.duplicated(keep='last')]

        return self.funds_overview
    

    def save_search_results(self, filename=None):
        if filename is None:
            filename = self.funds_overview_path
        if self.funds_overview is not None:
            self.funds_overview.to_csv(filename)


    def join_finanzen_zero_data(self, filename='data/downloadable-instruments.csv'):
        """
        Join finanzen.net tradeable funds data.
        accessible at:
        https://mein.finanzen-zero.net/assets/searchdata/downloadable-instruments.csv
        """
        if not os.path.exists('data/downloadable-instruments.csv'):
            print("Skip finanzen.net: './data/downloadable-instruments.csv' not found")
            return
        
        df = pd.read_csv(filename, sep=';')
        df.index=df['ISIN']
        df['finanzen_zero'] = True
        df = df.rename(columns={'Sparplan': 'sparplan_finanzen_zero'}).drop(columns=['ISIN','WKN', 'Typ','Name'])
        df['sparplan_finanzen_zero'] = df['sparplan_finanzen_zero'] == 'Ja'

        self.funds_overview = self.funds_overview.drop(columns=['finanzen_zero', 'sparplan_finanzen_zero'], errors='ignore').join(df, how='left')
        self.funds_overview['finanzen_zero'] = self.funds_overview['finanzen_zero'].fillna(False)
        
        return self.funds_overview
    

    def parse_timeseries_data(self, response_str):
        """Clean up and parse http response of timeseries into DataFrame.
        
        Parameters
        ----------
        response_str: str
            response of http request as string
            
        Returns
        -------
        pandas.DataFrame, None
            parsed response string
        """
        
        print("parsing...")
        reg = re.search(r"series : (\[[\s\S]+\])\s+\}\);", response_str)
        if reg is None:
            print('Cannot parse response')
            return

        json_str = reg.group(1)    
        json_str = json_str.replace('Date.UTC', 'datetime.date')
        json_str = re.sub(r',0(\d)', r',\1', json_str)
        json_str = re.sub(r"data: \[?(\[[\s\S]+?\])?\]", r"data: '[\1]'", json_str)
        data = dirtyjson.loads(json_str)
        
        dfs = []
        skipped = []
        for i in data:
            X = eval(i['data'])
            if len(X) > 0:
                df = pd.DataFrame.from_records(X, columns=['x', i['id']])
                df.set_index('x', inplace=True)
                # response data shifted by one month for some reason
                df.index = pd.to_datetime(df.index) + pd.DateOffset(months=1)
                dfs.append(df)
            else:
                skipped.append(i['id'])
        if len(skipped) > 0:
            print("No data:", skipped)
        return pd.concat(dfs, axis=1, join='outer'), skipped
    

    def get_timeseries(self, isins, batch_size=100):
        """ Gets timeseries data from fondsdiscounter website. Sets self.ts
        
        Parameters
        ----------
        isins: str, list(str)
            ISIN or List of ISINs
            
        Returns
        -------
        pandas.DataFrame
            full timeseries for ISINs in wide format
            
        TODO
        ----
        remove old ts if new data queried
        """
        
        if isinstance(isins, str):
            isins = [isins]
        else:
            isins = list(isins)
        
        data = self.data_template.copy()
        
        dfs = []
        batches, rem = divmod(len(isins), batch_size)
        for k in range(batches+1):
            isins_batch = isins[k*batch_size:(k+1)*batch_size]
            if len(isins_batch) > 0:
                data['isin'] = ','.join(isins_batch)
                response = self.get_response(url=self.api_url, data=data, headers=self.headers, method='POST')

                if response:
                    df, skipped = self.parse_timeseries_data(response.text)
                    if df is not None:
                        dfs.append(df)
                    else:
                        print('No data for {}'.format(isins_batch))
                else:
                    print('No response for {}'.format(isins_batch))
        # TODO: only drop the ones we add, not the ones requested
        self.ts.drop(isins, axis=1, inplace=True, errors='ignore')
        df = pd.concat(dfs, axis=1, join='outer')
        self.ts = self.ts.combine_first(df)
        return df
        
    def save_timeseries(self, filename=None):
        if filename is None:
            filename = self.timeseries_path
        if self.ts is not None:
            self.ts.to_csv(filename)
            
    def select_ts(self, columns):
        """return timeseries for ISINs if they are present in self.ts.
        
        Parameters
        ----------
        columns: list(str)
            list of ISINs to select from timeseries
        
        Returns
        -------
        pandas.DataFrame
            timeseries which could be found
        """
        skipped = []
        cols = filter(None, [i if i in set(self.ts.columns) else skipped.append(i) for i in columns])
        if len(skipped) > 0:
            print('Not in ts:', skipped)
        return self.ts[cols]
    
    def get_ts_long(self, ts=None, val_name='y', var_name='name'):
        """transform timeseries into long format for plotting
        
        Parameters
        ----------
        ts: pandas.DataFrame, optional
            timeseries dataframe. if None, self.ts is used
            
        val_name: str, default='y'
            name of the resulting function values column
            
        var_name: str, default='name'
            name for the variable column in long format e.g. ISINs
            
        Returns
        -------
        pandas.DataFrame
            timeseries in long format
        """
        if ts is None:
            ts = self.ts
        id_var = ts.index.name
        ts_long = pd.melt(ts.reset_index(), id_vars=id_var, var_name=var_name, value_name=val_name)
        return ts_long
    
    def transform(self, func, ts=None, args=(), **kwds):
        """apply function to timeseries
        
        Parameters
        ----------
        func: function
            function, which gets applied to each timeseries
            
        ts: pandas.DataFrame, optional
            timeseries where fuction should be applied. if None, self.ts is used
            
        args, kwds: optional
            (keyword) arguments to be applied to func
        """
        if ts is None:
            ts = self.ts
        return ts.apply(func, result_type=None, args=args, **kwds)

    def plot_ts(self, columns=None, transform=None, legend=False, name=None):
        """plots timeseries for 
        
        Parameters
        ----------
        columns: list(str)
            list of ISINs to plot
            
        transform: {str, function}, optional
            if 'yyyy-mm-dd', 'yesterday': normalize each timeseries to specified date or last business day
            or function f(pd.Series) -> pd.Series to apply to each timeseries before plotting 
            
        legend: bool, default=False
            if True, plots legend
            
        name: str, optional
            column of self.funds_overview to use for timeseries labels
        """
        if columns is not None:
            if isinstance(columns, str):
                columns = [columns]
            else:
                columns = list(columns)
            ts = self.select_ts(columns)
        else:
            ts = self.ts
            
        if name is not None:
            try:
                ts.columns = self.funds_overview.loc[ts.columns, name]
            except KeyError:
                # timeseries queried from different source, thus ISIN can be missing from self.funds_overview
                ts.columns = [self.funds_overview[name].get(i, i) for i in ts.columns]
        
        x = ts.index.name
        y = 'y'
        color = 'name'
        
        if transform is not None:
            if isinstance(transform, str):
                if transform == 'yesterday':
                    date = datetime.date.today() - pd.tseries.offsets.BusinessDay(1)
                else:
                    date = transform
                transform_func = lambda s: s/s.loc[date]
            else:
                transform_func = transform
            # need to interpolate NaN so that timeseries don't get lost upon transformation
            ts = self.transform(transform_func, ts=ts.interpolate('time'))
        
        ts_long = self.get_ts_long(ts, val_name=y, var_name=color).dropna()

        fig = px.line(ts_long, x=x, y=y, color=color)
#         fig.update_layout(legend={'yanchor': 'top', 'xanchor': 'left', 'y': 1, 'x': 0})
        fig.update_layout(showlegend=legend)
        fig.show()

    # AI generated:
    def plot_fund_correlations(self, isins=None, min_periods=30, method='pearson', cmap='coolwarm', title='Fund Return Correlations'):
        """
        Compute and plot correlations between fund time series.
        
        Parameters
        ----------
        isins : list, optional
            List of ISINs to include. If None, uses all available time series.
        min_periods : int, default=30
            Minimum number of observations required to compute correlation.
        method : {'pearson', 'kendall', 'spearman'}, default='pearson'
            Method of correlation:
            - pearson: standard correlation coefficient
            - kendall: Kendall Tau correlation coefficient
            - spearman: Spearman rank correlation coefficient
        cmap : str, default='coolwarm'
            Colormap for the heatmap.
        title : str, default='Fund Return Correlations'
            Title for the plot.
        
        Returns
        -------
        pandas.DataFrame
            Correlation matrix of fund returns.
        """
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Select time series data for the given ISINs
        if isins is not None:
            ts_data = self.select_ts(isins)
        else:
            ts_data = self.ts
        
        if ts_data.empty:
            print("No time series data available for analysis.")
            return None
        
        # Calculate daily returns
        returns = ts_data.pct_change().dropna()
        
        # Compute correlation matrix
        corr_matrix = returns.corr(method=method, min_periods=min_periods)
        
        # Plot correlation heatmap
        plt.figure(figsize=(12, 10))
        mask = np.zeros_like(corr_matrix, dtype=bool)
        mask[np.triu_indices_from(mask, k=1)] = True  # Show only lower triangle
        
        sns.heatmap(
            corr_matrix, 
            annot=True,
            mask=mask,
            cmap=cmap,
            vmin=-1, 
            vmax=1, 
            center=0,
            square=True,
            fmt=".2f",
            linewidths=0.5,
            cbar_kws={"shrink": .8}
        )
        
        plt.title(title, fontsize=16)
        plt.tight_layout()
        plt.show()
        
        return corr_matrix

    def plot_risk_return(self, timespan='1Y', isins=None, benchmark_isins=None, annualized=True, 
                         min_periods=30, figsize=(12, 8), include_labels=True, label_column='name'):
        """
        Create a risk-return scatter plot for funds.
        
        Parameters
        ----------
        timespan : str, default='1Y'
            Time period for analysis ('1M', '3M', '1Y', '3Y', '5Y').
        isins : list, optional
            List of ISINs to include. If None, uses all funds in funds_overview.
        benchmark_isins : list, optional
            List of benchmark ISINs to highlight in the plot.
        annualized : bool, default=True
            Whether to annualize the return and volatility.
        min_periods : int, default=30
            Minimum number of observations required for calculations.
        figsize : tuple, default=(12, 8)
            Figure size.
        include_labels : bool, default=True
            Whether to include labels for each fund.
        label_column : str, default='name'
            Column to use for fund labels.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame with risk and return metrics.
        """
        import matplotlib.pyplot as plt
        
        # Get data for plotting
        risk_return_data = pd.DataFrame()
        
        if isins is None:
            funds_df = self.funds_overview
        else:
            funds_df = self.select_funds(isins)
        
        if funds_df.empty:
            print("No fund data available for analysis.")
            return None
        
        # Extract data from performance metrics
        for isin in funds_df.index:
            # Skip if necessary columns don't exist
            if 'performance' not in funds_df.columns or 'risk' not in funds_df.columns:
                continue
                
            # Skip if not list data
            if not isinstance(funds_df.loc[isin, 'performance'], list) or not isinstance(funds_df.loc[isin, 'risk'], list):
                continue
            
            # Extract performance data for this timespan
            perf_data = next((item for item in funds_df.loc[isin, 'performance'] 
                              if item['timeSpan'] == timespan), None)
            
            # Extract risk data for this timespan
            risk_data = next((item for item in funds_df.loc[isin, 'risk'] 
                              if item['timeSpan'] == timespan), None)
            
            # Skip if data missing
            if perf_data is None or risk_data is None:
                continue
            
            # Add to DataFrame
            risk_return_data.at[isin, 'return'] = perf_data.get('performanceTimeSpanPct', np.nan)
            risk_return_data.at[isin, 'volatility'] = risk_data.get('volatility', np.nan)
            risk_return_data.at[isin, 'sharpe'] = risk_data.get('sharpeRatio', np.nan)
            
            # Add fund name for labels
            if label_column in funds_df.columns:
                risk_return_data.at[isin, 'name'] = funds_df.at[isin, label_column]
            else:
                risk_return_data.at[isin, 'name'] = isin
        
        # Drop rows with missing data
        risk_return_data = risk_return_data.dropna(subset=['return', 'volatility'])
        
        if risk_return_data.empty:
            print(f"No risk-return data available for timespan {timespan}.")
            return None
        
        # Create scatter plot
        plt.figure(figsize=figsize)
        
        # Plot funds
        scatter = plt.scatter(
            risk_return_data['volatility'], 
            risk_return_data['return'],
            alpha=0.6,
            s=100,  # point size
            c=risk_return_data['sharpe'], 
            cmap='viridis'
        )
        
        # Highlight benchmarks if provided
        if benchmark_isins is not None:
            benchmark_data = risk_return_data.loc[risk_return_data.index.isin(benchmark_isins)]
            if not benchmark_data.empty:
                plt.scatter(
                    benchmark_data['volatility'],
                    benchmark_data['return'],
                    s=150,  # larger size for benchmarks
                    marker='*',  # star marker
                    c='red',
                    label='Benchmarks'
                )
        
        # Add labels if requested
        if include_labels:
            for idx, row in risk_return_data.iterrows():
                label = row['name']
                if isinstance(label, str) and len(label) > 20:
                    label = label[:18] + '...'  # Truncate long names
                plt.annotate(
                    label,
                    (row['volatility'], row['return']),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=8
                )
        
        # Add color bar to show Sharpe ratio
        cbar = plt.colorbar(scatter)
        cbar.set_label('Sharpe Ratio')
        
        # Add grid lines
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add title and labels
        period_label = {
            '1M': '1 Month', '3M': '3 Months', '1Y': '1 Year',
            '3Y': '3 Years', '5Y': '5 Years', '10Y': '10 Years'
        }.get(timespan, timespan)
        
        plt.title(f'Risk vs. Return ({period_label})', fontsize=16)
        plt.xlabel('Volatility (Risk) %', fontsize=12)
        plt.ylabel('Return %', fontsize=12)
        
        # Add optimal portfolio line
        min_vol = risk_return_data['volatility'].min()
        max_vol = risk_return_data['volatility'].max()
        vol_range = np.linspace(min_vol, max_vol, 100)
        
        # Calculate mean Sharpe ratio
        mean_sharpe = risk_return_data['sharpe'].mean()
        if not np.isnan(mean_sharpe) and mean_sharpe > 0:
            # Draw a line representing constant Sharpe ratio
            plt.plot(vol_range, mean_sharpe * vol_range, 'r--', 
                     label=f'Sharpe Ratio = {mean_sharpe:.2f}')
        
        plt.legend()
        plt.tight_layout()
        plt.show()
        
        return risk_return_data

    def compare_with_benchmarks(self, fund_isins, benchmark_isins=None, 
                               start_date=None, end_date=None, normalize_date=None,
                               figsize=(14, 8), plot_diff=True):
        """
        Compare fund performance against benchmarks.
        
        Parameters
        ----------
        fund_isins : list
            List of fund ISINs to analyze.
        benchmark_isins : list, optional
            List of benchmark ISINs. If None, uses default benchmarks.
        start_date : str, optional
            Start date for the analysis in format 'YYYY-MM-DD'.
        end_date : str, optional
            End date for the analysis in format 'YYYY-MM-DD'.
        normalize_date : str, optional
            Date to normalize returns to in format 'YYYY-MM-DD'.
            If None, normalizes to the first date in the range.
        figsize : tuple, default=(14, 8)
            Figure size.
        plot_diff : bool, default=True
            Whether to plot the difference from benchmarks.
        
        Returns
        -------
        tuple
            (normalized_ts, diff_from_benchmark)
        """
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        # Default benchmarks if none provided
        if benchmark_isins is None:
            benchmark_isins = [
                'IE00B5BMR087',  # iShares Core S&P 500 UCITS ETF
                'DE000A0F5UF5',  # iShares STOXX Europe 600 UCITS ETF
                'IE0005042456',  # iShares MSCI EM UCITS ETF
                'DE0006289390',  # iShares MSCI Japan UCITS ETF
                'DE0005933931',  # iShares Core DAX UCITS ETF
                'LU0340285161'   # Xtrackers MSCI World UCITS ETF
            ]
        
        # Combine fund and benchmark ISINs
        all_isins = list(set(fund_isins + benchmark_isins))
        
        # Get time series data for all ISINs
        ts_data = self.select_ts(all_isins)
        
        if ts_data.empty:
            print("No time series data available for the selected funds and benchmarks.")
            return None, None
        
        # Filter by date range if provided
        if start_date:
            ts_data = ts_data[ts_data.index >= start_date]
        if end_date:
            ts_data = ts_data[ts_data.index <= end_date]
        
        # Set normalize date if not provided
        if normalize_date is None:
            normalize_date = ts_data.index.min()
        elif normalize_date not in ts_data.index:
            # Find closest date
            closest_date = ts_data.index[ts_data.index.get_indexer([normalize_date], method='nearest')[0]]
            print(f"Normalize date {normalize_date} not found, using closest date {closest_date}")
            normalize_date = closest_date
        
        # Normalize data
        normalized_ts = ts_data.div(ts_data.loc[normalize_date], axis=1) * 100
        
        # Create figure
        plt.figure(figsize=figsize)
        
        # Plot funds
        for isin in fund_isins:
            if isin in normalized_ts.columns:
                label = isin
                if 'name' in self.funds_overview.columns and isin in self.funds_overview.index:
                    label = self.funds_overview.loc[isin, 'name']
                    if isinstance(label, str) and len(label) > 30:
                        label = label[:28] + '...'
                plt.plot(normalized_ts.index, normalized_ts[isin], label=label, linewidth=2)
        
        # Plot benchmarks with dashed lines
        for isin in benchmark_isins:
            if isin in normalized_ts.columns:
                label = f"Benchmark: {isin}"
                if 'name' in self.funds_overview.columns and isin in self.funds_overview.index:
                    label = f"Benchmark: {self.funds_overview.loc[isin, 'name']}"
                    if isinstance(label, str) and len(label) > 40:
                        label = label[:38] + '...'
                plt.plot(normalized_ts.index, normalized_ts[isin], label=label, 
                         linestyle='--', linewidth=1.5, alpha=0.7)
        
        # Format plot
        plt.title(f'Fund Performance Relative to Benchmarks (Normalized to {normalize_date.strftime("%Y-%m-%d")})', 
                  fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Normalized Value (%)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Format x-axis dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.show()
        
        # Plot difference from benchmarks if requested
        if plot_diff and benchmark_isins:
            # Calculate average benchmark performance
            benchmark_cols = [col for col in normalized_ts.columns if col in benchmark_isins]
            if benchmark_cols:
                avg_benchmark = normalized_ts[benchmark_cols].mean(axis=1)
                
                # Calculate difference for each fund
                diff_from_benchmark = pd.DataFrame(index=normalized_ts.index)
                for isin in fund_isins:
                    if isin in normalized_ts.columns:
                        diff_from_benchmark[isin] = normalized_ts[isin] - avg_benchmark
                
                # Plot differences
                plt.figure(figsize=figsize)
                
                for isin in fund_isins:
                    if isin in diff_from_benchmark.columns:
                        label = isin
                        if 'name' in self.funds_overview.columns and isin in self.funds_overview.index:
                            label = self.funds_overview.loc[isin, 'name']
                            if isinstance(label, str) and len(label) > 30:
                                label = label[:28] + '...'
                        plt.plot(diff_from_benchmark.index, diff_from_benchmark[isin], 
                                 label=label, linewidth=2)
                
                # Add zero line
                plt.axhline(y=0, color='r', linestyle='-', alpha=0.5)
                
                # Format plot
                plt.title(f'Outperformance/Underperformance vs. Average Benchmark', fontsize=16)
                plt.xlabel('Date', fontsize=12)
                plt.ylabel('Difference (%)', fontsize=12)
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                
                # Format x-axis dates
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                plt.xticks(rotation=45)
                
                plt.tight_layout()
                plt.show()
                
                return normalized_ts, diff_from_benchmark
        
        return normalized_ts, None

