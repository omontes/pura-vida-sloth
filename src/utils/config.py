"""
Configuration Management
========================
Centralized configuration for all downloaders with API key management
"""

from pathlib import Path
from typing import Dict, Any
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Global configuration"""

    # ============================================================================
    # API KEYS
    # ============================================================================

    # Existing APIs
    FMP_API_KEY = os.getenv('FMP_API_KEY', '')
    CORE_API_KEY = os.getenv('CORE_API_KEY', '')
    NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')

    # New APIs for Hype Cycle System
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # Strongly recommended for GitHub tracking
    PATENTSVIEW_API_KEY = os.getenv('PATENTSVIEW_API_KEY', '')  # Required for patent_downloader.py

    # ============================================================================
    # DEFAULT SETTINGS
    # ============================================================================

    DEFAULT_OUTPUT_DIR = "./data"
    DEFAULT_DAYS_BACK = 30

    # ============================================================================
    # RATE LIMITS (requests per second)
    # ============================================================================

    RATE_LIMITS = {
        'sec': float(os.getenv('SEC_RATE_LIMIT', '10')),
        'earnings': float(os.getenv('EARNINGS_RATE_LIMIT', '2')),
        'research': float(os.getenv('RESEARCH_RATE_LIMIT', '2')),
        'regulatory': float(os.getenv('REGULATORY_RATE_LIMIT', '2')),
        'press': float(os.getenv('PRESS_RATE_LIMIT', '2'))
    }

    # ============================================================================
    # PARALLEL DOWNLOAD SETTINGS
    # ============================================================================

    MAX_WORKERS = {
        'sec': 5,
        'earnings': 3,
        'research': 3,
        'regulatory': 3,
        'press': 3
    }

    # ============================================================================
    # TIMEOUT SETTINGS (seconds)
    # ============================================================================

    REQUEST_TIMEOUT = 30
    DOWNLOAD_TIMEOUT = 60

    # ============================================================================
    # RETRY SETTINGS
    # ============================================================================

    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '5'))
    RETRY_BACKOFF = 2  # Exponential backoff multiplier
    INITIAL_RETRY_DELAY = float(os.getenv('INITIAL_RETRY_DELAY', '1'))

    # ============================================================================
    # CHECKPOINT SETTINGS
    # ============================================================================

    ENABLE_CHECKPOINTS = os.getenv('ENABLE_CHECKPOINTS', 'true').lower() == 'true'
    CHECKPOINT_INTERVAL = int(os.getenv('CHECKPOINT_INTERVAL', '50'))

    # ============================================================================
    # PROXY CONFIGURATION
    # ============================================================================

    USE_PROXIES = os.getenv('USE_PROXIES', 'false').lower() == 'true'
    PROXY_LIST = os.getenv('PROXY_LIST', '').split(',') if os.getenv('PROXY_LIST') else []

    # ============================================================================
    # TARGET COMPANIES
    # ============================================================================

    TARGET_COMPANIES = {
        # Large Banks
        'JPM': 'JPMorgan Chase & Co.',
        'BAC': 'Bank of America Corp',
        'WFC': 'Wells Fargo & Company',
        'C': 'Citigroup Inc.',
        'GS': 'Goldman Sachs Group Inc.',
        'MS': 'Morgan Stanley',
        'USB': 'U.S. Bancorp',
        'PNC': 'PNC Financial Services',
        'TFC': 'Truist Financial Corp',
        'BK': 'Bank of New York Mellon',
        # Payment Processors
        'V': 'Visa Inc.',
        'MA': 'Mastercard Inc.',
        'AXP': 'American Express Company',
        'PYPL': 'PayPal Holdings Inc.',
        'SQ': 'Block Inc.',
        'FIS': 'Fidelity National Information Services',
        'FISV': 'Fiserv Inc.',
        # FinTech & Digital
        'COIN': 'Coinbase Global Inc.',
        'SOFI': 'SoFi Technologies Inc.',
        'AFRM': 'Affirm Holdings Inc.',
        'UPST': 'Upstart Holdings Inc.',
        'LC': 'LendingClub Corp',
        # Investment & Wealth Management
        'SCHW': 'Charles Schwab Corp',
        'IBKR': 'Interactive Brokers Group',
        'HOOD': 'Robinhood Markets Inc.',
        # Insurance/Finance Tech
        'AIG': 'American International Group',
        'MET': 'MetLife Inc.',
        'PRU': 'Prudential Financial',
        # Credit Services
        'COF': 'Capital One Financial',
        'DFS': 'Discover Financial Services',
        'SYF': 'Synchrony Financial',
        # Crypto/Blockchain
        'MSTR': 'MicroStrategy Inc.',
        'RIOT': 'Riot Platforms Inc.',
        'MARA': 'Marathon Digital Holdings'
    }

    # ============================================================================
    # COMPANY RSS FEEDS
    # ============================================================================

    COMPANY_RSS_FEEDS = {
        'JPM': 'https://www.jpmorganchase.com/news-stories/rss',
        'BAC': 'https://newsroom.bankofamerica.com/rss',
        'V': 'https://usa.visa.com/about-visa/newsroom.rss',
        'MA': 'https://www.mastercard.com/news/feed/',
        'PYPL': 'https://newsroom.paypal-corp.com/rss',
        'COIN': 'https://blog.coinbase.com/feed'
    }

    # ============================================================================
    # COMPANY INVESTOR RELATIONS URLs
    # ============================================================================

    COMPANY_IR_URLS = {
        'JPM': 'https://www.jpmorganchase.com/ir/presentations-webcasts',
        'BAC': 'https://investor.bankofamerica.com/events-and-presentations',
        'GS': 'https://www.goldmansachs.com/investor-relations/financials/quarterly-earnings.html',
        'MS': 'https://www.morganstanley.com/about-us-ir/shareholder/quarterly-earnings',
        'V': 'https://investor.visa.com/events-and-presentations/',
        'MA': 'https://investor.mastercard.com/events-and-presentations/',
        'PYPL': 'https://investor.pypl.com/events-and-presentations/'
    }

    # ============================================================================
    # REGULATORY SOURCES
    # ============================================================================

    REGULATORY_RSS_FEEDS = {
        'FED_PRESS': 'https://www.federalreserve.gov/feeds/press_all.xml',
        'FED_SR_LETTERS': 'https://www.federalreserve.gov/feeds/h3.xml',
        'FED_REGULATIONS': 'https://www.federalreserve.gov/feeds/regs.xml',
        'FDIC_PRESS': 'https://www.fdic.gov/news/press-releases/feed.xml',
        'FDIC_FIL': 'https://www.fdic.gov/regulations/financial-institution-letters/feed.xml',
        'OCC_NEWS': 'https://www.occ.gov/rss/news-releases.xml',
        'OCC_BULLETINS': 'https://www.occ.gov/rss/bulletins.xml',
        'CFPB_NEWS': 'https://www.consumerfinance.gov/about-us/newsroom/feed/'
    }

    FEDERAL_REGISTER_API = 'https://www.federalregister.gov/api/v1/documents.json'

    FEDERAL_AGENCIES = [
        'consumer-financial-protection-bureau',
        'comptroller-of-the-currency',
        'federal-deposit-insurance-corporation',
        'federal-reserve-system',
        'financial-crimes-enforcement-network',
        'securities-and-exchange-commission',
        'commodity-futures-trading-commission'
    ]

    # ============================================================================
    # RESEARCH PAPER SOURCES
    # ============================================================================

    RESEARCH_KEYWORDS = [
        'fintech', 'digital banking', 'blockchain finance', 'cryptocurrency',
        'decentralized finance', 'DeFi', 'payment systems', 'neobank',
        'robo-advisor', 'algorithmic trading', 'high-frequency trading',
        'financial AI', 'regtech', 'insurtech', 'open banking',
        'embedded finance', 'BNPL', 'digital wallet', 'stablecoin',
        'central bank digital currency', 'CBDC', 'smart contracts',
        'peer-to-peer lending', 'crowdfunding', 'financial inclusion'
    ]

    RESEARCH_RSS_FEEDS = {
        'FED_NOTES': 'https://www.federalreserve.gov/feeds/feds_notes.xml',
        'FED_PAPERS': 'https://www.federalreserve.gov/feeds/feds.xml',
        'BIS_WORKING': 'https://www.bis.org/doclist/wpapers.rss',
        'BIS_ALL': 'https://www.bis.org/doclist/all.rss',
        'NBER_NEW': 'https://www.nber.org/rss/new.xml'
    }

    CORE_API_ENDPOINT = 'https://api.core.ac.uk/v3/search/works'
    FRASER_OAI_ENDPOINT = 'https://fraser.stlouisfed.org/oai/request'
    ARXIV_API_ENDPOINT = 'http://export.arxiv.org/api/query'

    # ============================================================================
    # USER AGENTS
    # ============================================================================

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]

    SEC_USER_AGENT = 'FinTechHypeCycle research@fintech.ai'

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    @classmethod
    def validate(cls):
        """Validate that required API keys are set"""
        warnings = []

        if not cls.FMP_API_KEY:
            warnings.append("FMP_API_KEY not set (earnings downloader will use web scraping fallback)")

        if not cls.CORE_API_KEY:
            warnings.append("CORE_API_KEY not set (research downloader will have limited coverage)")

        if warnings:
            print("\n⚠️  Configuration Warnings:")
            for warning in warnings:
                print(f"   - {warning}")
            print("\nFor best results, set API keys in .env file.")
            print("See .env.template for instructions.\n")
            return False
        else:
            print("✓ All required API keys are configured\n")
            return True

    @classmethod
    def get_proxy(cls):
        """Get a random proxy from the list (if proxies enabled)"""
        if not cls.USE_PROXIES or not cls.PROXY_LIST:
            return None

        import random
        proxy = random.choice(cls.PROXY_LIST)
        return {'http': proxy, 'https': proxy}

    @classmethod
    def get_user_agent(cls, use_sec_agent=False):
        """Get a random user agent (or SEC-specific agent)"""
        if use_sec_agent:
            return cls.SEC_USER_AGENT

        import random
        return random.choice(cls.USER_AGENTS)

    @classmethod
    def load_from_file(cls, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from JSON file
        
        Args:
            config_path: Path to config file
        
        Returns:
            Configuration dictionary
        """
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    @classmethod
    def save_to_file(cls, config: Dict[str, Any], config_path: Path):
        """
        Save configuration to JSON file
        
        Args:
            config: Configuration dictionary
            config_path: Path to save config
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
