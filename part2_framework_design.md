qa-automation-framework/
├── config/                          # Configuration management
│   ├── __init__.py
│   ├── environments.py              # Environment configuration loader
│   ├── dev.json                     # Development environment config
│   ├── staging.json                 # Staging environment config  
│   ├── prod.json                    # Production environment config
│   └── browserstack.json            # BrowserStack configuration
├── core/                            # Core framework components
│   ├── __init__.py
│   ├── base_test.py                 # Base test class with common functionality
│   ├── browser_factory.py          # Browser instantiation and management
│   ├── mobile_factory.py           # Mobile device configuration
│   └── test_context.py             # Test execution context manager
├── pages/                           # Page Object Model
│   ├── __init__.py
│   ├── base_page.py                 # Base page class with common methods
│   ├── components/                  # Reusable UI components
│   │   ├── __init__.py
│   │   ├── navigation.py            # Navigation component
│   │   ├── modal.py                 # Modal dialogs
│   │   └── forms.py                 # Form components
│   ├── web/                         # Web-specific pages
│   │   ├── __init__.py
│   │   ├── login_page.py
│   │   ├── dashboard_page.py
│   │   ├── projects_page.py
│   │   └── settings_page.py
│   └── mobile/                      # Mobile-specific pages
│       ├── __init__.py
│       ├── mobile_login_page.py
│       └── mobile_dashboard_page.py
├── api/                             # API testing framework
│   ├── __init__.py
│   ├── base_api.py                  # Base API client
│   ├── clients/                     # API clients for different services
│   │   ├── __init__.py
│   │   ├── auth_client.py           # Authentication API
│   │   ├── project_client.py        # Project management API
│   │   ├── user_client.py           # User management API
│   │   └── tenant_client.py         # Tenant management API
│   └── models/                      # API response models
│       ├── __init__.py
│       ├── project_model.py
│       ├── user_model.py
│       └── tenant_model.py
├── utils/                           # Utility functions and helpers
│   ├── __init__.py
│   ├── test_data_manager.py         # Test data generation and management
│   ├── database_helper.py           # Database operations
│   ├── file_helper.py               # File operations
│   ├── encryption_helper.py         # Data encryption/decryption
│   ├── screenshot_helper.py         # Screenshot utilities
│   └── retry_helper.py              # Retry mechanisms
├── integrations/                    # Third-party integrations
│   ├── __init__.py
│   ├── browserstack_integration.py  # BrowserStack cloud testing
│   ├── slack_integration.py         # Slack notifications
│   ├── jira_integration.py          # JIRA issue tracking
│   └── allure_integration.py        # Allure reporting
├── tests/                           # Test suites
│   ├── __init__.py
│   ├── conftest.py                  # Test configuration
│   ├── smoke/                       # Smoke tests
│   │   ├── __init__.py
│   │   ├── test_login_smoke.py
│   │   └── test_critical_path.py
│   ├── regression/                  # Full regression suite
│   │   ├── __init__.py
│   │   ├── web/
│   │   │   ├── test_user_management.py
│   │   │   ├── test_project_management.py
│   │   │   └── test_tenant_isolation.py
│   │   ├── api/
│   │   │   ├── test_api_authentication.py
│   │   │   ├── test_api_projects.py
│   │   │   └── test_api_security.py
│   │   └── mobile/
│   │       ├── test_mobile_login.py
│   │       └── test_mobile_projects.py
│   ├── integration/                 # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api_ui_integration.py
│   │   └── test_cross_platform.py
│   └── performance/                 # Performance tests
│       ├── __init__.py
│       ├── test_load_performance.py
│       └── test_stress_testing.py
├── data/                            # Test data
│   ├── test_users.json              # Test user accounts
│   ├── test_projects.json           # Project test data
│   ├── tenant_configs.json          # Tenant configurations
│   └── sql/                         # Database scripts
│       ├── setup_test_data.sql
│       └── cleanup_test_data.sql
├── reports/                         # Test reports and artifacts
│   ├── html/                        # HTML reports
│   ├── allure-results/              # Allure test results
│   ├── screenshots/                 # Test screenshots
│   ├── videos/                      # Test execution videos
│   └── logs/                        # Test execution logs
├── scripts/                         # Utility scripts
│   ├── setup_environment.py         # Environment setup
│   ├── data_seeder.py              # Test data seeding
│   ├── cleanup_script.py           # Test cleanup
│   └── run_tests.sh                # Test execution script
├── docker/                          # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── playwright.dockerfile
├── .github/                         # GitHub Actions CI/CD
│   └── workflows/
│       ├── pr-tests.yml            # Pull request testing
│       ├── nightly-regression.yml   # Nightly regression
│       └── cross-platform.yml      # Cross-platform testing
├── requirements.txt                 # Python dependencies
├── pytest.ini                      # Pytest configuration
├── conftest.py                     # Global pytest configuration
├── README.md                       # Framework documentation
└── .env.example                    # Environment variables template
