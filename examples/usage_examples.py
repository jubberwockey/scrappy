#!/usr/bin/env python3
"""
Example usage of the Scrappy funds analysis program.

This file demonstrates how to use the refactored scrappy program for:
1. Downloading funds data
2. Analyzing performance
3. Creating visualizations
4. Generating recommendations
"""

import sys
import os
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrappy import Scrappy, ScrapingConfig


def basic_usage_example():
    """Basic usage example showing core functionality."""
    print("=== Basic Usage Example ===")
    
    # Initialize the scrappy analyzer with data file paths
    scrappy = Scrappy(
        funds_overview_path='data/funds_overview_sample.csv',
        performance_path='data/performance_sample.csv',
        timeseries_path='data/timeseries_sample.csv'
    )
    
    # 1. Download funds overview data (sustainable funds)
    print("1. Downloading sustainable funds data...")
    try:
        funds_data = scrappy.download_funds_overview(
            filter_ids=[5634, 5703, 5582],  # Sustainability, Alternative Energy, Ecology
            limit=50
        )
        print(f"Downloaded {len(funds_data)} funds")
        print(funds_data.head())
    except Exception as e:
        print(f"Error downloading data: {e}")
        # For demo purposes, create sample data
        funds_data = create_sample_funds_data()
        scrappy.data_manager.add_funds_data(funds_data)
    
    # 2. Search for specific funds
    print("\n2. Searching for ESG funds...")
    esg_funds = scrappy.search_funds_by_pattern('ESG|Sustainable|Green', column='name')
    print(f"Found {len(esg_funds)} ESG funds")
    
    # 3. Filter funds by criteria
    print("\n3. Filtering funds by low fees...")
    low_fee_funds = scrappy.filter_funds(
        esg_funds.index[esg_funds['TER'] < 0.5].tolist()
    )
    print(f"Found {len(low_fee_funds)} low-fee funds")
    
    # 4. Extract performance metrics
    print("\n4. Extracting performance metrics...")
    performance_data = scrappy.extract_performance()
    if not performance_data.empty:
        print(performance_data.head())
    
    # 5. Identify top performers
    print("\n5. Identifying top performers...")
    try:
        top_funds = scrappy.filter_top_performers(
            by='sharpeRatio', 
            timespan='1Y', 
            limit=10
        )
        print(f"Top 10 funds by Sharpe ratio:")
        print(top_funds[['name', 'TER']].head())
    except Exception as e:
        print(f"Could not identify top performers: {e}")
    
    return scrappy


def visualization_examples(scrappy):
    """Examples of creating visualizations."""
    print("\n=== Visualization Examples ===")
    
    # Get some sample ISINs for visualization
    sample_isins = list(scrappy.funds_overview.index[:5])
    
    # 1. Download timeseries data for visualization
    print("1. Downloading timeseries data...")
    try:
        timeseries_data = scrappy.download_timeseries(sample_isins)
        print(f"Downloaded timeseries for {len(timeseries_data.columns)} funds")
    except Exception as e:
        print(f"Error downloading timeseries: {e}")
        # Create sample timeseries for demo
        timeseries_data = create_sample_timeseries(sample_isins)
        scrappy.data_manager.add_timeseries_data(timeseries_data)
    
    # 2. Visualize price timeseries
    print("\n2. Creating timeseries visualization...")
    try:
        scrappy.plot_timeseries(
            columns=sample_isins[:3],
            transform='2023-01-01',  # Normalize to start of 2023
            title="Fund Performance Comparison (Normalized to 2023-01-01)"
        )
        print("Timeseries plot created successfully")
    except Exception as e:
        print(f"Error creating timeseries plot: {e}")
    
    # 3. Visualize correlations
    print("\n3. Creating correlation heatmap...")
    try:
        correlation_matrix = scrappy.plot_correlations(
            isins=sample_isins,
            title="Fund Return Correlations"
        )
        print("Correlation heatmap created successfully")
        if correlation_matrix is not None:
            print(f"Average correlation: {correlation_matrix.mean().mean():.3f}")
    except Exception as e:
        print(f"Error creating correlation plot: {e}")
    
    # 4. Risk-return analysis
    print("\n4. Creating risk-return scatter plot...")
    try:
        risk_return_data = scrappy.plot_risk_return(
            timespan='1Y',
            isins=sample_isins,
            title="Risk vs Return Analysis"
        )
        print("Risk-return plot created successfully")
        if risk_return_data is not None and not risk_return_data.empty:
            print(f"Average return: {risk_return_data['return'].mean():.2f}%")
            print(f"Average volatility: {risk_return_data['volatility'].mean():.2f}%")
    except Exception as e:
        print(f"Error creating risk-return plot: {e}")
    
    # 5. Benchmark comparison
    print("\n5. Creating benchmark comparison...")
    try:
        normalized_data, difference_data = scrappy.plot_benchmark_comparison(
            fund_isins=sample_isins[:2],
            normalize_date='2023-01-01',
            plot_difference=True
        )
        print("Benchmark comparison created successfully")
    except Exception as e:
        print(f"Error creating benchmark comparison: {e}")


