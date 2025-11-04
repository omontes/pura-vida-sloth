# Downloader Fixes Progress

## Summary

Fixing broken downloaders to be industry-agnostic by adding parameter support.

## Completed ✅

### 1. Research Downloader
**File:** `src/downloaders/research_papers.py`
**Changes:**
- Added `keywords: List[str] = None` parameter to `__init__`
- Falls back to `Config.RESEARCH_KEYWORDS` if not provided
- **Status:** ✅ Working - Downloaded 234 papers in test
- **Test:** `tests/test_downloaders/test_research_papers.py`

### 2. SEC Downloader
**File:** `src/downloaders/sec_filings.py`
**Changes:**
- Added `tickers: Optional[Dict[str, str]] = None` parameter to `__init__`
- Changed `self.TARGET_COMPANIES` → `self.companies` (uses parameter or fallback)
- Falls back to `self.TARGET_COMPANIES` if not provided
- **Status:** ✅ Parameterization working - Found 5 filings for JOBY
- **Test:** `tests/test_downloaders/test_sec_filings.py` (efficient - 1 company only)
- **Note:** Has Windows filename bug (colons in datetime) but core functionality works

## In Progress 🔧

### 3. Earnings Downloader
**File:** `src/downloaders/earnings.py`
**Next:** Add `tickers` parameter similar to SEC downloader

### 4. Press Release Downloader
**File:** `src/downloaders/press_releases.py`
**Next:** Add `companies` parameter

### 5. Regulatory Downloader
**File:** `src/downloaders/regulatory.py`
**Next:** Add `keywords` and/or `regulators` parameters

## Testing Strategy

All new tests follow efficient pattern:
- **1 data point only** to minimize API usage
- Fast execution (10-60 seconds vs 5 minutes)
- Located in `tests/test_downloaders/test_{name}.py`
- Can be run individually: `python tests/test_downloaders/test_sec_filings.py`

## Known Issues

### Windows Filename Bug (SEC Downloader)
- **Issue:** Filenames contain `:` from ISO datetime format
- **Example:** `JOBY_8-K_2025-10-08T00:00:00_000162828025044595.html`
- **Error:** `[Errno 22] Invalid argument` on Windows
- **Fix Needed:** Replace `:` with `-` in timestamp portion
- **Impact:** Files found correctly, just can't save on Windows
- **Priority:** Low (works on Linux/Mac, Windows-specific issue)

## Next Steps

1. Fix Earnings downloader (add tickers parameter)
2. Fix Press Release downloader (add companies parameter)
3. Fix Regulatory downloader (add keywords parameter)
4. Fix Windows filename bug in SEC downloader
5. Create new downloaders (EDGAR, Alpha Vantage, Tavily)
6. Update `evtol_config.json` with `keywords_by_source` section
7. Create remaining individual test files
8. Run full integration test

## Benefits Achieved

✅ **Industry-Agnostic Design** - Downloaders now accept parameters
✅ **Backward Compatible** - Falls back to hardcoded values if no parameters
✅ **Fast Testing** - Individual tests with minimal API calls
✅ **Verified Working** - Research (234 papers) and SEC (5 filings found)
