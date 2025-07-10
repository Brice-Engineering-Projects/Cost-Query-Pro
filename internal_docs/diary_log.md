# Diary Logs

==============================================

Date:  July 9, 2025

==============================================

### Summary of Modifications

1. Migrations
   - Move database URL configuration to settings-based approach
   - Consolidate Base model definition in db/__init__.py
   - Restructure migrations for better separation of concerns
   - Update model imports to use consolidated base
   - Split schema migrations into users and other tables

2. Tests
    - Create tests for auth
    - Create tests for routes
    - Create conftest file

# Next Task
    - Run pytest
    - Debug errors