def advanced_analysis_example(scrappy):
    """Advanced analysis examples."""
    print("\n=== Advanced Analysis Examples ===")
    
    # 1. Integrate broker availability data
    print("1. Integrating broker availability data...")
    try:
        scrappy.join_finanzen_zero_data('data/downloadable-instruments.csv')
        print("Broker data integrated successfully")
        
        # Show funds available with zero fees
        zero_fee_funds = scrappy.filter_funds(
            scrappy.funds_overview[scrappy.funds_overview.get('finanzen_zero', False)].index.tolist()
        )
        print(f"Found {len(zero_fee_funds)} funds with zero broker fees")
    except Exception as e:
        print(f"Error integrating broker data: {e}")
    
    # 2. Custom analysis: Find best sustainable funds with low fees
    print("\n2. Finding best sustainable funds with low fees...")
    try:
        # Filter for sustainable funds with low TER and available at zero fees
        sustainable_funds = scrappy.search_funds_by_pattern('Sustainable|ESG|Green', column='name')
        
        if not sustainable_funds.empty:
            # Apply multiple criteria
            criteria = (
                (sustainable_funds['TER'] < 0.75) &  # Low fees
                (sustainable_funds.get('finanzen_zero', False))  # Available at zero broker fees
            )
            
            best_sustainable = sustainable_funds[criteria]
            print(f"Found {len(best_sustainable)} best sustainable funds:")
            print(best_sustainable[['name', 'TER', 'investment_focus']].head())
        else:
            print("No sustainable funds found in dataset")
    except Exception as e:
        print(f"Error in custom analysis: {e}")
    
    # 3. Performance ranking across different timeframes
    print("\n3. Multi-timeframe performance analysis...")
    try:
        timeframes = ['1Y', '3Y', '5Y']
        performance_summary = {}
        
        for timeframe in timeframes:
            try:
                top_performers = scrappy.filter_top_performers(
                    by='sharpeRatio',
                    timespan=timeframe,
                    limit=5
                )
                performance_summary[timeframe] = top_performers.index.tolist()
                print(f"Top 5 funds ({timeframe}): {len(top_performers)} found")
            except Exception as e:
                print(f"No data for {timeframe}: {e}")
        
        # Find funds that appear in multiple timeframes (consistent performers)
        if len(performance_summary) > 1:
            all_funds = set()
            for funds_list in performance_summary.values():
                all_funds.update(funds_list)
            
            consistent_performers = []
            for fund in all_funds:
                appearances = sum(1 for funds_list in performance_summary.values() if fund in funds_list)
                if appearances >= 2:
                    consistent_performers.append(fund)
            
            print(f"Consistent performers across timeframes: {len(consistent_performers)}")
            if consistent_performers:
                consistent_funds = scrappy.filter_funds(consistent_performers)
                print(consistent_funds[['name', 'TER']].head())
    
    except Exception as e:
        print(f"Error in multi-timeframe analysis: {e}")


