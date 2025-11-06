"""
Generic ADE Parser for Regulatory Documents

Uses Landing AI's Advanced Document Extraction (ADE) API to parse PDFs
from any industry folder into structured markdown and JSON outputs.

Example usage:
    python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs
"""

import os
import json
import argparse
import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

import aiohttp
import aiofiles
from tqdm.asyncio import tqdm as async_tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager

# Load environment variables
load_dotenv()


class ADEParser:
    """
    Generic parser for extracting structured content from PDFs using Landing AI's ADE API.

    Processes all PDFs in a specified directory and saves outputs as:
    - Markdown files: {output_dir}/markdown/{filename}.md
    - JSON files: {output_dir}/json/{filename}.json
    """

    # Landing AI ADE API endpoint
    API_ENDPOINT = "https://api.va.landing.ai/v1/ade/parse"

    # Minimum PDF file size (1 KB) to validate files
    MIN_PDF_SIZE = 1024

    def __init__(
        self,
        pdf_dir: str,
        api_key: Optional[str] = None,
        model: str = "dpt-2-latest",
        output_dir_name: str = "ade_parsed_results",
        max_concurrent: int = 5
    ):
        """
        Initialize the ADE Parser.

        Args:
            pdf_dir: Path to directory containing PDF files
            api_key: Landing AI API key (defaults to LANDING_API_KEY from .env)
            model: ADE model version to use (default: dpt-2-latest)
            output_dir_name: Name of output directory (default: ade_parsed_results)
            max_concurrent: Maximum number of concurrent API requests (default: 5)
        """
        self.pdf_dir = Path(pdf_dir)
        self.model = model

        # Validate PDF directory exists
        if not self.pdf_dir.exists():
            raise ValueError(f"PDF directory does not exist: {self.pdf_dir}")
        if not self.pdf_dir.is_dir():
            raise ValueError(f"Path is not a directory: {self.pdf_dir}")

        # Set up output directory structure
        # Output goes in sibling folder to pdfs/
        self.output_dir = self.pdf_dir.parent / output_dir_name
        self.markdown_dir = self.output_dir / "markdown"
        self.json_dir = self.output_dir / "json"
        self.checkpoint_dir = self.output_dir / "checkpoints"

        # Create all output directories
        for dir_path in [self.markdown_dir, self.json_dir, self.checkpoint_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.logger = setup_logger(
            "ADEParser",
            self.output_dir / "ade_parser.log"
        )

        # Set up checkpoint manager
        self.checkpoint = CheckpointManager(
            self.checkpoint_dir,
            'ade_parser'
        )

        # Get API key from environment or parameter
        self.api_key = api_key or os.getenv('LANDING_API_KEY') or os.getenv('LANDING_API_LEY')
        if not self.api_key:
            raise ValueError(
                "Landing AI API key not found. Set LANDING_API_KEY in .env or pass via api_key parameter."
            )

        # Initialize statistics
        self.stats = {
            'total_pdfs': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'failed_items': []
        }

        # Async concurrency control
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        self.logger.info(f"Initialized ADEParser")
        self.logger.info(f"PDF directory: {self.pdf_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Max concurrent requests: {self.max_concurrent}")

    def _get_pdf_files(self) -> list[Path]:
        """
        Get all PDF files from the input directory.

        Returns:
            List of Path objects for PDF files
        """
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        self.logger.info(f"Found {len(pdf_files)} PDF files in {self.pdf_dir}")
        return sorted(pdf_files)

    def _validate_pdf(self, pdf_path: Path) -> bool:
        """
        Validate that the PDF file is readable and has valid PDF content.

        Checks:
        1. File extension is .pdf
        2. File exists and is readable
        3. File size is above minimum threshold
        4. File starts with PDF magic bytes (%PDF-)

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check file extension
            if pdf_path.suffix.lower() != '.pdf':
                self.logger.warning(f"Not a PDF file (wrong extension): {pdf_path.name}")
                return False

            # Check file exists
            if not pdf_path.exists():
                self.logger.warning(f"PDF does not exist: {pdf_path}")
                return False

            # Check file size
            file_size = pdf_path.stat().st_size
            if file_size < self.MIN_PDF_SIZE:
                self.logger.warning(f"PDF too small ({file_size} bytes): {pdf_path.name}")
                return False

            # Check PDF magic bytes (validate it's actually a PDF)
            with open(pdf_path, 'rb') as f:
                header = f.read(5)
                if not header.startswith(b'%PDF-'):
                    self.logger.warning(
                        f"Not a valid PDF file (missing magic bytes): {pdf_path.name}"
                    )
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating PDF {pdf_path.name}: {e}")
            return False

    def parse_pdf(self, pdf_path: Path) -> Optional[Dict]:
        """
        Parse a single PDF using Landing AI's ADE API.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Parsed response dict with 'markdown' and full JSON data, or None on failure
        """
        try:
            self.logger.info(f"Parsing PDF: {pdf_path.name}")

            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            # Open and send PDF file
            with open(pdf_path, 'rb') as f:
                files = {
                    'document': (pdf_path.name, f, 'application/pdf')
                }
                data = {
                    'model': self.model
                }

                # Make API request
                response = requests.post(
                    self.API_ENDPOINT,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout for large PDFs
                )

            # Check response status
            if response.status_code != 200:
                self.logger.error(
                    f"API request failed for {pdf_path.name}: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                return None

            # Parse JSON response
            result = response.json()
            self.logger.info(f"Successfully parsed {pdf_path.name}")

            # Log metadata if available
            if 'metadata' in result:
                metadata = result['metadata']
                self.logger.info(
                    f"  Pages: {metadata.get('page_count', 'N/A')}, "
                    f"Duration: {metadata.get('duration_ms', 'N/A')}ms, "
                    f"Credits: {metadata.get('credit', 'N/A')}"
                )

            return result

        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout parsing {pdf_path.name} (exceeded 5 minutes)")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error parsing {pdf_path.name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing {pdf_path.name}: {e}")
            return None

    async def parse_pdf_async(self, pdf_path: Path, session: aiohttp.ClientSession) -> Optional[Dict]:
        """
        Parse a single PDF using Landing AI's ADE API (async version).

        Args:
            pdf_path: Path to PDF file
            session: aiohttp ClientSession for making requests

        Returns:
            Parsed response dict with 'markdown' and full JSON data, or None on failure
        """
        async with self.semaphore:  # Limit concurrent requests
            try:
                self.logger.info(f"Parsing PDF: {pdf_path.name}")

                # Prepare API request headers
                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }

                # Read PDF file
                async with aiofiles.open(pdf_path, 'rb') as f:
                    pdf_content = await f.read()

                # Prepare form data
                form_data = aiohttp.FormData()
                form_data.add_field(
                    'document',
                    pdf_content,
                    filename=pdf_path.name,
                    content_type='application/pdf'
                )
                form_data.add_field('model', self.model)

                # Make async API request
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                async with session.post(
                    self.API_ENDPOINT,
                    headers=headers,
                    data=form_data,
                    timeout=timeout
                ) as response:
                    # Check response status
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(
                            f"API request failed for {pdf_path.name}: "
                            f"Status {response.status}, Response: {error_text}"
                        )
                        return None

                    # Parse JSON response
                    result = await response.json()
                    self.logger.info(f"Successfully parsed {pdf_path.name}")

                    # Log metadata if available
                    if 'metadata' in result:
                        metadata = result['metadata']
                        self.logger.info(
                            f"  Pages: {metadata.get('page_count', 'N/A')}, "
                            f"Duration: {metadata.get('duration_ms', 'N/A')}ms, "
                            f"Credits: {metadata.get('credit', 'N/A')}"
                        )

                    return result

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout parsing {pdf_path.name} (exceeded 5 minutes)")
                return None
            except aiohttp.ClientError as e:
                self.logger.error(f"Client error parsing {pdf_path.name}: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error parsing {pdf_path.name}: {e}")
                return None

    def save_results(self, pdf_path: Path, parsed_data: Dict) -> Tuple[bool, bool]:
        """
        Save parsed results as markdown and JSON files.

        Args:
            pdf_path: Original PDF path (used for naming output files)
            parsed_data: Parsed response from ADE API

        Returns:
            Tuple of (markdown_success, json_success)
        """
        # Use PDF filename (without extension) for output files
        base_name = pdf_path.stem

        markdown_success = False
        json_success = False

        # Save markdown file
        try:
            markdown_content = parsed_data.get('markdown', '')
            if markdown_content:
                markdown_path = self.markdown_dir / f"{base_name}.md"
                markdown_path.write_text(markdown_content, encoding='utf-8')
                self.logger.info(f"Saved markdown: {markdown_path.name}")
                markdown_success = True
            else:
                self.logger.warning(f"No markdown content for {pdf_path.name}")
        except Exception as e:
            self.logger.error(f"Error saving markdown for {pdf_path.name}: {e}")

        # Save full JSON file
        try:
            json_path = self.json_dir / f"{base_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved JSON: {json_path.name}")
            json_success = True
        except Exception as e:
            self.logger.error(f"Error saving JSON for {pdf_path.name}: {e}")

        return markdown_success, json_success

    def process_directory(self) -> Dict:
        """
        Process all PDFs in the input directory.

        Returns:
            Statistics dictionary with processing results
        """
        pdf_files = self._get_pdf_files()
        self.stats['total_pdfs'] = len(pdf_files)

        if not pdf_files:
            self.logger.warning("No PDF files found to process")
            return self.stats

        self.logger.info(f"Starting batch processing of {len(pdf_files)} PDFs")

        # Process each PDF with progress bar
        with tqdm(total=len(pdf_files), desc="Parsing PDFs", unit="pdf") as pbar:
            for pdf_path in pdf_files:
                # Check if already processed
                if self.checkpoint.is_completed(pdf_path.name):
                    self.logger.info(f"Skipping already processed: {pdf_path.name}")
                    self.stats['skipped'] += 1
                    pbar.update(1)
                    continue

                # Validate PDF
                if not self._validate_pdf(pdf_path):
                    self.logger.warning(f"Skipping invalid PDF: {pdf_path.name}")
                    self.checkpoint.mark_failed(pdf_path.name, "Invalid PDF file")
                    self.stats['failed'] += 1
                    self.stats['failed_items'].append({
                        'file': pdf_path.name,
                        'reason': 'Invalid PDF file'
                    })
                    pbar.update(1)
                    continue

                # Parse PDF
                parsed_data = self.parse_pdf(pdf_path)

                if parsed_data is None:
                    self.logger.error(f"Failed to parse: {pdf_path.name}")
                    self.checkpoint.mark_failed(pdf_path.name, "API parsing failed")
                    self.stats['failed'] += 1
                    self.stats['failed_items'].append({
                        'file': pdf_path.name,
                        'reason': 'API parsing failed'
                    })
                    pbar.update(1)
                    continue

                # Save results
                markdown_ok, json_ok = self.save_results(pdf_path, parsed_data)

                if markdown_ok and json_ok:
                    # Mark as successfully completed
                    metadata = parsed_data.get('metadata', {})
                    self.checkpoint.mark_completed(pdf_path.name, metadata={
                        'page_count': metadata.get('page_count'),
                        'duration_ms': metadata.get('duration_ms'),
                        'credit': metadata.get('credit')
                    })
                    self.stats['successful'] += 1
                else:
                    # Mark as failed if file saving issues
                    self.checkpoint.mark_failed(pdf_path.name, "Failed to save outputs")
                    self.stats['failed'] += 1
                    self.stats['failed_items'].append({
                        'file': pdf_path.name,
                        'reason': 'Failed to save outputs'
                    })

                # Update progress bar
                success_rate = (self.stats['successful'] / (self.stats['successful'] + self.stats['failed']) * 100) if (self.stats['successful'] + self.stats['failed']) > 0 else 0
                pbar.set_postfix({
                    'success': self.stats['successful'],
                    'failed': self.stats['failed'],
                    'rate': f"{success_rate:.1f}%"
                })
                pbar.update(1)

        self.logger.info("Batch processing completed")
        self.logger.info(f"Total: {self.stats['total_pdfs']}, Successful: {self.stats['successful']}, Failed: {self.stats['failed']}, Skipped: {self.stats['skipped']}")

        return self.stats

    async def process_single_pdf_async(self, pdf_path: Path, session: aiohttp.ClientSession, pbar) -> None:
        """
        Process a single PDF asynchronously (helper for process_directory_async).

        Args:
            pdf_path: Path to PDF file
            session: aiohttp ClientSession
            pbar: Progress bar to update
        """
        # Check if already processed
        if self.checkpoint.is_completed(pdf_path.name):
            self.logger.info(f"Skipping already processed: {pdf_path.name}")
            self.stats['skipped'] += 1
            pbar.update(1)
            return

        # Validate PDF
        if not self._validate_pdf(pdf_path):
            self.logger.warning(f"Skipping invalid PDF: {pdf_path.name}")
            self.checkpoint.mark_failed(pdf_path.name, "Invalid PDF file")
            self.stats['failed'] += 1
            self.stats['failed_items'].append({
                'file': pdf_path.name,
                'reason': 'Invalid PDF file'
            })
            pbar.update(1)
            return

        # Parse PDF
        parsed_data = await self.parse_pdf_async(pdf_path, session)

        if parsed_data is None:
            self.logger.error(f"Failed to parse: {pdf_path.name}")
            self.checkpoint.mark_failed(pdf_path.name, "API parsing failed")
            self.stats['failed'] += 1
            self.stats['failed_items'].append({
                'file': pdf_path.name,
                'reason': 'API parsing failed'
            })
            pbar.update(1)
            return

        # Save results
        markdown_ok, json_ok = self.save_results(pdf_path, parsed_data)

        if markdown_ok and json_ok:
            # Mark as successfully completed
            metadata = parsed_data.get('metadata', {})
            self.checkpoint.mark_completed(pdf_path.name, metadata={
                'page_count': metadata.get('page_count'),
                'duration_ms': metadata.get('duration_ms'),
                'credit': metadata.get('credit')
            })
            self.stats['successful'] += 1
        else:
            # Mark as failed if file saving issues
            self.checkpoint.mark_failed(pdf_path.name, "Failed to save outputs")
            self.stats['failed'] += 1
            self.stats['failed_items'].append({
                'file': pdf_path.name,
                'reason': 'Failed to save outputs'
            })

        # Update progress bar
        success_rate = (self.stats['successful'] / (self.stats['successful'] + self.stats['failed']) * 100) if (self.stats['successful'] + self.stats['failed']) > 0 else 0
        pbar.set_postfix({
            'success': self.stats['successful'],
            'failed': self.stats['failed'],
            'rate': f"{success_rate:.1f}%"
        })
        pbar.update(1)

    async def process_directory_async(self) -> Dict:
        """
        Process all PDFs in the input directory using async concurrent processing.

        Returns:
            Statistics dictionary with processing results
        """
        pdf_files = self._get_pdf_files()
        self.stats['total_pdfs'] = len(pdf_files)

        if not pdf_files:
            self.logger.warning("No PDF files found to process")
            return self.stats

        self.logger.info(f"Starting async batch processing of {len(pdf_files)} PDFs")
        self.logger.info(f"Processing up to {self.max_concurrent} PDFs concurrently")

        # Create aiohttp session
        async with aiohttp.ClientSession() as session:
            # Create progress bar
            pbar = async_tqdm(total=len(pdf_files), desc="Parsing PDFs", unit="pdf")

            # Process all PDFs concurrently
            tasks = [
                self.process_single_pdf_async(pdf_path, session, pbar)
                for pdf_path in pdf_files
            ]
            await asyncio.gather(*tasks)

            pbar.close()

        self.logger.info("Async batch processing completed")
        self.logger.info(f"Total: {self.stats['total_pdfs']}, Successful: {self.stats['successful']}, Failed: {self.stats['failed']}, Skipped: {self.stats['skipped']}")

        return self.stats

    def generate_report(self) -> Path:
        """
        Generate a summary report of the parsing results.

        Returns:
            Path to the generated report JSON file
        """
        report_path = self.output_dir / "parse_report.json"

        report = {
            'summary': {
                'total_pdfs': self.stats['total_pdfs'],
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'skipped': self.stats['skipped'],
                'success_rate': f"{(self.stats['successful'] / self.stats['total_pdfs'] * 100):.2f}%" if self.stats['total_pdfs'] > 0 else "0%"
            },
            'configuration': {
                'pdf_directory': str(self.pdf_dir),
                'output_directory': str(self.output_dir),
                'model': self.model
            },
            'failed_items': self.stats['failed_items']
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated report: {report_path}")
        return report_path


def main():
    """
    CLI entry point for the ADE parser.
    """
    parser = argparse.ArgumentParser(
        description="Parse regulatory PDFs using Landing AI's ADE API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse eVTOL regulatory docs
  python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs

  # Parse with specific model
  python -m src.parsers.ade_parser --pdf_dir data/quantum/regulatory_docs/pdfs --model dpt-2-latest

  # Use custom output directory name
  python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs --output_dir parsed_output

  # Process 10 PDFs concurrently for faster processing
  python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs --max_concurrent 10
        """
    )

    parser.add_argument(
        '--pdf_dir',
        type=str,
        required=True,
        help='Path to directory containing PDF files to parse'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='dpt-2-latest',
        help='Landing AI ADE model version (default: dpt-2-latest)'
    )

    parser.add_argument(
        '--output_dir',
        type=str,
        default='ade_parsed_results',
        help='Name of output directory (default: ade_parsed_results)'
    )

    parser.add_argument(
        '--api_key',
        type=str,
        default=None,
        help='Landing AI API key (optional, defaults to LANDING_API_KEY from .env)'
    )

    parser.add_argument(
        '--max_concurrent',
        type=int,
        default=5,
        help='Maximum number of concurrent API requests (default: 5, recommended: 5-10)'
    )

    args = parser.parse_args()

    try:
        # Initialize parser
        ade_parser = ADEParser(
            pdf_dir=args.pdf_dir,
            api_key=args.api_key,
            model=args.model,
            output_dir_name=args.output_dir,
            max_concurrent=args.max_concurrent
        )

        # Process all PDFs using async concurrent processing
        stats = asyncio.run(ade_parser.process_directory_async())

        # Generate report
        report_path = ade_parser.generate_report()

        # Print summary
        print("\n" + "="*60)
        print("ADE PARSING COMPLETED")
        print("="*60)
        print(f"Total PDFs: {stats['total_pdfs']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Skipped: {stats['skipped']}")
        if stats['total_pdfs'] > 0:
            success_rate = (stats['successful'] / stats['total_pdfs'] * 100)
            print(f"Success Rate: {success_rate:.2f}%")
        print(f"\nReport saved to: {report_path}")
        print(f"Markdown files: {ade_parser.markdown_dir}")
        print(f"JSON files: {ade_parser.json_dir}")
        print("="*60)

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == '__main__':
    main()
