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
    print("1. Downloading ESG/sustainable funds data...")
    try:
        # Using category shortcut
        esg_funds = scrappy.download_funds_overview(
            filter_ids='esg',  # Use ESG category shortcut
            limit=50
        )
        print(f"Downloaded {len(esg_funds)} ESG funds")
        print(f"ESG column values: {esg_funds['esg'].value_counts()}")
        print(esg_funds.head())
        
        # Download bond/fixed income funds
        print("\n1b. Downloading bond/fixed income funds...")
        renten_funds = scrappy.download_funds_overview(
            filter_ids='renten',  # Use renten category shortcut
            limit=30
        )
        print(f"Downloaded {len(renten_funds)} bond funds")
        print(f"Renten column values: {renten_funds['renten'].value_counts()}")
        
        # Download with additional options
        print("\n1c. Downloading large-volume ESG funds...")
        large_esg_funds = scrappy.download_funds_overview(
            filter_ids='esg',
            limit=25,
            additional_options="minVolumeRange=100000000;999999999999"  # Min 100M volume
        )
        print(f"Downloaded {len(large_esg_funds)} large ESG funds")
        
        # Combine all funds
        all_funds = pd.concat([esg_funds, renten_funds], axis=0)
        all_funds = all_funds[~all_funds.index.duplicated(keep='last')]
        scrappy.data_manager.add_funds_data(all_funds)
        
    except Exception as e:
        print(f"Error downloading data: {e}")
        # For demo purposes, create sample data
        funds_data = create_sample_funds_data()
        scrappy.data_manager.add_funds_data(funds_data)
    
    # 2. Search for specific funds using new filter capabilities
    print("\n2. Searching for ESG funds using filter_funds...")
    esg_filter_funds = scrappy.filter_funds({
        'esg': True,
        'TER': '<0.8'
    })
    print(f"Found {len(esg_filter_funds)} low-cost ESG funds")
    
    # 3. Filter funds by category and other criteria
    print("\n3. Filtering bond funds with low risk...")
    try:
        bond_funds = scrappy.filter_funds({
            'renten': True,
            'name': 'regex:Bond|Anleihe|Renten'
        })
        print(f"Found {len(bond_funds)} bond funds")
    except Exception as e:
        print(f"Could not filter bond funds: {e}")
    
    # 4. Extract performance metrics
    print("\n4. Extracting performance metrics...")
    performance_data = scrappy.extract_performance()
    if not performance_data.empty:
        print(performance_data.head())
    
    # 5. Demonstrate category-based analysis
    print("\n5. Category-based fund analysis...")
    try:
        funds_overview = scrappy.funds_overview
        if not funds_overview.empty and 'esg' in funds_overview.columns:
            print(f"ESG funds: {funds_overview['esg'].sum()}")
            print(f"Bond funds: {funds_overview['renten'].sum()}")
            print(f"Benchmark funds: {funds_overview['benchmark'].sum()}")
            
            # Compare average TER by category
            if 'TER' in funds_overview.columns:
                esg_ter = funds_overview[funds_overview['esg']]['TER'].mean()
                renten_ter = funds_overview[funds_overview['renten']]['TER'].mean()
                print(f"Average TER - ESG: {esg_ter:.3f}%, Bonds: {renten_ter:.3f}%")
    except Exception as e:
        print(f"Could not perform category analysis: {e}")
    
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
    
    # 1. Demonstrate large download with volatility-based splitting
    print("1. Large download with volatility-based splitting...")
    try:
        # This should trigger volatility-based splitting
        large_dataset = scrappy.download_funds_overview(
            filter_ids='esg',
            limit=2500,  # This will trigger splitting
            additional_options="minVolumeRange=10000000;999999999999"  # Min 10M volume
        )
        print(f"Downloaded {len(large_dataset)} funds with volatility-based splitting")
        
        # Analyze volatility distribution
        if 'risk' in large_dataset.columns:
            print("Volatility distribution analysis would go here...")
        
    except Exception as e:
        print(f"Large download example failed: {e}")
    
    # 2. Integrate broker availability data
    print("\n2. Integrating broker availability data...")
    try:
        scrappy.join_finanzen_zero_data('data/downloadable-instruments.csv')
        print("Broker data integrated successfully")
        
        # Show funds available with zero fees by category
        funds_overview = scrappy.funds_overview
        if not funds_overview.empty and 'finanzen_zero' in funds_overview.columns:
            esg_zero_fee = scrappy.filter_funds({
                'esg': True,
                'finanzen_zero': True
            })
            print(f"ESG funds with zero broker fees: {len(esg_zero_fee)}")
            
            renten_zero_fee = scrappy.filter_funds({
                'renten': True, 
                'finanzen_zero': True
            })
            print(f"Bond funds with zero broker fees: {len(renten_zero_fee)}")
            
    except Exception as e:
        print(f"Error integrating broker data: {e}")
    
    # 3. Custom analysis: Compare categories
    print("\n3. Cross-category fund analysis...")
    try:
        funds_overview = scrappy.funds_overview
        
        if not funds_overview.empty:
            # Category-based filtering and comparison
            categories = ['esg', 'renten', 'benchmark']
            category_stats = {}
            
            for category in categories:
                if category in funds_overview.columns:
                    cat_funds = funds_overview[funds_overview[category] == True]
                    if not cat_funds.empty and 'TER' in cat_funds.columns:
                        category_stats[category] = {
                            'count': len(cat_funds),
                            'avg_ter': cat_funds['TER'].mean(),
                            'median_ter': cat_funds['TER'].median(),
                            'min_ter': cat_funds['TER'].min(),
                            'max_ter': cat_funds['TER'].max()
                        }
            
            print("Category comparison:")
            for cat, stats in category_stats.items():
                print(f"{cat.upper()}: {stats['count']} funds, "
                      f"TER avg: {stats['avg_ter']:.3f}%, "
                      f"range: {stats['min_ter']:.3f}%-{stats['max_ter']:.3f}%")
                      
            # Find funds that might be in multiple categories
            if 'esg' in funds_overview.columns and 'renten' in funds_overview.columns:
                esg_bonds = funds_overview[
                    (funds_overview['esg'] == True) & 
                    (funds_overview['renten'] == True)
                ]
                print(f"Funds that are both ESG and bonds: {len(esg_bonds)}")
    
    except Exception as e:
        print(f"Error in cross-category analysis: {e}")
    
    # 4. Performance ranking across different categories
    print("\n4. Category-based performance analysis...")
    try:
        # Rank ESG funds
        esg_funds = scrappy.filter_funds({'esg': True})
        if not esg_funds.empty:
            esg_ranking = scrappy.rank_funds(
                isins=list(esg_funds.index[:50]),  # Limit to first 50 for demo
                timespan='1Y',
                limit=5
            )
            print("Top 5 ESG funds:")
            print(esg_ranking)
        
        # Rank bond funds  
        bond_funds = scrappy.filter_funds({'renten': True})
        if not bond_funds.empty:
            bond_ranking = scrappy.rank_funds_by_strategy(
                strategy='conservative',  # Conservative strategy for bonds
                isins=list(bond_funds.index[:50]),
                limit=5
            )
            print("\nTop 5 bond funds (conservative strategy):")
            print(bond_ranking)
    
    except Exception as e:
        print(f"Error in category-based performance analysis: {e}")


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