def data_management_example(scrappy):
    """Examples of data management operations."""
    print("\n=== Data Management Examples ===")
    
    # 1. Save all data
    print("1. Saving data to files...")
    try:
        scrappy.save_funds_overview('output/funds_overview.csv')
        scrappy.save_performance('output/performance_metrics.csv')
        scrappy.save_timeseries('output/timeseries_data.csv')
        print("Data saved successfully")
    except Exception as e:
        print(f"Error saving data: {e}")
    
    # 2. Data quality checks
    print("\n2. Performing data quality checks...")
    funds_data = scrappy.funds_overview
    
    if not funds_data.empty:
        print(f"Total funds: {len(funds_data)}")
        print(f"Funds with TER data: {funds_data['TER'].notna().sum()}")
        print(f"Funds with performance data: {funds_data['performance'].notna().sum()}")
        print(f"Average TER: {funds_data['TER'].mean():.3f}%")
        print(f"TER range: {funds_data['TER'].min():.3f}% - {funds_data['TER'].max():.3f}%")
        
        # Check for missing data
        missing_data = funds_data.isnull().sum()
        print(f"Columns with missing data: {missing_data[missing_data > 0].to_dict()}")
    
    # 3. Export filtered dataset
    print("\n3. Exporting filtered dataset...")
    try:
        # Create a curated dataset of high-quality funds
        quality_criteria = (
            funds_data['TER'].notna() &
            (funds_data['TER'] < 1.0) &
            funds_data['performance'].notna()
        )
        
        quality_funds = funds_data[quality_criteria]
        print(f"High-quality funds: {len(quality_funds)}")
        
        # Export with additional metadata
        export_data = quality_funds.copy()
        export_data['export_date'] = pd.Timestamp.now()
        export_data['quality_score'] = (
            (1 - export_data['TER'] / export_data['TER'].max()) * 0.5 +  # Lower TER is better
            (export_data['morningstar'].fillna(3) / 5) * 0.3 +  # Higher rating is better
            0.2  # Base score
        )
        
        # Save curated dataset
        export_data.to_csv('output/curated_funds.csv')
        print("Curated dataset exported successfully")
        
    except Exception as e:
        print(f"Error exporting filtered dataset: {e}")


def create_sample_funds_data():
    """Create sample funds data for demonstration."""
    np.random.seed(42)  # For reproducible results
    
    fund_names = [
        'Global Sustainable Equity Fund',
        'European ESG Growth Fund',
        'Green Energy Investment Fund',
        'Sustainable World Index Fund',
        'Climate Action Equity Fund'
    ]
    
    isins = [f'DE000DEMO{i:03d}' for i in range(1, len(fund_names) + 1)]
    
    data = {
        'name': fund_names,
        'TER': np.random.uniform(0.2, 1.5, len(fund_names)),
        'investment_focus': ['Sustainability'] * len(fund_names),
        'morningstar': np.random.choice([3, 4, 5], len(fund_names)),
        'performance': [
            [{'timeSpan': '1Y', 'performanceTimeSpanPct': np.random.uniform(5, 20)}]
            for _ in range(len(fund_names))
        ],
        'risk': [
            [{'timeSpan': '1Y', 'volatility': np.random.uniform(10, 25), 'sharpeRatio': np.random.uniform(0.5, 1.5)}]
            for _ in range(len(fund_names))
        ]
    }
    
    return pd.DataFrame(data, index=isins)


def create_sample_timeseries(isins):
    """Create sample timeseries data for demonstration."""
    np.random.seed(42)
    
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    data = {}
    
    for isin in isins:
        # Generate realistic price series with trend and volatility
        returns = np.random.normal(0.0005, 0.015, len(dates))  # Daily returns
        prices = 100 * np.exp(np.cumsum(returns))  # Convert to price series
        data[isin] = prices
    
    return pd.DataFrame(data, index=dates)


