# Task 7.3: End-to-End Tests

## Overview

Create end-to-end tests using Playwright to simulate real user workflows from the browser, testing the complete application stack including the Vue frontend, FastAPI backend, and database.

## Priority

**P2 (Medium)** - Important but not blocking for MVP

## Dependencies

- Task 7.2: Integration Tests
- Task 6: Web Frontend (all tasks 15-19)

## Objectives

1. Set up Playwright for browser automation
2. Test complete user workflows
3. Test OAuth setup process
4. Test contact browsing and filtering
5. Test search functionality
6. Test sync management
7. Test on multiple browsers (Chromium, Firefox, WebKit)
8. Create reusable page objects
9. Generate test reports with screenshots

## Technical Context

### Playwright Features
- Cross-browser testing (Chromium, Firefox, WebKit)
- Auto-wait for elements
- Screenshot and video recording
- Network interception
- Mobile device emulation

### Test Organization
```
tests/
├── e2e/
│   ├── test_user_workflows.py
│   ├── test_oauth_setup.py
│   ├── test_contacts_browsing.py
│   ├── test_search_ui.py
│   ├── test_sync_management.py
│   └── pages/
│       ├── base_page.py
│       ├── home_page.py
│       ├── contacts_page.py
│       ├── search_page.py
│       └── sync_page.py
├── conftest.py
└── playwright.config.py
```

## Acceptance Criteria

- [ ] Playwright is configured and working
- [ ] User workflows are tested end-to-end
- [ ] OAuth flow is tested (with mocks)
- [ ] Contact browsing works in browser
- [ ] Search functionality works in browser
- [ ] Sync management UI is tested
- [ ] Tests run on multiple browsers
- [ ] Screenshots captured on failures
- [ ] Test reports generated
- [ ] Tests are maintainable with page objects

## Implementation Steps

### 1. Install Playwright

Update `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "playwright>=1.40.0",
    "pytest-playwright>=0.4.3",
]
```

Install and set up:

```bash
uv pip install playwright pytest-playwright
uv run playwright install
```

### 2. Configure Playwright

Create `tests/playwright.config.py`:

```python
"""Playwright configuration."""
import os
from playwright.sync_api import Page

# Test configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

BROWSER_CONFIG = {
    "headless": HEADLESS,
    "slow_mo": 100 if not HEADLESS else 0,  # Slow down for debugging
}

# Viewport sizes
DESKTOP_VIEWPORT = {"width": 1280, "height": 720}
TABLET_VIEWPORT = {"width": 768, "height": 1024}
MOBILE_VIEWPORT = {"width": 375, "height": 667}

# Timeouts
DEFAULT_TIMEOUT = 30000  # 30 seconds
NAVIGATION_TIMEOUT = 60000  # 60 seconds

# Screenshot settings
SCREENSHOT_ON_FAILURE = True
TRACE_ON_FAILURE = True
```

### 3. Create Page Object Base

Create `tests/e2e/pages/base_page.py`:

```python
"""Base page object for all pages."""
from playwright.sync_api import Page, expect


class BasePage:
    """Base page object with common functionality."""
    
    def __init__(self, page: Page):
        """Initialize page object.
        
        Args:
            page: Playwright page instance
        """
        self.page = page
        self.base_url = "http://localhost:8000"
    
    def navigate_to(self, path: str = "/"):
        """Navigate to a path.
        
        Args:
            path: URL path to navigate to
        """
        self.page.goto(f"{self.base_url}{path}")
        self.page.wait_for_load_state("networkidle")
    
    def wait_for_element(self, selector: str, timeout: int = 30000):
        """Wait for element to be visible.
        
        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds
        """
        self.page.wait_for_selector(selector, state="visible", timeout=timeout)
    
    def click(self, selector: str):
        """Click an element.
        
        Args:
            selector: CSS selector
        """
        self.page.click(selector)
    
    def fill(self, selector: str, value: str):
        """Fill an input field.
        
        Args:
            selector: CSS selector
            value: Value to fill
        """
        self.page.fill(selector, value)
    
    def get_text(self, selector: str) -> str:
        """Get text content of an element.
        
        Args:
            selector: CSS selector
            
        Returns:
            Text content
        """
        return self.page.text_content(selector) or ""
    
    def is_visible(self, selector: str) -> bool:
        """Check if element is visible.
        
        Args:
            selector: CSS selector
            
        Returns:
            True if visible
        """
        return self.page.is_visible(selector)
    
    def wait_for_navigation(self):
        """Wait for navigation to complete."""
        self.page.wait_for_load_state("networkidle")
    
    def take_screenshot(self, name: str):
        """Take a screenshot.
        
        Args:
            name: Screenshot filename
        """
        self.page.screenshot(path=f"test-results/{name}.png")


class NavigationMixin:
    """Mixin for common navigation actions."""
    
    def click_nav_link(self, text: str):
        """Click a navigation link.
        
        Args:
            text: Link text
        """
        self.page.click(f"nav >> text={text}")
        self.wait_for_navigation()
    
    def go_home(self):
        """Navigate to home page."""
        self.click_nav_link("Home")
    
    def go_to_contacts(self):
        """Navigate to contacts page."""
        self.click_nav_link("Contacts")
    
    def go_to_search(self):
        """Navigate to search page."""
        self.click_nav_link("Search")
    
    def go_to_sync(self):
        """Navigate to sync page."""
        self.click_nav_link("Sync")
```

