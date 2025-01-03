"""Commit Types und Beispiele für Git Commits"""

COMMIT_TYPES = {
    "feat": {
        "description": "New Feature or Enhancement",
        "priority": 1,
        "examples": [
            "Add PerformanceMetrics for real-time monitoring",
            "Implement AI-powered code suggestions",
            "Updated Layout processing with forms and key-value areas",
            "Create WebSocket connection handler",
            "Create a backend to transform PubMed XML files to DoclingDocument",
            "Implement real-time search functionality"
        ]
    },
    "fix": {
        "description": "Bug Fix or Error Resolution", 
        "priority": 2,
        "examples": [
            "Fix memory leak in WebSocket connection",
            "Resolve race condition in state updates",
            "Fix broken API endpoint validation",
            "Fix performance bottleneck in search",
            "Do not import python modules from deepsearch-glm",
            "Correcting DefaultText ID for MS Word backend",
            "restore pydantic version pin after fixes"
        ]
    },
    "docs": {
        "description": "Documentation Updates",
        "priority": 3,
        "examples": [
            "Update API documentation with new endpoints",
            "Add performance monitoring guide",
            "Improve setup instructions for developers",
            "Document new authentication flow",
            "add DocETL, Kotaemon, spaCy integrations; minor docs improvements",
            "Update component usage examples"
        ]
    },
    "refactor": {
        "description": "Code Restructuring & Improvements",
        "priority": 4,
        "examples": [
            "Refactor performance monitoring system",
            "Simplify authentication logic",
            "Move metrics logic to separate module",
            "Restructure component hierarchy",
            "Convert class components to hooks",
            "Optimize database queries"
        ]
    },
    "test": {
        "description": "Testing Improvements",
        "priority": 4,
        "examples": [
            "Add performance metrics unit tests",
            "Update WebSocket integration tests",
            "Add authentication flow tests",
            "Fix flaky component tests",
            "Add load testing suite",
            "Improve test coverage"
        ]
    }
} 