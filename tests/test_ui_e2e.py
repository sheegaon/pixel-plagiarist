"""
End-to-end UI tests for Pixel Plagiarist using Selenium WebDriver.

These tests simulate real user interactions with the game including:
- Creating and joining rooms
- Drawing and submitting artwork
- Copying phase interactions
- Voting on drawings
- Complete game flow with AI players

Run with: pytest tests/test_ui_e2e.py -v -s --log-cli-level=INFO --full-trace
"""

import pytest
import time
import subprocess
import os
import signal
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from util.logging_utils import info_log, setup_logging

# Test configuration
SERVER_HOST = "localhost"
SERVER_PORT = 5002  # Use different port for testing
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
CHROME_DRIVER_PATH = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
setup_logging()


class TestFixtures:
    """Shared test fixtures and utilities"""

    @staticmethod
    def wait_for_element(driver, by, value, timeout=10):
        """Wait for element to be present and visible"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            info_log(f"Element not found: {by}={value}")
            raise

    @staticmethod
    def wait_for_clickable(driver, by, value, timeout=10):
        """Wait for element to be clickable"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            info_log(f"Element not clickable: {by}={value}")
            raise

    @staticmethod
    def wait_for_text_in_element(driver, by, value, text, timeout=10):
        """Wait for specific text to appear in element"""
        try:
            WebDriverWait(driver, timeout).until(
                EC.text_to_be_present_in_element((by, value), text)
            )
            return True
        except TimeoutException:
            info_log(f"Text '{text}' not found in element: {by}={value}")
            return False

    @staticmethod
    def draw_simple_shape(driver, canvas_id="drawingCanvas"):
        """Draw a simple X shape on the canvas"""
        canvas = TestFixtures.wait_for_element(driver, By.ID, canvas_id)

        # Get canvas dimensions and center
        canvas_width = canvas.get_attribute("width") or "400"
        canvas_height = canvas.get_attribute("height") or "300"
        width = int(canvas_width)
        height = int(canvas_height)

        actions = ActionChains(driver)

        # Draw an X - line from top-left to bottom-right
        actions.move_to_element_with_offset(canvas, -width // 4, -height // 4)
        actions.click_and_hold()
        actions.move_by_offset(width // 2, height // 2)
        actions.release()

        # Draw second line from top-right to bottom-left
        actions.move_to_element_with_offset(canvas, width // 4, -height // 4)
        actions.click_and_hold()
        actions.move_by_offset(-width // 2, height // 2)
        actions.release()

        actions.perform()
        time.sleep(0.5)  # Allow drawing to register

        info_log(f"Drew simple X shape on canvas: {canvas_id}")


@pytest.fixture(scope="session")
def server_process():
    """Start Flask server in testing mode for the entire test session"""
    info_log("Starting Flask server in testing mode...")

    # Set environment variables for testing
    env = os.environ.copy()
    env["TESTING_MODE"] = "true"
    env["PORT"] = str(SERVER_PORT)
    env["FLASK_ENV"] = "testing"  # Use testing environment
    env["DEBUG_MODE"] = "false"  # Disable debug mode for tests
    env["WERKZEUG_ALLOW_ASYNC_UNSAFE"] = "true"  # Allow async unsafe for testing
    env["USE_RELOADER"] = "false"  # Disable reloader

    # Start server process
    cmd = [sys.executable, "server.py"]
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=r"w:/tfishman/code/qr-fi-isa/pixel_plagiarist"  # Path(__file__).parent.parent  # Run from project root
    )
    import time

    # Wait for server to start
    max_retries = 5
    for i in range(max_retries):
        try:
            import requests
            response = requests.get(f"{BASE_URL}/", timeout=2)
            if response.status_code in [200, 302]:  # 302 for login redirect
                info_log(f"Server started successfully on port {SERVER_PORT}")
                break
        except:
            time.sleep(1)
    else:
        proc.terminate()
        proc.wait()
        raise RuntimeError("Server failed to start within timeout")

    yield proc

    # Cleanup
    info_log("Shutting down Flask server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture
def chrome_driver():
    """Create Chrome WebDriver instance for each test"""
    options = Options()
    options.add_argument("--headless")  # Run headless for CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")

    # Try to find chromedriver
    service = None
    if os.path.exists(CHROME_DRIVER_PATH):
        service = Service(CHROME_DRIVER_PATH)

    try:
        if service:
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)  # Use PATH
    except Exception as e:
        pytest.skip(f"Chrome driver not available: {e}")

    driver.implicitly_wait(5)
    yield driver

    # Cleanup
    try:
        driver.quit()
    except:
        pass


@pytest.fixture
def ai_players():
    """Spawn AI players for multiplayer testing"""
    processes = []

    def spawn_ais(count=2, host=SERVER_HOST, port=SERVER_PORT):
        """Spawn specified number of AI players"""
        for i in range(count):
            cmd = [
                sys.executable, "ai_player.py",
                "--name", f"TestBot{i + 1}",
                "--host", host,
                "--port", str(port),
                "--count", "1"
            ]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            processes.append(proc)
            time.sleep(0.5)  # Stagger connections

        info_log(f"Spawned {count} AI players")
        time.sleep(2)  # Allow AIs to connect
        return processes

    yield spawn_ais

    # Cleanup AI processes
    info_log("Cleaning up AI players...")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        except:
            pass


def login_as_guest(driver, username="TestUser"):
    """Helper to login as guest user"""
    info_log(f"Logging in as guest: {username}")

    # Navigate to login page
    driver.get(f"{BASE_URL}/login")

    # Wait for login form
    username_input = TestFixtures.wait_for_element(driver, By.NAME, "username")
    username_input.clear()
    username_input.send_keys(username)

    # Submit login form
    login_btn = TestFixtures.wait_for_clickable(driver, By.CSS_SELECTOR, ".username-login-btn")
    login_btn.click()

    # Wait for redirect to main game
    TestFixtures.wait_for_element(driver, By.ID, "homeScreen", timeout=10)
    info_log("Successfully logged in and redirected to game")


class TestRoomManagement:
    """Test room creation, joining, and management"""

    def test_create_bronze_room(self, server_process, chrome_driver):
        """Test creating a Bronze level room"""
        driver = chrome_driver
        login_as_guest(driver, "RoomCreator")

        # Wait for home screen to load
        TestFixtures.wait_for_element(driver, By.ID, "homeScreen")

        # Create Bronze room (100 stake)
        bronze_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//button[contains(text(), 'Create Bronze Level Room')]"
        )
        bronze_btn.click()

        # Wait for room creation and transition to waiting screen
        TestFixtures.wait_for_element(driver, By.ID, "waitingScreen", timeout=10)

        # Verify we're in waiting phase
        phase_indicator = TestFixtures.wait_for_element(driver, By.CLASS_NAME, "phase-indicator")
        assert "Waiting for Players" in phase_indicator.text

        # Verify room info is displayed
        room_info = TestFixtures.wait_for_element(driver, By.ID, "roomInfo")
        assert "Room:" in room_info.text

        info_log("Successfully created Bronze room")

    def test_join_room_by_code(self, server_process, chrome_driver, ai_players):
        """Test joining a room using room code"""
        driver = chrome_driver

        # First, spawn an AI to create a room
        ai_processes = ai_players(1)
        time.sleep(3)  # Allow AI to create room

        login_as_guest(driver, "RoomJoiner")

        # Click join by room code button
        join_code_btn = TestFixtures.wait_for_clickable(
            driver, By.CSS_SELECTOR, ".join-code-btn"
        )
        join_code_btn.click()

        # Wait for modal to appear
        modal = TestFixtures.wait_for_element(driver, By.ID, "joinCodeModal")

        # For this test, we'll need to get a real room code from the room list
        # Cancel modal and check room list first
        close_btn = driver.find_element(By.CLASS_NAME, "close")
        close_btn.click()

        # Refresh room list to see AI-created rooms
        refresh_btn = TestFixtures.wait_for_clickable(driver, By.CSS_SELECTOR, ".refresh-btn")
        refresh_btn.click()
        time.sleep(2)

        # Check if any rooms are available
        room_list = driver.find_element(By.ID, "roomList")
        room_items = room_list.find_elements(By.CSS_SELECTOR, ".room-item.clickable")

        if room_items:
            # Click on first available room
            room_items[0].click()

            # Wait for joining
            TestFixtures.wait_for_element(driver, By.ID, "waitingScreen", timeout=10)

            # Verify we joined successfully
            phase_indicator = TestFixtures.wait_for_element(driver, By.CLASS_NAME, "phase-indicator")
            assert "Waiting for Players" in phase_indicator.text

            info_log("Successfully joined room from list")
        else:
            info_log("No rooms available for joining test")

    def test_leave_room(self, server_process, chrome_driver):
        """Test leaving a room during waiting phase"""
        driver = chrome_driver
        login_as_guest(driver, "RoomLeaver")

        # Create a room first
        bronze_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//button[contains(text(), 'Create Bronze Level Room')]"
        )
        bronze_btn.click()

        # Wait for waiting screen
        TestFixtures.wait_for_element(driver, By.ID, "waitingScreen")

        # Click leave room button
        leave_btn = TestFixtures.wait_for_clickable(driver, By.CSS_SELECTOR, ".leave-room-btn")
        leave_btn.click()

        # Wait for return to home screen
        TestFixtures.wait_for_element(driver, By.ID, "homeScreen", timeout=10)

        # Verify we're back on home screen
        assert driver.find_element(By.ID, "homeScreen").is_displayed()

        info_log("Successfully left room and returned to home")


class TestGameFlow:
    """Test complete game flow including all phases"""

    def test_complete_game_flow(self, server_process, chrome_driver, ai_players):
        """Test complete game flow from room creation to results"""
        driver = chrome_driver
        login_as_guest(driver, "GamePlayer")

        # Spawn 2 AI players to fill minimum players requirement
        ai_processes = ai_players(2)

        # Create Bronze room
        bronze_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//button[contains(text(), 'Create Bronze Level Room')]"
        )
        bronze_btn.click()

        # Wait for waiting screen
        TestFixtures.wait_for_element(driver, By.ID, "waitingScreen")

        # Wait for countdown to start (minimum players reached)
        countdown_display = TestFixtures.wait_for_element(
            driver, By.ID, "countdownDisplay", timeout=15
        )
        assert countdown_display.is_displayed()

        # Wait for game to start (transition to drawing phase)
        TestFixtures.wait_for_element(driver, By.ID, "drawingScreen", timeout=20)

        # Verify drawing phase
        phase_indicator = driver.find_element(By.CLASS_NAME, "phase-indicator")
        assert "Original Drawing Phase" in phase_indicator.text

        # Wait for prompt to load
        prompt_text = TestFixtures.wait_for_element(driver, By.ID, "drawingPromptText")
        assert len(prompt_text.text) > 0

        info_log(f"Drawing prompt: {prompt_text.text}")

        # Draw something on canvas
        TestFixtures.draw_simple_shape(driver, "drawingCanvas")

        # Submit drawing
        submit_btn = TestFixtures.wait_for_clickable(driver, By.ID, "submitDrawingBtn")
        submit_btn.click()

        # Wait for copying phase
        TestFixtures.wait_for_element(driver, By.ID, "copyingScreen", timeout=30)

        # Verify copying phase
        phase_indicator = driver.find_element(By.CLASS_NAME, "phase-indicator")
        assert "Copying Phase" in phase_indicator.text

        # Draw copy (simple shape)
        TestFixtures.draw_simple_shape(driver, "copyingCanvas")

        # Submit copy
        submit_copy_btn = TestFixtures.wait_for_clickable(driver, By.ID, "submitCopyBtn")
        submit_copy_btn.click()

        # Wait for voting phase
        TestFixtures.wait_for_element(driver, By.ID, "votingScreen", timeout=30)

        # Verify voting phase
        phase_indicator = driver.find_element(By.CLASS_NAME, "phase-indicator")
        assert "Voting Phase" in phase_indicator.text

        # Wait for voting options to load
        voting_grid = TestFixtures.wait_for_element(driver, By.ID, "votingGrid")
        voting_options = WebDriverWait(driver, 10).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, ".voting-option")
        )

        if voting_options:
            # Click on first voting option (auto-submits)
            voting_options[0].click()

            # Wait a moment for vote submission
            time.sleep(2)

            info_log("Submitted vote")

        # Wait for results phase
        TestFixtures.wait_for_element(driver, By.ID, "resultsScreen", timeout=30)

        # Verify results phase
        phase_indicator = driver.find_element(By.CLASS_NAME, "phase-indicator")
        assert "Game Results" in phase_indicator.text

        # Verify results are displayed
        results_grid = TestFixtures.wait_for_element(driver, By.ID, "resultsGrid")
        assert results_grid.is_displayed()

        # Look for return home button
        return_home_btn = TestFixtures.wait_for_element(
            driver, By.XPATH, "//button[contains(text(), 'Return Home')]"
        )
        assert return_home_btn.is_displayed()

        info_log("Successfully completed full game flow!")

    def test_drawing_phase_auto_submit(self, server_process, chrome_driver, ai_players):
        """Test auto-submission in drawing phase when timer expires"""
        driver = chrome_driver
        login_as_guest(driver, "AutoSubmitTest")

        # Spawn AIs and create room
        ai_processes = ai_players(2)

        bronze_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//button[contains(text(), 'Create Bronze Level Room')]"
        )
        bronze_btn.click()

        # Wait for game to start
        TestFixtures.wait_for_element(driver, By.ID, "drawingScreen", timeout=30)

        # Don't draw anything - let timer expire
        # In testing mode, timers are 5 seconds, so wait for auto-submission

        # Wait for transition to copying phase (auto-submit occurred)
        TestFixtures.wait_for_element(driver, By.ID, "copyingScreen", timeout=15)

        phase_indicator = driver.find_element(By.CLASS_NAME, "phase-indicator")
        assert "Copying Phase" in phase_indicator.text

        info_log("Auto-submission worked correctly")


