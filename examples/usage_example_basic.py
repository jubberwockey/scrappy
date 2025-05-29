import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from scrappy import Scrappy


def basic_usage_example(s):
    """Basic usage example showing core functionality."""

    funds_data = s.download_funds_overview(
        # filter_ids=[5634, 5703, 5582],  # Sustainability, Alternative Energy, Ecology
        # limit=50
    )
    print(f"Downloaded {len(funds_data)} funds")
    print(funds_data.head())



def main():
    """Main function demonstrating all examples."""
    
    s = Scrappy(
        funds_overview_path='data/funds_overview_sample.csv',
        performance_path='data/performance_sample.csv',
        timeseries_path='data/timeseries_sample.csv'
    )

    try:
        # Basic usage
        basic_usage_example(s)
        
        # Visualizations
        # visualization_examples(scrappy)
        
        # # Advanced analysis
        # advanced_analysis_example(scrappy)
        
        # # Data management
        # data_management_example(scrappy)
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