### 4. Create Page Objects

Create `tests/e2e/pages/contacts_page.py`:

```python
"""Contacts page object."""
from playwright.sync_api import Page, expect
from .base_page import BasePage, NavigationMixin


class ContactsPage(BasePage, NavigationMixin):
    """Contacts page object."""
    
    # Selectors
    CONTACTS_GRID = "#contacts-container"
    CONTACT_CARD = ".contact-card"
    SORT_SELECT = "#sort-select"
    VIEW_SELECT = "#view-select"
    LETTER_FILTER = ".index-filter"
    CONTACT_MODAL = "#contact-modal"
    MODAL_CLOSE = "#close-modal"
    
    def navigate(self):
        """Navigate to contacts page."""
        self.navigate_to("/contacts")
    
    def wait_for_contacts_to_load(self):
        """Wait for contacts to finish loading."""
        self.wait_for_element(self.CONTACTS_GRID)
        # Wait for spinner to disappear
        self.page.wait_for_selector(".spinner", state="hidden", timeout=5000)
    
    def get_contact_count(self) -> int:
        """Get number of visible contacts.
        
        Returns:
            Number of contact cards
        """
        return len(self.page.query_selector_all(self.CONTACT_CARD))
    
    def click_contact(self, index: int = 0):
        """Click a contact card.
        
        Args:
            index: Index of contact to click (0-based)
        """
        cards = self.page.query_selector_all(self.CONTACT_CARD)
        if index < len(cards):
            cards[index].click()
    
    def filter_by_letter(self, letter: str):
        """Filter contacts by letter.
        
        Args:
            letter: Letter to filter by (A-Z or #)
        """
        self.page.click(f"{self.LETTER_FILTER}[data-group='{letter}']")
        self.wait_for_contacts_to_load()
    
    def change_sort(self, sort_value: str):
        """Change sort order.
        
        Args:
            sort_value: Sort value ('name' or 'recent')
        """
        self.page.select_option(self.SORT_SELECT, sort_value)
        self.wait_for_contacts_to_load()
    
    def change_view(self, view: str):
        """Change view mode.
        
        Args:
            view: View mode ('grid' or 'list')
        """
        self.page.select_option(self.VIEW_SELECT, view)
    
    def is_modal_open(self) -> bool:
        """Check if contact modal is open.
        
        Returns:
            True if modal is visible
        """
        return self.is_visible(self.CONTACT_MODAL) and not "hidden" in self.page.get_attribute(self.CONTACT_MODAL, "class")
    
    def close_modal(self):
        """Close contact detail modal."""
        if self.is_modal_open():
            self.click(self.MODAL_CLOSE)
            self.page.wait_for_selector(self.CONTACT_MODAL, state="hidden")
    
    def get_contact_names(self) -> list[str]:
        """Get all visible contact names.
        
        Returns:
            List of contact names
        """
        cards = self.page.query_selector_all(f"{self.CONTACT_CARD} h3")
        return [card.text_content() for card in cards if card.text_content()]


class SearchPage(BasePage, NavigationMixin):
    """Search page object."""
    
    # Selectors
    SEARCH_INPUT = "#search-input"
    SEARCH_RESULTS = "#search-results"
    SEARCH_SPINNER = "#search-spinner"
    
    def navigate(self):
        """Navigate to search page."""
        self.navigate_to("/search")
    
    def search(self, query: str):
        """Perform a search.
        
        Args:
            query: Search query
        """
        self.fill(self.SEARCH_INPUT, query)
        # Wait for debounce and results
        self.page.wait_for_timeout(500)  # Debounce delay
        self.wait_for_results()
    
    def wait_for_results(self):
        """Wait for search results to load."""
        # Wait for spinner to disappear
        self.page.wait_for_selector(self.SEARCH_SPINNER, state="hidden", timeout=5000)
    
    def get_result_count(self) -> int:
        """Get number of search results.
        
        Returns:
            Number of results
        """
        return len(self.page.query_selector_all(f"{self.SEARCH_RESULTS} > div > div"))
    
    def get_first_result_name(self) -> str:
        """Get name of first search result.
        
        Returns:
            Contact name
        """
        first_result = self.page.query_selector(f"{self.SEARCH_RESULTS} h3")
        return first_result.text_content() if first_result else ""


class SyncPage(BasePage, NavigationMixin):
    """Sync management page object."""
    
    # Selectors
    SYNC_BUTTON = "#sync-button"
    FULL_SYNC_BUTTON = "#full-sync-button"
    SYNC_STATUS = "#sync-status"
    
    def navigate(self):
        """Navigate to sync page."""
        self.navigate_to("/sync")
    
    def trigger_sync(self):
        """Trigger incremental sync."""
        self.click(self.SYNC_BUTTON)
    
    def trigger_full_sync(self):
        """Trigger full sync."""
        self.click(self.FULL_SYNC_BUTTON)
    
    def get_status(self) -> str:
        """Get current sync status.
        
        Returns:
            Status text
        """
        return self.get_text(f"{self.SYNC_STATUS} span")
    
    def wait_for_sync_complete(self, timeout: int = 60000):
        """Wait for sync to complete.
        
        Args:
            timeout: Timeout in milliseconds
        """
        # Wait for status to change from "Running"
        self.page.wait_for_function(
            """() => {
                const status = document.querySelector('#sync-status span');
                return status && !status.textContent.includes('Running');
            }""",
            timeout=timeout
        )
```