class TestUIInteractions:
    """Test specific UI interactions and edge cases"""

    def test_modal_interactions(self, server_process, chrome_driver):
        """Test modal opening, closing, and form validation"""
        driver = chrome_driver
        login_as_guest(driver, "ModalTester")

        # Test join code modal
        join_code_btn = TestFixtures.wait_for_clickable(driver, By.CSS_SELECTOR, ".join-code-btn")
        join_code_btn.click()

        # Verify modal is visible
        modal = TestFixtures.wait_for_element(driver, By.ID, "joinCodeModal")
        assert modal.is_displayed()

        # Test closing with X button
        close_btn = driver.find_element(By.CLASS_NAME, "close")
        close_btn.click()

        # Wait for modal to hide
        time.sleep(0.5)
        assert not modal.is_displayed()

        # Test opening again and form validation
        join_code_btn.click()
        TestFixtures.wait_for_element(driver, By.ID, "joinCodeModal")

        # Try to join with empty code
        join_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Join Room')]")
        join_btn.click()

        # Should show error (though we can't easily verify error message display)
        info_log("Modal interactions test completed")

    def test_canvas_drawing_tools(self, server_process, chrome_driver, ai_players):
        """Test canvas drawing tools and interactions"""
        driver = chrome_driver
        login_as_guest(driver, "CanvasTester")

        # Create room and get to drawing phase
        ai_processes = ai_players(2)

        bronze_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//button[contains(text(), 'Create Bronze Level Room')]"
        )
        bronze_btn.click()

        # Wait for drawing phase
        TestFixtures.wait_for_element(driver, By.ID, "drawingScreen", timeout=30)

        # Test canvas is present and drawable
        canvas = TestFixtures.wait_for_element(driver, By.ID, "drawingCanvas")
        assert canvas.is_displayed()

        # Test drawing
        TestFixtures.draw_simple_shape(driver, "drawingCanvas")

        # Test undo button
        undo_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//div[contains(text(), 'Undo')]"
        )
        undo_btn.click()

        info_log("Canvas drawing tools test completed")

    def test_responsive_elements(self, server_process, chrome_driver):
        """Test responsive design elements"""
        driver = chrome_driver

        # Test different window sizes
        sizes = [(1920, 1080), (768, 1024), (480, 800)]

        for width, height in sizes:
            driver.set_window_size(width, height)
            time.sleep(0.5)

            login_as_guest(driver, f"ResponsiveTest{width}")

            # Verify key elements are visible
            home_screen = TestFixtures.wait_for_element(driver, By.ID, "homeScreen")
            assert home_screen.is_displayed()

            # Check room sections are present
            room_sections = driver.find_element(By.CSS_SELECTOR, ".room-sections")
            assert room_sections.is_displayed()

            info_log(f"Responsive test passed for {width}x{height}")


