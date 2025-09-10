# Configuration Management
class ScrapingConfig:
    """Configuration settings for the scraping operations."""
    
    # Filter categories for fund types
    FILTER_CATEGORIES = {
        'esg': [5634, 5703, 5582],  # Sustainability, Alternative Energy, Ecology
        'renten': [5634, 5532, 5645, 5620, 5670, 5560, 5646, 5647, 5531, 5672,
                  5673, 5674, 5676, 5677, 5648, 5643, 5534, 5644, 5570, 5678,
                  5679, 5680, 5535, 5681, 5581, 5625, 5651, 5654, 5622, 5652,
                  5557, 5684, 5685, 5653, 5558]  # Bond/Fixed Income funds
    }
    
    # API endpoints
    API_URLS = {
        'fondsdiscount': 'https://www.fondsdiscount.de/themes/barcelona/content/module/chart/getChartData.php',
        'onvista': 'https://api.onvista.de/api/v1/funds/finder/configuration_query'
    }
    
    # Default parameters
    DEFAULT_BATCH_SIZE = 100
    MAX_API_LIMIT = 1000 # uses paging for more than 1000 results

    
    # Column mappings for onvista API
    ONVISTA_COLUMNS = {
        'instrument.name': 'name',
        'instrument.entitySubType': 'type',
        'fundsDetails.nameInvestmentFocus': 'investment_focus',
        'fundsDetails.fundsInvestmentRegion.name': 'region',
        'issuer.nameGroupIssuer': 'issuer',
        'benchmark.instrument.name': 'benchmark',
        'instrument.isin': 'isin',
        'fundsBaseData.nameCountry': 'country',
        'fundsBaseData.isoCurrencyFund': 'currency',
        'fundsBaseData.volumeFund': 'volume',
        'fundsDetails.fundsTypeCapitalisation.name': 'fund_type',
        'fundsBaseData.maxPctInitialFee': 'initial_fee', # Ausgabeaufschlag
        'fundsBaseData.ongoingCharges': 'TER',
        'fundsEvaluation.morningstarRating': 'morningstar',
        'fundsEvaluation.morningstarRating3y': 'morningstar_3y',
        'fundsEvaluation.morningstarRating5y': 'morningstar_5y',
        'fundsEvaluation.feriRating': 'feri',
        'fundsEvaluation.riskClass': 'risk_class',
        'fundsPerformanceList.list': 'performance',
        'fundsRiskList.list': 'risk',
        'instrument.wkn': 'wkn',
        'fundsBaseData.allInFee': 'all_in_fee',
        'fundsBaseData.isoCurrencyFees': 'currency_fee',
        'fundsBaseData.custodianBankFeePct': 'depot_bank_fee',
        'fundsBaseData.switchingFee': 'switching_fee',
        'fundsBaseData.maxPctDistributionFee': 'distribution_fee',
        'fundsBaseData.maxPctRedemptionFee': 'redemption_fee',
        'fundsBaseData.minInitialInvestment': 'min_initial_investment',
        'fundsBaseData.minFollowupInvestment': 'min_followup_investment',
        'fundsEvaluation.morningstarSustainabilityRating': 'sustainability_rating',
    }
    
    # Default benchmark ISINs
    DEFAULT_BENCHMARKS = [
        'IE00B5BMR087',  # iShares Core S&P 500 UCITS ETF
        'DE000A0F5UF5',  # iShares STOXX Europe 600 UCITS ETF
        'IE0005042456',  # iShares MSCI EM UCITS ETF
        'DE0006289390',  # iShares MSCI Japan UCITS ETF
        'DE0005933931',  # iShares Core DAX UCITS ETF
        'LU0340285161'   # Xtrackers MSCI World UCITS ETF
    ]
    
    # HTTP headers for different APIs
    FONDSDISCOUNT_HEADERS = {
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
    
    ONVISTA_HEADERS = {
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
        'TE': 'Trailers',
    }
    
    # Data template for fondsdiscount API
    FONDSDISCOUNT_DATA_TEMPLATE = {
        'function': 'getMultiChartIsin',
        'isin': 'DE000A0KEYM4',
        'fondsname': '',
        'range': '4',
        'org_currency': 'true',
        'charttyp': 'p',
        'maxNameLength': '40',
        'chart': 'chart_p',
    }