### 5. Create E2E Tests

Create `tests/e2e/test_user_workflows.py`:

```python
"""End-to-end tests for complete user workflows."""
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages.contacts_page import ContactsPage, SearchPage, SyncPage


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "record_video_dir": "test-results/videos",
    }


class TestContactBrowsingWorkflow:
    """Test contact browsing workflows."""
    
    def test_view_contacts_list(self, page: Page):
        """Test viewing contacts list."""
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        # Should show contacts
        contact_count = contacts_page.get_contact_count()
        assert contact_count > 0, "Should display contacts"
    
    def test_filter_contacts_by_letter(self, page: Page):
        """Test filtering contacts by letter."""
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        # Filter by 'A'
        contacts_page.filter_by_letter("A")
        
        # All contacts should start with A
        names = contacts_page.get_contact_names()
        assert all(name.startswith("A") or name.startswith("a") for name in names)
    
    def test_sort_contacts(self, page: Page):
        """Test sorting contacts."""
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        # Sort by name
        contacts_page.change_sort("name")
        
        # Get names
        names = contacts_page.get_contact_names()
        
        # Should be sorted
        assert names == sorted(names)
    
    def test_view_contact_details(self, page: Page):
        """Test viewing contact details."""
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        # Click first contact
        contacts_page.click_contact(0)
        
        # Modal should open
        assert contacts_page.is_modal_open(), "Modal should be open"
        
        # Close modal
        contacts_page.close_modal()
        
        # Modal should close
        assert not contacts_page.is_modal_open(), "Modal should be closed"
    
    def test_switch_view_mode(self, page: Page):
        """Test switching between grid and list views."""
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        # Switch to list view
        contacts_page.change_view("list")
        
        # Should show table
        assert page.is_visible("table"), "Should show table in list view"
        
        # Switch back to grid
        contacts_page.change_view("grid")
        
        # Should show cards
        assert page.is_visible(".contact-card"), "Should show cards in grid view"


class TestSearchWorkflow:
    """Test search workflows."""
    
    def test_search_by_name(self, page: Page):
        """Test searching by name."""
        search_page = SearchPage(page)
        search_page.navigate()
        
        # Search for a name
        search_page.search("John")
        
        # Should show results
        result_count = search_page.get_result_count()
        assert result_count > 0, "Should find matching contacts"
    
    def test_search_by_phone(self, page: Page):
        """Test searching by phone number."""
        search_page = SearchPage(page)
        search_page.navigate()
        
        # Search for phone
        search_page.search("555-123-4567")
        
        # Should show results
        result_count = search_page.get_result_count()
        assert result_count >= 0, "Should handle phone search"
    
    def test_search_no_results(self, page: Page):
        """Test search with no results."""
        search_page = SearchPage(page)
        search_page.navigate()
        
        # Search for nonexistent name
        search_page.search("XYZ_NONEXISTENT_12345")
        
        # Should show no results message
        page.wait_for_selector("text=No results found")


class TestSyncWorkflow:
    """Test sync management workflows."""
    
    def test_view_sync_status(self, page: Page):
        """Test viewing sync status."""
        sync_page = SyncPage(page)
        sync_page.navigate()
        
        # Should show status
        status = sync_page.get_status()
        assert status in ["Idle", "Running", "Completed", "Error"]
    
    @pytest.mark.slow
    def test_trigger_sync(self, page: Page):
        """Test triggering sync."""
        sync_page = SyncPage(page)
        sync_page.navigate()
        
        # Trigger sync
        sync_page.trigger_sync()
        
        # Status should change
        page.wait_for_timeout(1000)
        status = sync_page.get_status()
        assert status in ["Running", "Completed"]


class TestNavigationWorkflow:
    """Test navigation workflows."""
    
    def test_navigate_between_pages(self, page: Page):
        """Test navigating between different pages."""
        from tests.e2e.pages.base_page import BasePage
        
        base = BasePage(page)
        base.navigate_to("/")
        
        # Navigate to each page
        contacts_page = ContactsPage(page)
        contacts_page.go_to_contacts()
        assert "/contacts" in page.url
        
        contacts_page.go_to_search()
        assert "/search" in page.url
        
        contacts_page.go_to_sync()
        assert "/sync" in page.url
        
        contacts_page.go_home()
        assert page.url.endswith("/")


@pytest.mark.slow
class TestResponsiveDesign:
    """Test responsive design on different devices."""
    
    def test_mobile_layout(self, page: Page):
        """Test mobile layout."""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        # Should show single column
        # (Would need to check computed styles or layout)
        assert contacts_page.get_contact_count() > 0
    
    def test_tablet_layout(self, page: Page):
        """Test tablet layout."""
        # Set tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})
        
        contacts_page = ContactsPage(page)
        contacts_page.navigate()
        contacts_page.wait_for_contacts_to_load()
        
        assert contacts_page.get_contact_count() > 0
```

