#!/usr/bin/env python3
"""
Test script to verify the rank_funds functionality works correctly.
"""

import sys
import os
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_rank_funds_functionality():
    """Test the rank_funds functionality with sample data."""
    try:
        from scrappy import Scrappy, FundsDataManager, FundsAnalyzer
        
        # Create sample funds data
        sample_data = pd.DataFrame({
            'name': ['Fund A', 'Fund B', 'Fund C', 'Fund D'],
            'TER': [0.5, 0.75, 1.0, 0.3],
            'sparplan_finanzen_zero': [True, True, False, True],
            'performance': [
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 10.0}],
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 15.0}],
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 8.0}],
                [{'timeSpan': '1Y', 'performanceTimeSpanPct': 12.0}]
            ],
            'risk': [
                [{'timeSpan': '1Y', 'volatility': 12.0, 'sharpeRatio': 0.8}],
                [{'timeSpan': '1Y', 'volatility': 15.0, 'sharpeRatio': 1.0}],
                [{'timeSpan': '1Y', 'volatility': 10.0, 'sharpeRatio': 0.6}],
                [{'timeSpan': '1Y', 'volatility': 11.0, 'sharpeRatio': 1.1}]
            ]
        }, index=['DE000FUND001', 'DE000FUND002', 'DE000FUND003', 'DE000FUND004'])
        
        # Initialize scrappy
        scrappy = Scrappy()
        scrappy.data_manager.add_funds_data(sample_data)
        
        print("✓ Sample data created and loaded")
        
        # Test basic ranking
        ranked_funds = scrappy.rank_funds(
            criteria={'performanceTimeSpanPct': 1.0, 'sharpeRatio': 2.0, 'TER': -1.0},
            timespan='1Y',
            sparplan_only=True
        )
        
        print(f"✓ Basic ranking completed: {len(ranked_funds)} funds ranked")
        print("Top ranked funds:")
        print(ranked_funds.head())
        
        # Test strategy-based ranking
        for strategy in ['balanced', 'growth', 'conservative']:
            try:
                strategy_ranked = scrappy.rank_funds_by_strategy(
                    strategy=strategy,
                    timespan='1Y',
                    sparplan_only=True
                )
                print(f"✓ {strategy} strategy ranking: {len(strategy_ranked)} funds")
            except Exception as e:
                print(f"✗ {strategy} strategy failed: {e}")
        
        # Test with different parameters
        all_funds_ranked = scrappy.rank_funds(
            sparplan_only=False,
            min_criteria={'performanceTimeSpanPct': 5}
        )
        print(f"✓ All funds ranking (no sparplan filter): {len(all_funds_ranked)} funds")
        
        return True
        
    except Exception as e:
        print(f"✗ rank_funds test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyzer_strategies():
    """Test that analyzer strategies are properly defined."""
    try:
        from scrappy import FundsAnalyzer, FundsDataManager
        
        manager = FundsDataManager()
        analyzer = FundsAnalyzer(manager)
        
        # Check that strategies exist
        expected_strategies = ['balanced', 'growth', 'conservative', 'long_term', 'short_term']
        for strategy in expected_strategies:
            assert strategy in analyzer.strategies, f"Missing strategy: {strategy}"
            assert isinstance(analyzer.strategies[strategy], dict), f"Strategy {strategy} should be a dict"
        
        print("✓ All expected strategies are defined")
        
        # Check strategy structure
        for strategy_name, strategy_config in analyzer.strategies.items():
            assert 'performanceTimeSpanPct' in strategy_config, f"Missing performanceTimeSpanPct in {strategy_name}"
            assert 'sharpeRatio' in strategy_config, f"Missing sharpeRatio in {strategy_name}"
            assert 'TER' in strategy_config, f"Missing TER in {strategy_name}"
        
        print("✓ All strategies have required criteria")
        return True
        
    except Exception as e:
        print(f"✗ Strategy test failed: {e}")
        return False

def test_method_availability():
    """Test that all ranking methods are available."""
    try:
        from scrappy import Scrappy
        
        scrappy = Scrappy()
        
        # Check main class methods
        assert hasattr(scrappy, 'rank_funds'), "Missing rank_funds method"
        assert hasattr(scrappy, 'rank_funds_by_strategy'), "Missing rank_funds_by_strategy method"
        
        # Check analyzer methods
        assert hasattr(scrappy.analyzer, 'rank_funds'), "Missing analyzer.rank_funds method"
        assert hasattr(scrappy.analyzer, 'rank_funds_by_strategy'), "Missing analyzer.rank_funds_by_strategy method"
        assert hasattr(scrappy.analyzer, '_extract_ranking_metrics'), "Missing _extract_ranking_metrics method"
        assert hasattr(scrappy.analyzer, '_apply_minimum_criteria'), "Missing _apply_minimum_criteria method"
        assert hasattr(scrappy.analyzer, '_calculate_ranking_scores'), "Missing _calculate_ranking_scores method"
        
        print("✓ All ranking methods are available")
        return True
        
    except Exception as e:
        print(f"✗ Method availability test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing rank_funds functionality...")
    print("=" * 50)
    
    tests = [
        test_method_availability,
        test_analyzer_strategies,
        test_rank_funds_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All rank_funds tests passed!")
    else:
        print("⚠️  Some tests failed - please check the output above")

if __name__ == "__main__":
    main() 