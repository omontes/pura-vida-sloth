"""
Checkpoint Manager
==================
Manages download progress checkpoints for resume capability
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from .config import Config

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoints for download progress tracking and resume capability
    """

    def __init__(self, output_dir: Path, downloader_name: str):
        """
        Initialize checkpoint manager

        Args:
            output_dir: Output directory for downloads
            downloader_name: Name of the downloader (e.g., 'sec', 'earnings')
        """
        self.output_dir = Path(output_dir)
        self.downloader_name = downloader_name
        self.checkpoint_file = self.output_dir / f".checkpoint_{downloader_name}.json"
        self.checkpoint_data = self._load_checkpoint()
        self.save_interval = Config.CHECKPOINT_INTERVAL

        # Initialize checkpoint structure if new
        if not self.checkpoint_data:
            self.checkpoint_data = {
                'downloader': downloader_name,
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'completed_items': [],
                'failed_items': [],
                'skipped_items': [],
                'stats': {
                    'total_processed': 0,
                    'total_success': 0,
                    'total_failed': 0,
                    'total_skipped': 0
                },
                'metadata': {}
            }

    def _load_checkpoint(self) -> Dict[str, Any]:
        """
        Load checkpoint from file

        Returns:
            Checkpoint data dictionary
        """
        if not Config.ENABLE_CHECKPOINTS:
            return {}

        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Loaded checkpoint for {self.downloader_name}: "
                           f"{data['stats']['total_processed']} items processed")
                return data
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}. Starting fresh.")
                return {}
        return {}

    def save_checkpoint(self, force: bool = False):
        """
        Save checkpoint to file

        Args:
            force: Force save even if interval not reached
        """
        if not Config.ENABLE_CHECKPOINTS:
            return

        try:
            # Update timestamp
            self.checkpoint_data['last_updated'] = datetime.now().isoformat()

            # Create output directory if doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Checkpoint saved: {self.checkpoint_data['stats']['total_processed']} items")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def is_completed(self, item_id: str) -> bool:
        """
        Check if item was already completed

        Args:
            item_id: Unique identifier for item

        Returns:
            True if already completed
        """
        return item_id in self.checkpoint_data.get('completed_items', [])

    def is_failed(self, item_id: str) -> bool:
        """
        Check if item previously failed

        Args:
            item_id: Unique identifier for item

        Returns:
            True if previously failed
        """
        return item_id in self.checkpoint_data.get('failed_items', [])

    def is_skipped(self, item_id: str) -> bool:
        """
        Check if item was skipped

        Args:
            item_id: Unique identifier for item

        Returns:
            True if was skipped
        """
        return item_id in self.checkpoint_data.get('skipped_items', [])

    def mark_completed(self, item_id: str, metadata: Dict[str, Any] = None):
        """
        Mark item as completed

        Args:
            item_id: Unique identifier for item
            metadata: Optional metadata about the item
        """
        if item_id not in self.checkpoint_data['completed_items']:
            self.checkpoint_data['completed_items'].append(item_id)
            self.checkpoint_data['stats']['total_success'] += 1
            self.checkpoint_data['stats']['total_processed'] += 1

            # Store metadata if provided
            if metadata:
                if 'item_metadata' not in self.checkpoint_data:
                    self.checkpoint_data['item_metadata'] = {}
                self.checkpoint_data['item_metadata'][item_id] = metadata

            # Auto-save at intervals
            if self.checkpoint_data['stats']['total_processed'] % self.save_interval == 0:
                self.save_checkpoint()

    def mark_failed(self, item_id: str, error: str = None):
        """
        Mark item as failed

        Args:
            item_id: Unique identifier for item
            error: Optional error message
        """
        if item_id not in self.checkpoint_data['failed_items']:
            self.checkpoint_data['failed_items'].append(item_id)
            self.checkpoint_data['stats']['total_failed'] += 1
            self.checkpoint_data['stats']['total_processed'] += 1

            # Store error message
            if error:
                if 'error_log' not in self.checkpoint_data:
                    self.checkpoint_data['error_log'] = {}
                self.checkpoint_data['error_log'][item_id] = {
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }

            # Auto-save at intervals
            if self.checkpoint_data['stats']['total_processed'] % self.save_interval == 0:
                self.save_checkpoint()

    def mark_skipped(self, item_id: str, reason: str = None):
        """
        Mark item as skipped

        Args:
            item_id: Unique identifier for item
            reason: Optional reason for skipping
        """
        if item_id not in self.checkpoint_data['skipped_items']:
            self.checkpoint_data['skipped_items'].append(item_id)
            self.checkpoint_data['stats']['total_skipped'] += 1
            self.checkpoint_data['stats']['total_processed'] += 1

            # Store skip reason
            if reason:
                if 'skip_log' not in self.checkpoint_data:
                    self.checkpoint_data['skip_log'] = {}
                self.checkpoint_data['skip_log'][item_id] = reason

            # Auto-save at intervals
            if self.checkpoint_data['stats']['total_processed'] % self.save_interval == 0:
                self.save_checkpoint()

    def get_stats(self) -> Dict[str, int]:
        """
        Get current statistics

        Returns:
            Statistics dictionary
        """
        return self.checkpoint_data.get('stats', {}).copy()

    def get_completed_items(self) -> List[str]:
        """
        Get list of completed item IDs

        Returns:
            List of item IDs
        """
        return self.checkpoint_data.get('completed_items', []).copy()

    def get_failed_items(self) -> List[str]:
        """
        Get list of failed item IDs

        Returns:
            List of item IDs
        """
        return self.checkpoint_data.get('failed_items', []).copy()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value
        """
        return self.checkpoint_data.get('metadata', {}).get(key, default)

    def set_metadata(self, key: str, value: Any):
        """
        Set metadata value

        Args:
            key: Metadata key
            value: Metadata value
        """
        if 'metadata' not in self.checkpoint_data:
            self.checkpoint_data['metadata'] = {}
        self.checkpoint_data['metadata'][key] = value

    def clear_checkpoint(self):
        """Clear checkpoint file and reset data"""
        self.checkpoint_data = {
            'downloader': self.downloader_name,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'completed_items': [],
            'failed_items': [],
            'skipped_items': [],
            'stats': {
                'total_processed': 0,
                'total_success': 0,
                'total_failed': 0,
                'total_skipped': 0
            },
            'metadata': {}
        }

        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                logger.info(f"Checkpoint cleared for {self.downloader_name}")
            except Exception as e:
                logger.warning(f"Could not delete checkpoint file: {e}")

    def finalize(self):
        """Finalize checkpoint (save and optionally clean up)"""
        self.save_checkpoint(force=True)

        # Optionally delete checkpoint if everything succeeded
        stats = self.get_stats()
        if stats.get('total_failed', 0) == 0:
            logger.info(f"All items processed successfully. Checkpoint saved at: {self.checkpoint_file}")
        else:
            logger.warning(f"{stats.get('total_failed', 0)} items failed. "
                          f"Checkpoint saved for potential retry: {self.checkpoint_file}")

    def get_resume_info(self) -> Optional[str]:
        """
        Get resume information string

        Returns:
            Human-readable resume information
        """
        if not self.checkpoint_data or not self.checkpoint_data.get('stats', {}).get('total_processed'):
            return None

        stats = self.checkpoint_data['stats']
        last_updated = self.checkpoint_data.get('last_updated', 'Unknown')

        return (f"Resuming from checkpoint:\n"
                f"  Last updated: {last_updated}\n"
                f"  Processed: {stats['total_processed']} items\n"
                f"  Success: {stats['total_success']}, "
                f"Failed: {stats['total_failed']}, "
                f"Skipped: {stats['total_skipped']}")

    def should_retry_failed(self, item_id: str, max_attempts: int = 3) -> bool:
        """
        Check if failed item should be retried

        Args:
            item_id: Item identifier
            max_attempts: Maximum retry attempts

        Returns:
            True if should retry
        """
        if 'retry_count' not in self.checkpoint_data:
            self.checkpoint_data['retry_count'] = {}

        current_attempts = self.checkpoint_data['retry_count'].get(item_id, 0)
        return current_attempts < max_attempts

    def increment_retry_count(self, item_id: str):
        """
        Increment retry count for an item

        Args:
            item_id: Item identifier
        """
        if 'retry_count' not in self.checkpoint_data:
            self.checkpoint_data['retry_count'] = {}

        self.checkpoint_data['retry_count'][item_id] = \
            self.checkpoint_data['retry_count'].get(item_id, 0) + 1