class TestErrorHandling:
    """Test error conditions and edge cases"""

    def test_invalid_room_join(self, server_process, chrome_driver):
        """Test joining non-existent room"""
        driver = chrome_driver
        login_as_guest(driver, "ErrorTester")

        # Open join modal
        join_code_btn = TestFixtures.wait_for_clickable(driver, By.CSS_SELECTOR, ".join-code-btn")
        join_code_btn.click()

        # Enter invalid room code
        room_input = TestFixtures.wait_for_element(driver, By.ID, "roomCodeInputModal")
        room_input.clear()
        room_input.send_keys("INVALID")

        # Try to join
        join_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Join Room')]")
        join_btn.click()

        # Should remain on home screen (join failed)
        time.sleep(2)
        assert driver.find_element(By.ID, "homeScreen").is_displayed()

        info_log("Invalid room join handled correctly")

    def test_disconnection_handling(self, server_process, chrome_driver, ai_players):
        """Test handling of disconnections during game"""
        driver = chrome_driver
        login_as_guest(driver, "DisconnectTest")

        # Start a game
        ai_processes = ai_players(2)

        bronze_btn = TestFixtures.wait_for_clickable(
            driver, By.XPATH, "//button[contains(text(), 'Create Bronze Level Room')]"
        )
        bronze_btn.click()

        # Wait for waiting phase
        TestFixtures.wait_for_element(driver, By.ID, "waitingScreen")

        # Simulate refresh (disconnection/reconnection)
        driver.refresh()

        # Should redirect to login
        TestFixtures.wait_for_element(driver, By.NAME, "username", timeout=10)

        info_log("Disconnection handling test completed")


# Test configuration and markers
pytestmark = pytest.mark.slow

if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
