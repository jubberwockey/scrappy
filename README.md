# Scrappy

Scrappy is a (somewhat crappy) Python library for analyzing mutual funds and ETF data. Other python libraries focus on the analysis of individual stocks, but *literally none* of them analyzes funds and ETFs. Scrappy provides web scraping capabilities to collect fund metadata and time-series data, along with basic analysis and visualization tools specifically designed for investment funds rather than individual stocks.

## Installation

### Prerequisites
- Python 3.8+

### Quick Install
```bash
# Clone the repository
git clone https://github.com/yourusername/scrappy.git
cd scrappy

# Create and activate conda environment
conda create -n scrappy python=3.8 pip
conda activate scrappy

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
```
jupyter        # Notebook environment
requests       # Web requests
numpy          # Numerical computations
pandas         # Data manipulation
dirtyjson      # Flexible JSON parsing
plotly         # Interactive visualizations
seaborn        # Statistical plotting
scipy          # Scientific computing
```

## Usage Guide

### Quick Start
```python
from src.scrappy import Scrappy

# Initialize with data paths
s = Scrappy(
    funds_overview_path='data/funds_overview_sample.csv',
    performance_path='data/performance_sample.csv',
    timeseries_path='data/timeseries_sample.csv'
)

# Download funds data
funds_data = s.download_funds_overview()
```

## Project Structure

```
scrappy/
├── src/
│   ├── scrappy.py       # Main library with analysis classes
│   └── config.py        # Configuration settings
├── data/
│   ├── funds_overview_sample.csv   # Sample fund metadata
│   ├── performance_sample.csv      # Sample performance data
│   ├── timeseries_sample.csv       # Sample time series data
│   └── downloadable-instruments.csv # Available instruments
├── tests/
│   ├── test_basic_structure.py     # Basic structure tests
│   ├── test_data_scraper.py        # Data scraper tests
│   ├── test_funds_data_manager.py  # Data manager tests
│   └── test_rank_funds.py          # Fund ranking tests
└── requirements.txt             # Python dependencies
```
