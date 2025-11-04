"""
Enhanced API Client
===================
HTTP client with retry logic, rate limiting, and intelligent error handling
"""

import requests
import logging
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import Config
from .retry_handler import RetryHandler
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class APIClient:
    """
    Enhanced HTTP client with automatic retries, rate limiting, and proxy support
    """

    def __init__(self,
                 rate_limit: float = None,
                 use_sec_agent: bool = False,
                 timeout: int = None):
        """
        Initialize API client

        Args:
            rate_limit: Requests per second (default from Config)
            use_sec_agent: Use SEC-specific User-Agent
            timeout: Request timeout in seconds
        """
        self.rate_limiter = RateLimiter(rate_limit or 2.0)
        self.retry_handler = RetryHandler()
        self.timeout = timeout or Config.REQUEST_TIMEOUT
        self.use_sec_agent = use_sec_agent

        # Create session with connection pooling
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create requests session with connection pooling and retry strategy

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # We handle retries manually
        )

        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    def _get_headers(self, custom_headers: Dict[str, str] = None) -> Dict[str, str]:
        """
        Get request headers with User-Agent

        Args:
            custom_headers: Additional headers to include

        Returns:
            Headers dictionary
        """
        headers = {
            'User-Agent': Config.get_user_agent(self.use_sec_agent),
            'Accept': 'application/json, text/html, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def get(self,
            url: str,
            params: Dict[str, Any] = None,
            headers: Dict[str, str] = None,
            timeout: int = None,
            stream: bool = False) -> requests.Response:
        """
        Perform GET request with retry logic and rate limiting

        Args:
            url: Request URL
            params: Query parameters
            headers: Custom headers
            timeout: Request timeout (overrides default)
            stream: Stream response

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        def _request():
            with self.rate_limiter:
                return self.session.get(
                    url,
                    params=params,
                    headers=self._get_headers(headers),
                    proxies=Config.get_proxy(),
                    timeout=timeout or self.timeout,
                    stream=stream
                )

        try:
            response = self.retry_handler.retry_request(_request)
            return response
        except Exception as e:
            logger.error(f"GET request failed for {url}: {e}")
            raise

    def post(self,
             url: str,
             data: Dict[str, Any] = None,
             json: Dict[str, Any] = None,
             headers: Dict[str, str] = None,
             timeout: int = None) -> requests.Response:
        """
        Perform POST request with retry logic and rate limiting

        Args:
            url: Request URL
            data: Form data
            json: JSON data
            headers: Custom headers
            timeout: Request timeout

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        def _request():
            with self.rate_limiter:
                return self.session.post(
                    url,
                    data=data,
                    json=json,
                    headers=self._get_headers(headers),
                    proxies=Config.get_proxy(),
                    timeout=timeout or self.timeout
                )

        try:
            response = self.retry_handler.retry_request(_request)
            return response
        except Exception as e:
            logger.error(f"POST request failed for {url}: {e}")
            raise

    def download_file(self,
                      url: str,
                      output_path: str,
                      chunk_size: int = 8192) -> bool:
        """
        Download file with progress tracking

        Args:
            url: File URL
            output_path: Output file path
            chunk_size: Download chunk size

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.get(url, stream=True)
            response.raise_for_status()

            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))

            from pathlib import Path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

            logger.info(f"Downloaded: {output_path} ({total_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return False

    def get_json(self,
                 url: str,
                 params: Dict[str, Any] = None,
                 headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        Perform GET request and parse JSON response

        Args:
            url: Request URL
            params: Query parameters
            headers: Custom headers

        Returns:
            Parsed JSON dict or None on error
        """
        try:
            response = self.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except ValueError as e:
            logger.error(f"JSON parsing failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def close(self):
        """Close session and cleanup resources"""
        self.session.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class SECAPIClient(APIClient):
    """Specialized client for SEC EDGAR API"""

    def __init__(self):
        super().__init__(
            rate_limit=Config.RATE_LIMITS['sec'],
            use_sec_agent=True
        )


class FMPAPIClient(APIClient):
    """Specialized client for Financial Modeling Prep API"""

    BASE_URL = 'https://financialmodelingprep.com/api'

    def __init__(self):
        super().__init__(rate_limit=Config.RATE_LIMITS['earnings'])
        self.api_key = Config.FMP_API_KEY

        if not self.api_key:
            logger.warning("FMP_API_KEY not set. FMP API requests will fail.")

    def _build_url(self, endpoint: str, version: str = 'v3') -> str:
        """Build FMP API URL"""
        return f'{self.BASE_URL}/{version}/{endpoint}'

    def fetch_endpoint(self, endpoint: str, ticker: str = None, params: Dict[str, Any] = None) -> Optional[Any]:
        """
        Generic FMP API GET request

        Args:
            endpoint: API endpoint (e.g., 'profile', 'income-statement')
            ticker: Optional ticker symbol to append to endpoint
            params: Optional query parameters

        Returns:
            API response data or None
        """
        if not self.api_key:
            logger.error("FMP_API_KEY not configured")
            return None

        # Build URL
        if ticker:
            url = self._build_url(f'{endpoint}/{ticker}')
        else:
            url = self._build_url(endpoint)

        # Add API key to params
        if params is None:
            params = {}
        params['apikey'] = self.api_key

        return self.get_json(url, params=params)

    def get_company_profile(self, symbol: str) -> Optional[Any]:
        """Get company profile (free tier)"""
        return self.fetch_endpoint('profile', ticker=symbol)

    def get_earnings_transcript(self,
                                symbol: str,
                                quarter: int = None,
                                year: int = None) -> Optional[Dict[str, Any]]:
        """
        Get earnings call transcript from FMP API

        Args:
            symbol: Stock ticker symbol
            quarter: Quarter number (1-4)
            year: Year

        Returns:
            Transcript data or None
        """
        if not self.api_key:
            logger.error("FMP_API_KEY not configured")
            return None

        url = self._build_url(f'earning_call_transcript/{symbol}')
        params = {'apikey': self.api_key}

        if quarter and year:
            params['quarter'] = quarter
            params['year'] = year

        return self.get_json(url, params=params)


class COREAPIClient(APIClient):
    """Specialized client for CORE API"""

    def __init__(self):
        super().__init__(rate_limit=Config.RATE_LIMITS['research'])
        self.api_key = Config.CORE_API_KEY

        if not self.api_key:
            logger.warning("CORE_API_KEY not set. CORE API requests will fail.")

    def search_works(self,
                     query: str,
                     limit: int = 100,
                     offset: int = 0) -> Optional[Dict[str, Any]]:
        """
        Search for research works using CORE API

        Args:
            query: Search query
            limit: Number of results
            offset: Result offset

        Returns:
            Search results or None
        """
        if not self.api_key:
            logger.error("CORE_API_KEY not configured")
            return None

        url = Config.CORE_API_ENDPOINT
        headers = {'Authorization': f'Bearer {self.api_key}'}
        params = {
            'q': query,
            'limit': limit,
            'offset': offset
        }

        return self.get_json(url, params=params, headers=headers)
