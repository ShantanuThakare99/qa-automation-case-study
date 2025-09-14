"""
Global pytest configuration and fixtures for QA Automation Framework
"""

import pytest
import json
import os
import logging
from typing import Dict, Generator
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

def pytest_configure(config):
    """Configure pytest settings"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    os.makedirs('screenshots', exist_ok=True)
    
    # Add custom markers
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "regression: mark test as regression test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "api: mark test as API test")
    config.addinivalue_line("markers", "ui: mark test as UI test")
    config.addinivalue_line("markers", "mobile: mark test as mobile test")
    config.addinivalue_line("markers", "cross_platform: mark test as cross-platform test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "security: mark test as security test")

def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--env",
        action="store",
        default="staging",
        help="Environment to run tests against (dev, staging, prod)"
    )
    parser.addoption(
        "--browser",
        action="store", 
        default="chromium",
        help="Browser to use for testing (chromium, firefox, webkit)"
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser in headed mode"
    )
    parser.addoption(
        "--slow-mo",
        action="store",
        type=int,
        default=0,
        help="Slow down operations by specified milliseconds"
    )

@pytest.fixture(scope="session")
def test_config(request) -> Dict:
    """Load test configuration based on environment"""
    env = request.config.getoption("--env")
    config_file = f"config/{env}.json"
    
    if not os.path.exists(config_file):
        # Fallback to default config
        config_file = "config/staging.json"
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Add command line options to config
    config['browser'] = request.config.getoption("--browser")
    config['headed'] = request.config.getoption("--headed")
    config['slow_mo'] = request.config.getoption("--slow-mo")
    
    return config

@pytest.fixture(scope="session") 
def playwright_instance():
    """Session-scoped Playwright instance"""
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(playwright_instance, test_config) -> Generator[Browser, None, None]:
    """Session-scoped browser instance"""
    browser_name = test_config['browser']
    headed = test_config['headed']
    slow_mo = test_config['slow_mo']
    
    # Get browser launcher
    if browser_name == "firefox":
        launcher = playwright_instance.firefox
    elif browser_name == "webkit":
        launcher = playwright_instance.webkit
    else:
        launcher = playwright_instance.chromium
    
    # Launch browser with appropriate settings
    browser = launcher.launch(
        headless=not headed,
        slow_mo=slow_mo,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security'
        ] if browser_name == "chromium" else []
    )
    
    yield browser
    browser.close()

@pytest.fixture
def browser_context(browser: Browser, test_config) -> Generator[BrowserContext, None, None]:
    """Browser context with default configuration"""
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True,
        record_video_dir='reports/videos' if test_config.get('record_video') else None
    )
    
    # Set default timeouts
    context.set_default_timeout(30000)
    context.set_default_navigation_timeout(60000)
    
    yield context
    context.close()

@pytest.fixture
def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """Page fixture with screenshot on failure"""
    page = browser_context.new_page()
    
    yield page
    
    # Take screenshot on test failure
    if hasattr(pytest.current_test, 'failed') and pytest.current_test.failed:
        screenshot_path = f"screenshots/failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        logging.info(f"Screenshot saved: {screenshot_path}")
    
    page.close()

@pytest.fixture
def mobile_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Mobile browser context"""
    context = browser.new_context(
        viewport={'width': 375, 'height': 812},
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True
    )
    
    yield context
    context.close()

@pytest.fixture
def mobile_page(mobile_context: BrowserContext) -> Generator[Page, None, None]:
    """Mobile page fixture"""
    page = mobile_context.new_page()
    yield page
    page.close()

@pytest.fixture
def api_headers(test_config) -> Dict[str, str]:
    """Default API headers"""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'QA-Automation-Framework/1.0'
    }

@pytest.fixture(scope="function")
def test_data():
    """Generate test data for current test"""
    from faker import Faker
    fake = Faker()
    
    return {
        'company_name': fake.company(),
        'user_name': fake.name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'address': fake.address(),
        'project_name': f"Test Project {fake.uuid4()[:8]}",
        'description': fake.text(max_nb_chars=200)
    }

@pytest.fixture(autouse=True)
def test_info(request):
    """Automatically log test information"""
    test_name = request.node.name
    logging.info(f"Starting test: {test_name}")
    
    yield
    
    logging.info(f"Completed test: {test_name}")

@pytest.fixture(scope="function")
def cleanup_projects():
    """Track created projects for cleanup"""
    created_items = []
    
    yield created_items
    
    # Cleanup logic here
    if created_items:
        logging.info(f"Cleaning up {len(created_items)} test items")
        # Implement actual cleanup based on your needs

def pytest_runtest_makereport(item, call):
    """Make test results available to fixtures"""
    if call.when == "call":
        setattr(item, "rep_" + call.when, call)

@pytest.fixture(autouse=True)
def test_result(request):
    """Make test result available"""
    yield
    # This runs after the test
    if hasattr(request.node, "rep_call"):
        if request.node.rep_call.failed:
            pytest.current_test = request.node
            pytest.current_test.failed = True

def pytest_collection_modifyitems(config, items):
    """Modify test collection - add markers based on test names"""
    for item in items:
        # Auto-mark tests based on naming convention
        if "smoke" in item.name:
            item.add_marker(pytest.mark.smoke)
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)
        if "ui" in item.name.lower() or "web" in item.name.lower():
            item.add_marker(pytest.mark.ui)
        if "mobile" in item.name.lower():
            item.add_marker(pytest.mark.mobile)
        if "slow" in item.name.lower() or "performance" in item.name.lower():
            item.add_marker(pytest.mark.slow)

def pytest_html_report_title(report):
    """Customize HTML report title"""
    report.title = "QA Automation Test Report - WorkFlow Pro"

def pytest_html_results_summary(prefix, summary, postfix):
    """Customize HTML report summary"""
    prefix.extend([f"<p>Test Environment: {os.getenv('TEST_ENV', 'staging')}</p>"])
    prefix.extend([f"<p>Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"])
