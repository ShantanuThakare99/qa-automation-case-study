"""
Part 1: Debugging Flaky Test Code Solution
Fixed version of the original flaky tests with proper waits, error handling, and reliability improvements.
"""

import pytest
import time
from playwright.sync_api import sync_playwright, Browser, Page, expect
from typing import Generator
import logging

# Setup logging for better debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestConfig:
    """Configuration class for test constants"""
    BASE_URL = "https://app.workflowpro.com"
    DEFAULT_TIMEOUT = 30000  # 30 seconds
    SLOW_TIMEOUT = 60000     # 60 seconds for slow operations
    
    # Test credentials
    ADMIN_EMAIL = "admin@company1.com"
    USER_EMAIL = "user@company2.com"
    PASSWORD = "password123"

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Session-scoped browser fixture for better resource management"""
    with sync_playwright() as p:
        # Launch browser with proper configuration for CI/CD
        browser = p.chromium.launch(
            headless=True,  # Essential for CI/CD
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        yield browser
        browser.close()

@pytest.fixture
def page(browser: Browser) -> Generator[Page, None, None]:
    """Page fixture with proper configuration"""
    # Create new page with extended timeouts
    page = browser.new_page()
    
    # Set longer timeouts for dynamic loading
    page.set_default_timeout(TestConfig.DEFAULT_TIMEOUT)
    page.set_default_navigation_timeout(TestConfig.SLOW_TIMEOUT)
    
    # Set viewport for consistent rendering
    page.set_viewport_size({"width": 1920, "height": 1080})
    
    yield page
    page.close()

class LoginPage:
    """Page Object Model for Login functionality"""
    
    def __init__(self, page: Page):
        self.page = page
        
        # Locators
        self.email_input = page.locator("#email")
        self.password_input = page.locator("#password") 
        self.login_button = page.locator("#login-btn")
        self.loading_spinner = page.locator(".loading-spinner")
        self.error_message = page.locator(".error-message")
        
    def navigate_to_login(self):
        """Navigate to login page with retry mechanism"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Navigating to login page (attempt {attempt + 1})")
                self.page.goto(f"{TestConfig.BASE_URL}/login", wait_until="networkidle")
                
                # Wait for page to be fully loaded
                self.page.wait_for_load_state("domcontentloaded")
                
                # Verify we're on the correct page
                expect(self.page).to_have_url_pattern(".*\/login.*")
                return
                
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)  # Wait before retry
    
    def login(self, email: str, password: str, expect_success: bool = True):
        """Perform login with proper waits and error handling"""
        try:
            # Ensure form elements are available
            expect(self.email_input).to_be_visible(timeout=10000)
            expect(self.password_input).to_be_visible(timeout=10000)
            expect(self.login_button).to_be_enabled(timeout=10000)
            
            # Clear and fill form fields
            self.email_input.clear()
            self.email_input.fill(email)
            
            self.password_input.clear()
            self.password_input.fill(password)
            
            # Click login and wait for navigation
            with self.page.expect_navigation(wait_until="networkidle", timeout=TestConfig.SLOW_TIMEOUT):
                self.login_button.click()
            
            # Wait for loading spinner to disappear (if present)
            if self.loading_spinner.count() > 0:
                expect(self.loading_spinner).not_to_be_visible(timeout=TestConfig.SLOW_TIMEOUT)
            
            if expect_success:
                # Verify no error messages
                if self.error_message.count() > 0:
                    error_text = self.error_message.text_content()
                    raise AssertionError(f"Login failed with error: {error_text}")
                    
        except Exception as e:
            logger.error(f"Login failed for {email}: {str(e)}")
            raise

class DashboardPage:
    """Page Object Model for Dashboard functionality"""
    
    def __init__(self, page: Page):
        self.page = page
        
        # Locators
        self.welcome_message = page.locator(".welcome-message")
        self.project_cards = page.locator(".project-card")
        self.loading_content = page.locator(".loading-content")
        
    def wait_for_dashboard_load(self):
        """Wait for dashboard to fully load"""
        # Wait for URL to contain dashboard
        expect(self.page).to_have_url_pattern(".*\/dashboard.*")
        
        # Wait for loading content to disappear
        if self.loading_content.count() > 0:
            expect(self.loading_content).not_to_be_visible(timeout=TestConfig.SLOW_TIMEOUT)
        
        # Wait for welcome message to be visible
        expect(self.welcome_message).to_be_visible(timeout=TestConfig.DEFAULT_TIMEOUT)
    
    def get_project_cards(self):
        """Get all project cards with proper waiting"""
        # Wait for at least one project card or empty state
        self.page.wait_for_function(
            "document.querySelectorAll('.project-card').length > 0 || document.querySelector('.empty-state')",
            timeout=TestConfig.DEFAULT_TIMEOUT
        )
        return self.project_cards.all()
    
    def verify_tenant_data(self, expected_tenant: str):
        """Verify all visible data belongs to the expected tenant"""
        project_cards = self.get_project_cards()
        
        if not project_cards:
            logger.warning("No project cards found - might be empty state")
            return
        
        for card in project_cards:
            card_text = card.text_content()
            assert expected_tenant in card_text, f"Found card without {expected_tenant}: {card_text}"

