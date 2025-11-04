"""
Download Statistics Tracker
============================
Tracks and aggregates download statistics across all sources
"""

from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class DownloadStats:
    """Track download statistics"""
    
    def __init__(self):
        self.results_by_source = {}
        self.errors = {}
        self.start_time = datetime.now()
    
    def add_results(self, source: str, results: Dict[str, int]):
        """
        Add results from a downloader
        
        Args:
            source: Source name (e.g., 'sec', 'earnings')
            results: Dictionary with 'success', 'failed', 'skipped', 'total_size'
        """
        self.results_by_source[source] = results
    
    def add_error(self, source: str, error: str):
        """
        Add an error for a source
        
        Args:
            source: Source name
            error: Error message
        """
        if source not in self.errors:
            self.errors[source] = []
        self.errors[source].append(error)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all download statistics
        
        Returns:
            Summary dictionary
        """
        total_success = sum(r.get('success', 0) for r in self.results_by_source.values())
        total_failed = sum(r.get('failed', 0) for r in self.results_by_source.values())
        total_skipped = sum(r.get('skipped', 0) for r in self.results_by_source.values())
        total_size = sum(r.get('total_size', 0) for r in self.results_by_source.values())
        
        total_attempts = total_success + total_failed
        success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        return {
            'total_success': total_success,
            'total_failed': total_failed,
            'total_skipped': total_skipped,
            'total_size_mb': total_size / (1024 * 1024),
            'success_rate': success_rate,
            'duration_seconds': duration,
            'by_source': {
                source: {
                    'success': results.get('success', 0),
                    'failed': results.get('failed', 0),
                    'skipped': results.get('skipped', 0),
                    'size_mb': results.get('total_size', 0) / (1024 * 1024)
                }
                for source, results in self.results_by_source.items()
            },
            'errors': self.errors,
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
    
    def save_summary(self, filepath: Path):
        """
        Save summary to JSON file
        
        Args:
            filepath: Path to save summary
        """
        summary = self.get_summary()
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def print_progress(self):
        """Print current progress"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("DOWNLOAD PROGRESS")
        print("=" * 60)
        
        for source, data in summary['by_source'].items():
            print(f"{source.upper()}: {data['success']} docs ({data['size_mb']:.1f} MB)")
        
        print("-" * 60)
        print(f"TOTAL: {summary['total_success']} docs ({summary['total_size_mb']:.1f} MB)")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print("=" * 60 + "\n")
