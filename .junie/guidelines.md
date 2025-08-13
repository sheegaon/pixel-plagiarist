# Junie Project Guidelines

Project overview
- Pixel Plagiarist is a real-time, multiplayer, web-based drawing and social deduction game. Players draw an original based on a prompt, create convincing copies of others’ drawings, and vote to spot originals. Scores and token rewards are based on deception success and voting accuracy.

Tech stack
- Backend: Python Flask + Flask-SocketIO (WebSockets via eventlet)
- Frontend: Vanilla JavaScript modules, HTML/CSS, HTML5 Canvas
- Deployment: Heroku-ready (Procfile present)

Project structure (high level)
- server.py: Flask app entry point and Socket.IO setup
- ai_player.py: CLI to spawn AI players for testing
- game_logic/: Core game state and phase logic (drawing, copying, voting, timers, scoring)
- socket_handlers/: Socket.IO event handlers (connection, rooms, gameplay)
- static/: Frontend assets (js, css, images)
- templates/: HTML templates
- util/: Utilities and configuration (e.g., config.json, logging)
- tests/: Pytest suites (integration and optional E2E via Selenium)

Local development
1) Python environment
- Use Python 3.10+ (recommended). Create/activate a virtualenv.
2) Install runtime deps
- pip install -r requirements.txt
3) Run the server
- python server.py
- Visit http://localhost:5000
4) Useful env vars (optional)
- PORT: HTTP port (default 5000)
- FLASK_ENV: development | testing | production
- DEBUG_MODE: true | false
- TESTING_MODE: true | false (some tests/fixtures rely on this)

Testing
- Framework: pytest
- Install dev tools (not in requirements.txt):
  - pip install pytest selenium requests
- Quick integration tests (headless, no browser required):
  - pytest tests/test_integration.py -q
  - or run the full suite: pytest -q
- Optional end-to-end UI tests (Selenium/Chrome):
  - Requires Chrome/Chromium and matching ChromeDriver on PATH
  - Example: pytest tests/test_ui_e2e.py -v -s --log-cli-level=INFO --full-trace
  - E2E fixtures will start the Flask server and can spawn AI players automatically

Build and deploy
- Heroku: Procfile provided (web: python server.py). Ensure config vars and a suitable Socket.IO async worker (eventlet) are available. Alternative WSGI command (example): gunicorn -k eventlet -w 1 server:app

Coding conventions
- Follow PEP 8 for Python. Prefer clear, small functions with docstrings.
- Use type hints where practical.
- Keep game logic pure and deterministic where possible; side effects live at boundaries (handlers, I/O).

Junie workflow expectations
- Prefer minimal, targeted changes that directly address the issue.
- Before submitting code changes:
  - If Python logic changed: run pytest tests/test_integration.py -q (or pytest -q for full suite).
  - If UI/templates/static changed: smoke test locally (python server.py) and interact with main flows.
  - E2E UI tests are optional and may require local ChromeDriver; run when relevant to UI flows.
- Do not modify tests unless a test is incorrect relative to established behavior documented in README.md/ARCHITECTURE.md.
- Avoid altering persistent artifacts (e.g., pixel_plagiarist.db) unless the task requires it.

References
- See README.md for gameplay details, scoring, and setup.
- See ARCHITECTURE.md for module responsibilities and data flow.
- See DEPLOYING_TO_HEROKU.md for deployment specifics.
