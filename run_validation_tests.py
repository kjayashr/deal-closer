#!/usr/bin/env python3
"""
Validation Test Runner
Runs all 10 validation tests and generates a report.
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_validation_suite import ValidationTracker, TestValidationSuite
import pytest


def generate_report(tracker: ValidationTracker, output_file: str = "validation_report.json"):
    """Generate validation report."""
    summary = tracker.get_summary()
    
    # Add timestamp
    summary["timestamp"] = datetime.now().isoformat()
    summary["total_time_seconds"] = sum(r.get("duration", 0) for r in summary["results"])
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print("\n" + "="*80)
    print("VALIDATION TEST REPORT")
    print("="*80)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']} ✅")
    print(f"Failed: {summary['failed']} ❌")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Time: {summary['total_time_seconds']:.2f}s")
    print("\n" + "-"*80)
    
    # Print individual test results
    for result in summary["results"]:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status}: {result['test_name']}")
        if result["errors"]:
            for error in result["errors"]:
                print(f"    - {error}")
    
    print("\n" + "="*80)
    print(f"Full report saved to: {output_file}")
    print("="*80 + "\n")
    
    return summary


def main():
    """Main test runner."""
    print("Starting Validation Test Suite...")
    print("="*80)
    print("Make sure the API server is running on http://localhost:8000")
    print("Start with: uvicorn sales_agent.api.main:app --reload")
    print("="*80 + "\n")
    
    # Run pytest with our test suite
    # Use pytest's async support
    exit_code = pytest.main([
        "-v",
        "-s",
        "--tb=short",
        "tests/test_validation_suite.py"
    ])
    
    # Import tracker after tests run
    from tests.test_validation_suite import tracker
    
    # Generate report
    report = generate_report(tracker)
    
    # Return exit code based on results
    if report["failed"] > 0:
        print(f"\n⚠️  {report['failed']} test(s) failed. Review the report for details.")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

