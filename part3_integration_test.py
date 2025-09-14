"""
Part 3: API + UI Integration Test Solution
Complete flow testing: API project creation -> Web UI verification -> Mobile testing -> Tenant isolation
"""

import pytest
import requests
import json
import time
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Browser, Page, expect
from dataclasses import dataclass
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestProject:
    """Data class for test project information"""
    name: str
    description: str
    team_members: List[str]
    id: Optional[int] = None
    tenant_id: str = ""
    
class APIClient:
    """API client for WorkFlow Pro backend services"""
    
    def __init__(self, base_url: str = "https://app.workflowpro.com/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def authenticate(self, email: str, password: str) -> str:
        """Authenticate and return JWT token"""
        auth_data = {
            "email": email,
            "password": password
        }
        
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json=auth_data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
        
        token_data = response.json()
        token = token_data.get('access_token')
        
        if not token:
            raise Exception("No access token received")
            
        # Set authorization header for future requests
        self.session.headers['Authorization'] = f'Bearer {token}'
        return token
    
    def create_project(self, project: TestProject, tenant_id: str) -> Dict:
        """Create a project via API"""
        # Set tenant header
        headers = {'X-Tenant-ID': tenant_id}
        
        project_data = {
            "name": project.name,
            "description": project.description,
            "team_members": project.team_members
        }
        
        logger.info(f"Creating project via API: {project.name}")
        
        response = self.session.post(
            f"{self.base_url}/projects",
            json=project_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Project creation failed: {response.status_code} - {response.text}")
        
        project_response = response.json()
        logger.info(f"Project created with ID: {project_response.get('id')}")
        
        return project_response
    
    def get_project(self, project_id: int, tenant_id: str) -> Dict:
        """Get project details via API"""
        headers = {'X-Tenant-ID': tenant_id}
        
        response = self.session.get(
            f"{self.base_url}/projects/{project_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get project: {response.status_code} - {response.text}")
        
        return response.json()
    
    def delete_project(self, project_id: int, tenant_id: str) -> bool:
        """Delete project for cleanup"""
        headers = {'X-Tenant-ID': tenant_id}
        
        try:
            response = self.session.delete(
                f"{self.base_url}/projects/{project_id}",
                headers=headers,
                timeout=30
            )
            return response.status_code in [200, 204, 404]  # 404 is OK (already deleted)
        except Exception as e:
            logger.warning(f"Failed to delete project {project_id}: {str(e)}")
            return False

class WebUITester:
    """Web UI testing utilities"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = "https://app.workflowpro.com"
    
    def login(self, email: str, password: str):
        """Login to web application"""
        self.page.goto(f"{self.base_url}/login", wait_until="networkidle")
        
        # Fill login form
        self.page.fill("#email", email)
        self.page.fill("#password", password)
        
        # Submit and wait for dashboard
        with self.page.expect_navigation(wait_until="networkidle"):
            self.page.click("#login-btn")
        
        # Wait for dashboard to load
        expect(self.page).to_have_url_pattern(".*\/dashboard.*")
        self.page.wait_for_selector(".welcome-message", timeout=30000)
    
    def verify_project_in_dashboard(self, project_name: str, timeout: int = 30000) -> bool:
        """Verify project appears in dashboard"""
        logger.info(f"Verifying project '{project_name}' in web dashboard")
        
        # Navigate to projects page if not already there
        if "projects" not in self.page.url:
            self.page.click("a[href*='projects']")
            self.page.wait_for_load_state("networkidle")
        
        # Wait for projects to load
        self.page.wait_for_selector(".project-list", timeout=timeout)
        
        # Look for project by name
        project_locator = self.page.locator(f".project-card:has-text('{project_name}')")
        
        try:
            expect(project_locator).to_be_visible(timeout=timeout)
            logger.info(f"Project '{project_name}' found in web dashboard")
            return True
        except Exception:
            logger.error(f"Project '{project_name}' not found in web dashboard")
            return False
    
    def verify_project_details(self, project: TestProject) -> bool:
        """Verify project details in web UI"""
        project_card = self.page.locator(f".project-card:has-text('{project.name}')")
        project_card.click()
        
        # Wait for project details page
        self.page.wait_for_selector(".project-details", timeout=30000)
        
        # Verify project information
        expect(self.page.locator(".project-title")).to_contain_text(project.name)
        expect(self.page.locator(".project-description")).to_contain_text(project.description)
        
        # Verify team members
        for member in project.team_members:
            expect(self.page.locator(".team-members")).to_contain_text(member)
        
        return True

class MobileTester:
    """Mobile testing utilities using BrowserStack simulation"""
    
    def __init__(self):
        self.mobile_configs = {
            'iphone': {
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'viewport': {'width': 375, 'height': 812},
                'device_scale_factor': 3,
                'is_mobile': True,
                'has_touch': True
            },
            'android': {
                'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'viewport': {'width': 360, 'height': 760},
                'device_scale_factor': 3,
                'is_mobile': True,
                'has_touch': True
            }
        }
    
    def create_mobile_browser(self, device_type: str = 'iphone'):
        """Create browser with mobile configuration"""
        with sync_playwright() as p:
            config = self.mobile_configs[device_type]
            
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(**config)
            page = context.new_page()
            
            return browser, context, page
    
    def test_mobile_accessibility(self, project_name: str, email: str, password: str, device_type: str = 'iphone') -> bool:
        """Test project accessibility on mobile device"""
        logger.info(f"Testing mobile accessibility on {device_type}")
        
        browser, context, page = self.create_mobile_browser(device_type)
        
        try:
            # Login on mobile
            mobile_ui = WebUITester(page)
            mobile_ui.login(email, password)
            
            # Verify project is accessible on mobile
            found = mobile_ui.verify_project_in_dashboard(project_name, timeout=45000)  # Longer timeout for mobile
            
            if found:
                # Test mobile-specific interactions
                self._test_mobile_interactions(page, project_name)
            
            return found
            
        finally:
            browser.close()
    
    def _test_mobile_interactions(self, page: Page, project_name: str):
        """Test mobile-specific interactions"""
        project_card = page.locator(f".project-card:has-text('{project_name}')")
        
        # Test touch interactions
        project_card.tap()  # Use tap instead of click for mobile
        
        # Verify mobile responsive layout
        expect(page.locator(".mobile-nav")).to_be_visible()
        
        # Test swipe gestures if applicable
        if page.locator(".swipeable").count() > 0:
            page.locator(".swipeable").swipe_left()

class TenantIsolationTester:
    """Test tenant isolation and security boundaries"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def verify_tenant_isolation(self, project_id: int, authorized_tenant: str, unauthorized_tenant: str) -> bool:
        """Verify project is only accessible to authorized tenant"""
        logger.info(f"Testing tenant isolation for project {project_id}")
        
        # Should be able to access with authorized tenant
        try:
            authorized_project = self.api_client.get_project(project_id, authorized_tenant)
            logger.info("✓ Authorized tenant can access project")
        except Exception as e:
            logger.error(f"✗ Authorized tenant cannot access project: {str(e)}")
            return False
        
        # Should NOT be able to access with unauthorized tenant
        try:
            unauthorized_project = self.api_client.get_project(project_id, unauthorized_tenant)
            logger.error("✗ Unauthorized tenant can access project - SECURITY ISSUE!")
            return False
        except Exception:
            logger.info("✓ Unauthorized tenant correctly denied access")
            return True

class BrowserStackIntegration:
    """BrowserStack integration for cross-platform testing"""
    
    def __init__(self):
        self.capabilities = {
            'chrome_windows': {
                'browserName': 'Chrome',
                'browserVersion': 'latest',
                'os': 'Windows',
                'osVersion': '10'
            },
            'safari_mac': {
                'browserName': 'Safari',
                'browserVersion': 'latest',
                'os': 'OS X',
                'osVersion': 'Big Sur'
            },
            'chrome_android': {
                'browserName': 'chrome',
                'device': 'Samsung Galaxy S21',
                'realMobile': 'true'
            },
            'safari_ios': {
                'browserName': 'iPhone',
                'device': 'iPhone 13',
                'realMobile': 'true'
            }
        }
    
    def get_browserstack_url(self, username: str, access_key: str) -> str:
        """Get BrowserStack hub URL"""
        return f"https://{username}:{access_key}@hub-cloud.browserstack.com/wd/hub"
    
    def test_cross_platform(self, project_name: str, email: str, password: str) -> Dict[str, bool]:
        """Test across multiple platforms using BrowserStack"""
        results = {}
        
        # Note: In real implementation, you would use actual BrowserStack credentials
        # For this demo, we simulate the cross-platform testing
        
        platforms = ['chrome_windows', 'safari_mac', 'chrome_android', 'safari_ios']
        
        for platform in platforms:
            try:
                logger.info(f"Testing on {platform}")
                
                # Simulate platform-specific testing
                if 'mobile' in platform.lower() or 'android' in platform or 'iphone' in platform:
                    mobile_tester = MobileTester()
                    device_type = 'iphone' if 'ios' in platform else 'android'
                    success = mobile_tester.test_mobile_accessibility(project_name, email, password, device_type)
                else:
                    # Desktop browser testing
                    success = self._test_desktop_platform(platform, project_name, email, password)
                
                results[platform] = success
                
            except Exception as e:
                logger.error(f"Failed testing on {platform}: {str(e)}")
                results[platform] = False
        
        return results
    
    def _test_desktop_platform(self, platform: str, project_name: str, email: str, password: str) -> bool:
        """Test on desktop platform"""
        # In real implementation, this would connect to BrowserStack
        # For demo, we simulate with local browser
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                web_tester = WebUITester(page)
                web_tester.login(email, password)
                return web_tester.verify_project_in_dashboard(project_name)
            finally:
                browser.close()

# MAIN INTEGRATION TEST

@pytest.fixture
def test_project() -> TestProject:
    """Create test project data"""
    unique_id = str(uuid.uuid4())[:8]
    return TestProject(
        name=f"Test Project {unique_id}",
        description=f"Integration test project created at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        team_members=["john.doe@company1.com", "jane.smith@company1.com"]
    )

@pytest.fixture
def api_client() -> APIClient:
    """Create API client"""
    return APIClient()

@pytest.fixture
def cleanup_projects():
    """Fixture to track and cleanup test projects"""
    created_projects = []
    
    yield created_projects
    
    # Cleanup after test
    api_client = APIClient()
    try:
        # Re-authenticate for cleanup
        api_client.authenticate("admin@company1.com", "password123")
        
        for project_info in created_projects:
            project_id, tenant_id = project_info
            api_client.delete_project(project_id, tenant_id)
            logger.info(f"Cleaned up project {project_id}")
    except Exception as e:
        logger.warning(f"Cleanup failed: {str(e)}")

def test_project_creation_flow(test_project: TestProject, api_client: APIClient, cleanup_projects):
    """
    Complete integration test: API creation -> Web UI verification -> Mobile testing -> Tenant isolation
    
    Test Flow:
    1. API: Create project via REST API
    2. Web UI: Verify project appears in dashboard
    3. Mobile: Test mobile accessibility 
    4. Security: Verify tenant isolation
    5. Cross-Platform: Test on multiple browsers/devices
    """
    
    logger.info("=== Starting Complete Project Creation Integration Test ===")
    
    # Test configuration
    COMPANY1_ID = "company1"
    COMPANY2_ID = "company2" 
    ADMIN_EMAIL = "admin@company1.com"
    USER_EMAIL = "user@company2.com"
    PASSWORD = "password123"
    
    created_project_id = None
    
    try:
        # STEP 1: API Project Creation
        logger.info("STEP 1: Creating project via API")
        
        # Authenticate as Company1 admin
        token = api_client.authenticate(ADMIN_EMAIL, PASSWORD)
        assert token, "Failed to authenticate with API"
        
        # Create project via API
        project_response = api_client.create_project(test_project, COMPANY1_ID)
        created_project_id = project_response.get('id')
        test_project.id = created_project_id
        
        # Track for cleanup
        cleanup_projects.append((created_project_id, COMPANY1_ID))
        
        # Verify API response
        assert created_project_id, "No project ID returned from API"
        assert project_response.get('name') == test_project.name
        assert project_response.get('status') == 'active'
        
        logger.info(f"✓ Project created via API with ID: {created_project_id}")
        
        # STEP 2: Web UI Verification
        logger.info("STEP 2: Verifying project in Web UI")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                web_tester = WebUITester(page)
                web_tester.login(ADMIN_EMAIL, PASSWORD)
                
                # Wait a moment for data synchronization
                time.sleep(2)
                
                # Verify project appears in dashboard
                project_found = web_tester.verify_project_in_dashboard(test_project.name)
                assert project_found, f"Project '{test_project.name}' not found in web dashboard"
                
                # Verify project details
                web_tester.verify_project_details(test_project)
                
                logger.info("✓ Project verified in Web UI")
                
            finally:
                browser.close()
        
        # STEP 3: Mobile Accessibility Testing
        logger.info("STEP 3: Testing mobile accessibility")
        
        mobile_tester = MobileTester()
        
        # Test on iPhone
        iphone_success = mobile_tester.test_mobile_accessibility(
            test_project.name, ADMIN_EMAIL, PASSWORD, 'iphone'
        )
        assert iphone_success, "Project not accessible on iPhone"
        
        # Test on Android
        android_success = mobile_tester.test_mobile_accessibility(
            test_project.name, ADMIN_EMAIL, PASSWORD, 'android'
        )
        assert android_success, "Project not accessible on Android"
        
        logger.info("✓ Project accessible on mobile devices")
        
        # STEP 4: Tenant Isolation Testing
        logger.info("STEP 4: Verifying tenant isolation")
        
        tenant_tester = TenantIsolationTester(api_client)
        isolation_verified = tenant_tester.verify_tenant_isolation(
            created_project_id, COMPANY1_ID, COMPANY2_ID
        )
        assert isolation_verified, "Tenant isolation failed - SECURITY ISSUE!"
        
        logger.info("✓ Tenant isolation verified")
        
        # STEP 5: Cross-Platform Testing
        logger.info("STEP 5: Cross-platform testing")
        
        browserstack = BrowserStackIntegration()
        platform_results = browserstack.test_cross_platform(
            test_project.name, ADMIN_EMAIL, PASSWORD
        )
        
        # Verify at least 80% of platforms passed
        success_rate = sum(platform_results.values()) / len(platform_results)
        assert success_rate >= 0.8, f"Cross-platform success rate too low: {success_rate:.2%}"
        
        logger.info(f"✓ Cross-platform testing completed - Success rate: {success_rate:.2%}")
        
        # Log detailed results
        for platform, success in platform_results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {platform}")
        
        logger.info("=== Integration Test PASSED ===")
        
    except Exception as e:
        logger.error(f"Integration test failed: {str(e)}")
        raise
        
    finally:
        # Additional cleanup verification
        if created_project_id:
            try:
                # Verify project can be accessed before cleanup
                api_client.get_project(created_project_id, COMPANY1_ID)
                logger.info("Project verified before cleanup")
            except Exception:
                logger.warning("Project not found before cleanup")

# EDGE CASE TESTS

def test_network_failure_handling(test_project: TestProject, api_client: APIClient):
    """Test handling of network failures during integration"""
    logger.info("Testing network failure handling")
    
    # Simulate network timeout by using invalid endpoint
    original_base_url = api_client.base_url
    api_client.base_url = "https://invalid-endpoint.workflowpro.com/api/v1"
    
    try:
        with pytest.raises(Exception) as exc_info:
            api_client.authenticate("admin@company1.com", "password123")
        
        assert "timeout" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()
        logger.info("✓ Network failure handled correctly")
        
    finally:
        api_client.base_url = original_base_url

def test_slow_loading_conditions(test_project: TestProject):
    """Test behavior under slow loading conditions"""
    logger.info("Testing slow loading conditions")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Simulate slow network
            page.route("**/*", lambda route: (
                time.sleep(2),  # Add 2 second delay
                route.continue_()
            ))
            
            web_tester = WebUITester(page)
            
            # Should still work with longer timeouts
            start_time = time.time()
            web_tester.login("admin@company1.com", "password123")
            login_time = time.time() - start_time
            
            # Verify it took longer than normal (accounting for delays)
            assert login_time > 4, f"Login was too fast: {login_time}s"
            logger.info(f"✓ Slow loading handled correctly - Login took {login_time:.2f}s")
            
        finally:
            browser.close()

def test_mobile_responsiveness(test_project: TestProject):
    """Test mobile responsiveness across different screen sizes"""
    logger.info("Testing mobile responsiveness")
    
    screen_sizes = [
        {'width': 320, 'height': 568},  # iPhone SE
        {'width': 375, 'height': 812},  # iPhone 12
        {'width': 414, 'height': 896},  # iPhone 12 Pro Max
        {'width': 360, 'height': 640},  # Android Small
        {'width': 768, 'height': 1024}, # Tablet
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for size in screen_sizes:
            logger.info(f"Testing screen size: {size['width']}x{size['height']}")
            
            context = browser.new_context(
                viewport=size,
                is_mobile=True,
                has_touch=True
            )
            page = context.new_page()
            
            try:
                web_tester = WebUITester(page)
                web_tester.login("admin@company1.com", "password123")
                
                # Verify responsive elements are present
                expect(page.locator(".mobile-nav")).to_be_visible()
                
                logger.info(f"✓ Responsive design works at {size['width']}x{size['height']}")
                
            finally:
                context.close()
                
        browser.close()

# PERFORMANCE AND LOAD TESTS

@pytest.mark.performance
def test_concurrent_project_creation():
    """Test creating multiple projects concurrently"""
    import threading
    import queue
    
    logger.info("Testing concurrent project creation")
    
    results_queue = queue.Queue()
    num_threads = 5
    
    def create_project_worker(worker_id):
        try:
            api_client = APIClient()
            api_client.authenticate("admin@company1.com", "password123")
            
            project = TestProject(
                name=f"Concurrent Test Project {worker_id}",
                description=f"Created by worker {worker_id}",
                team_members=[f"user{worker_id}@company1.com"]
            )
            
            response = api_client.create_project(project, "company1")
            results_queue.put((worker_id, True, response.get('id')))
            
        except Exception as e:
            logger.error(f"Worker {worker_id} failed: {str(e)}")
            results_queue.put((worker_id, False, None))
    
    # Start threads
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=create_project_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Collect results
    successful_creations = 0
    created_project_ids = []
    
    while not results_queue.empty():
        worker_id, success, project_id = results_queue.get()
        if success:
            successful_creations += 1
            created_project_ids.append(project_id)
    
    # Verify at least 80% success rate
    success_rate = successful_creations / num_threads
    assert success_rate >= 0.8, f"Concurrent creation success rate too low: {success_rate:.2%}"
    
    logger.info(f"✓ Concurrent project creation - Success rate: {success_rate:.2%}")
    
    # Cleanup
    try:
        cleanup_api = APIClient()
        cleanup_api.authenticate("admin@company1.com", "password123")
        for project_id in created_project_ids:
            cleanup_api.delete_project(project_id, "company1")
    except Exception as e:
        logger.warning(f"Cleanup failed: {str(e)}")

if __name__ == "__main__":
    # Run the integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "--html=reports/integration_report.html",
        "--self-contained-html",
        "-m", "not performance"  # Skip performance tests in regular runs
    ])