def main():
    """Main function demonstrating all examples."""
    print("Scrappy Funds Analysis - Usage Examples")
    print("=" * 50)
    
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    # Run examples
    try:
        # Basic usage
        scrappy = basic_usage_example()
        
        # Visualizations
        visualization_examples(scrappy)
        
        # Advanced analysis
        advanced_analysis_example(scrappy)
        
        # Data management
        data_management_example(scrappy)
        
        # Example usage of new filter_funds function with dictionary conditions
        print("=== New filter_funds Function Examples ===")

        # Example 1: Filter by multiple conditions including regex
        conditions = {
            'TER': '<1.0',                           # TER less than 1.0%
            'name': 'regex:ESG|Sustainable|Green',   # Names containing ESG, Sustainable, or Green
            'region': ['Europe', 'USA', 'World']    # From specific regions
        }
        filtered_funds = scrappy.filter_funds(conditions)
        print(f"Funds matching all conditions: {len(filtered_funds)}")

        # Example 2: Consecutive filtering - start with low fees, then filter performance
        low_fee_funds = scrappy.filter_funds({'TER': '<=0.5'})
        print(f"Low fee funds (TER <= 0.5%): {len(low_fee_funds)}")

        # Then filter among those for high performance (if performance data available)
        high_perf_low_fee = scrappy.filter_funds(
            conditions={'volume': '>100000000'},  # Volume > 100M
            isins=list(low_fee_funds.index)
        )
        print(f"High volume, low fee funds: {len(high_perf_low_fee)}")

        # Example 3: Filter by ISIN patterns using regex
        isin_pattern_funds = scrappy.filter_funds({
            'index': 'regex:^DE000.*',  # German ISINs
            'TER': '<0.8'
        })
        print(f"German funds with low TER: {len(isin_pattern_funds)}")

        # Example 4: Ranking with specific ISINs only
        print("\n=== New Ranking Function Examples ===")

        # Get a subset of funds first - no more sparplan_only parameter needed
        subset_conditions = {
            'TER': '<0.8',
            'name': 'regex:Index|ETF'  # Focus on index funds/ETFs
        }
        subset_funds = scrappy.filter_funds(subset_conditions)
        subset_isins = list(subset_funds.index[:20])  # Take first 20

        print(f"Ranking among {len(subset_isins)} pre-filtered funds:")

        # Rank only among these specific ISINs
        top_ranked = scrappy.rank_funds(
            isins=subset_isins,
            timespan='1Y',
            limit=5
        )
        print("Top 5 funds from subset:")
        print(top_ranked)

        # Use strategy-based ranking with ISIN filter
        growth_strategy_subset = scrappy.rank_funds_by_strategy(
            strategy='growth',
            isins=subset_isins,
            timespan='1Y',
            limit=3
        )
        print("\nTop 3 growth strategy funds from subset:")
        print(growth_strategy_subset)

        # Example 5: filter_top_performers vs rank_funds comparison
        print("\n=== filter_top_performers vs rank_funds ===")
        
        # Use filter_top_performers for quick screening
        print("Quick screening with filter_top_performers:")
        top_performers = scrappy.filter_top_performers(
            isins=subset_isins,
            by='sharpeRatio',
            limit=10
        )
        print(f"Found {len(top_performers)} top performers")
        
        # Then use rank_funds for sophisticated multi-criteria ranking
        print("\nSophisticated ranking with rank_funds:")
        sophisticated_ranking = scrappy.rank_funds(
            isins=list(top_performers.index),  # Use top performers as input
            criteria={
                'sharpeRatio': 2.0,      # High weight on risk-adjusted returns
                'TER': -1.5,             # Penalize high fees
                'volatility': -0.8       # Penalize high volatility
            },
            limit=5
        )
        print("Multi-criteria ranking results:")
        print(sophisticated_ranking)
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("Check the 'output' directory for saved files.")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 