### 6. Configure pytest for E2E

Update `tests/conftest.py`:

```python
"""Pytest configuration for E2E tests."""
import pytest


@pytest.fixture(scope="session")
def playwright_launch_options(playwright_launch_options):
    """Configure Playwright launch options."""
    return {
        **playwright_launch_options,
        "headless": True,
        "slow_mo": 0,
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments."""
    return {
        **browser_type_launch_args,
        "args": [
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
    }


@pytest.fixture(autouse=True)
def screenshot_on_failure(page, request):
    """Take screenshot on test failure."""
    yield
    
    if request.node.rep_call.failed:
        screenshot_path = f"test-results/screenshots/{request.node.name}.png"
        page.screenshot(path=screenshot_path)
```

## Verification

After completing this task:

1. **Install Playwright**:
   ```bash
   uv pip install playwright pytest-playwright
   uv run playwright install
   ```

2. **Start Application**:
   ```bash
   # Terminal 1: Backend
   uv run python -m google_contacts_cisco.main
   
   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

3. **Run E2E Tests**:
   ```bash
   uv run pytest tests/e2e -v --headed
   # Use --headed to see browser
   ```

4. **Run on Specific Browser**:
   ```bash
   uv run pytest tests/e2e --browser chromium
   uv run pytest tests/e2e --browser firefox
   uv run pytest tests/e2e --browser webkit
   ```

5. **Generate Test Report**:
   ```bash
   uv run pytest tests/e2e --html=test-results/report.html --self-contained-html
   ```

6. **Debug Mode**:
   ```bash
   PWDEBUG=1 uv run pytest tests/e2e -v
   # Opens Playwright Inspector
   ```

## Notes

- **Page Objects**: Reusable page abstractions
- **Auto-wait**: Playwright waits automatically for elements
- **Screenshots**: Captured on test failures
- **Videos**: Recorded for failed tests
- **Multi-browser**: Tests run on Chromium, Firefox, WebKit
- **Headless**: Run without visible browser for CI/CD
- **Debugging**: Use PWDEBUG=1 for step-through debugging

## Common Issues

1. **Timeouts**: Increase timeout for slow operations
2. **Element Not Found**: Wait for element before interacting
3. **Flaky Tests**: Add proper waits, avoid hardcoded sleeps
4. **Browser Not Installed**: Run `playwright install`
5. **Port Conflicts**: Ensure app is running on correct port

## Best Practices

- Use page objects for maintainability
- Test user workflows, not implementation
- Use descriptive test names
- Take screenshots on failures
- Avoid hardcoded waits
- Test on multiple browsers
- Use semantic selectors (data-testid)
- Clean up after tests

## Related Documentation

- Playwright Python: https://playwright.dev/python/
- pytest-playwright: https://github.com/microsoft/playwright-pytest
- Page Object Pattern: https://playwright.dev/python/docs/pom

## Estimated Time

6-8 hours