# FIXED TESTS

def test_user_login_fixed(page: Page):
    """
    Fixed version of user login test with proper waits and error handling.
    
    FIXES APPLIED:
    1. Added explicit waits for page elements
    2. Used Page Object Model for better maintainability  
    3. Added retry mechanism for navigation
    4. Proper URL pattern matching instead of exact match
    5. Added loading state handling
    6. Better error handling and logging
    """
    logger.info("Starting user login test")
    
    # Initialize page objects
    login_page = LoginPage(page)
    dashboard_page = DashboardPage(page)
    
    # Navigate with retry mechanism
    login_page.navigate_to_login()
    
    # Perform login
    login_page.login(TestConfig.ADMIN_EMAIL, TestConfig.PASSWORD)
    
    # Wait for dashboard to load completely
    dashboard_page.wait_for_dashboard_load()
    
    logger.info("User login test completed successfully")

def test_multi_tenant_access_fixed(page: Page):
    """
    Fixed version of multi-tenant access test with proper tenant isolation verification.
    
    FIXES APPLIED:
    1. Added proper waiting for dynamic content loading
    2. Better project card handling with empty state consideration
    3. More robust tenant data verification
    4. Added handling for different loading times per tenant
    5. Improved error messaging for debugging
    """
    logger.info("Starting multi-tenant access test")
    
    # Initialize page objects
    login_page = LoginPage(page)
    dashboard_page = DashboardPage(page)
    
    # Navigate and login as Company2 user
    login_page.navigate_to_login()
    login_page.login(TestConfig.USER_EMAIL, TestConfig.PASSWORD)
    
    # Wait for dashboard to load
    dashboard_page.wait_for_dashboard_load()
    
    # Verify tenant isolation - only Company2 data should be visible
    dashboard_page.verify_tenant_data("Company2")
    
    logger.info("Multi-tenant access test completed successfully")

# ADDITIONAL RELIABILITY TESTS

def test_login_with_2fa_handling(page: Page):
    """Test login with 2FA consideration (when enabled for user)"""
    logger.info("Testing login with potential 2FA")
    
    login_page = LoginPage(page)
    login_page.navigate_to_login()
    
    # Login with 2FA-enabled user
    login_page.login(TestConfig.ADMIN_EMAIL, TestConfig.PASSWORD)
    
    # Check if 2FA page appeared
    tfa_code_input = page.locator("#2fa-code")
    if tfa_code_input.count() > 0:
        logger.info("2FA detected - entering code")
        # In real scenario, you'd get this from environment or test service
        tfa_code_input.fill("123456")  # Mock code
        page.click("#verify-2fa-btn")
    
    # Wait for final destination
    dashboard_page = DashboardPage(page)
    dashboard_page.wait_for_dashboard_load()

def test_login_error_handling(page: Page):
    """Test proper error handling for invalid credentials"""
    logger.info("Testing login error handling")
    
    login_page = LoginPage(page)
    login_page.navigate_to_login()
    
    # Attempt login with invalid credentials
    login_page.login("invalid@email.com", "wrongpassword", expect_success=False)
    
    # Verify error message is displayed
    expect(login_page.error_message).to_be_visible()
    error_text = login_page.error_message.text_content()
    assert "invalid" in error_text.lower() or "incorrect" in error_text.lower()

@pytest.mark.slow
def test_slow_loading_dashboard(page: Page):
    """Test dashboard loading under slow network conditions"""
    logger.info("Testing slow loading dashboard")
    
    # Simulate slow network
    page.route("**/*", lambda route: (
        time.sleep(1),  # Add 1 second delay
        route.continue_()
    ))
    
    login_page = LoginPage(page)
    dashboard_page = DashboardPage(page)
    
    login_page.navigate_to_login()
    login_page.login(TestConfig.ADMIN_EMAIL, TestConfig.PASSWORD)
    
    # Should still work with longer timeouts
    dashboard_page.wait_for_dashboard_load()

# CROSS-BROWSER COMPATIBILITY TESTS

@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_cross_browser_login(browser_name: str):
    """Test login functionality across different browsers"""
    with sync_playwright() as p:
        browser_type = getattr(p, browser_name)
        browser = browser_type.launch(headless=True)
        
        try:
            page = browser.new_page()
            page.set_default_timeout(TestConfig.DEFAULT_TIMEOUT)
            
            login_page = LoginPage(page)
            dashboard_page = DashboardPage(page)
            
            login_page.navigate_to_login()
            login_page.login(TestConfig.ADMIN_EMAIL, TestConfig.PASSWORD)
            dashboard_page.wait_for_dashboard_load()
            
            logger.info(f"Login successful on {browser_name}")
            
        finally:
            browser.close()

if __name__ == "__main__":
    # Run tests with proper reporting
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--html=reports/report.html",
        "--self-contained-html"
    ])
