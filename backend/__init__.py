"""Backend package for Adaptive Planner.

This file is intentionally lightweight.
Do not import Flask app objects here, because importing the backend package
must not start the application, database connection, routes, or ML services.
"""
