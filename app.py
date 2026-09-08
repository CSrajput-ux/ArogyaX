"""
ArogyaX Healthcare Platform — Main Application Entry Point
Architecture: Modular Flask Factory with Blueprint Separation
Frontend: frontend/templates & frontend/static
Backend: backend/ (routes, services, security, middleware, database, config)
"""

import os
import sys

# Ensure UTF-8 output encoding support on Windows terminal
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    print("==================================================")
    print(" [OK] ArogyaX Healthcare Platform Server Initializing")
    print(f" [*] Local URL: http://localhost:{port}")
    print("==================================================")
    app.run(host='0.0.0.0', port=port, debug=debug)
