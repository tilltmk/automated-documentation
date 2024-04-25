import time
import os
import sys
import re
import platform
import subprocess
import threading
import keyboard
import clipboard
import markdown2
import customtkinter as ctk
import ollama

# Check the operating system and import necessary modules accordingly
if platform.system() == "Linux":
    import mss
    import mss.tools
elif platform.system() == "Windows":
    import pyscreenshot as ImageGrab
    import pygetwindow as gw

def generate_answers(model_name, prompt, use_ollama):
    """
    Generate answers using the Ollama model or return the prompt as is.
    
    Args:
        model_name (str): The name of the Ollama model.
        prompt (str): The prompt to generate answers for.
        use_ollama (bool): Flag indicating whether to use Ollama for analysis.
    
    Returns:
        str: The generated detailed description or the original prompt.
    """
    if not use_ollama:
        return prompt
    
    full_prompt = f"describe the following actions for this markdown documentation in short terms and with context: {prompt}"
    model_name = "vicuna:13b-16k"
    messages = [{'role': 'user', 'content': full_prompt}]
    try:
        response = ollama.chat(model=model_name, messages=messages)
        return response['message']['content']
    except Exception as e:
        print(f"There was an error communicating with the Ollama model: {e}")
        return None

def get_active_window_title():
    """
    Get the title of the active window.
    
    Returns:
        str: The title of the active window.
    """
    if platform.system() == "Linux":
        try:
            # Get the window ID of the currently focused window
            window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()

            # Get the name of the window with this ID
            window_name = subprocess.check_output(["xdotool", "getwindowname", window_id]).decode().strip()

            return window_name
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving window title: {e}")
            return None
    elif platform.system() == "Windows":
        window = gw.getActiveWindow()
        return window.title if window else "No active window"

class ActivityMonitor(ctk.CTk):
    """
    Class representing an Activity Monitor application.
    """
    def __init__(self, use_ollama=False):
        """
        Initialize the ActivityMonitor object.
        
        Args:
            use_ollama (bool): Flag indicating whether to use Ollama for analysis.
        """
        super().__init__()
        self.title("Activity Monitor")
        self.geometry("300x150")
        self.use_ollama = use_ollama
        self.is_running = False
        self.markdown_log = ""

        # Create GUI elements
        self.start_button = ctk.CTkButton(self, text="Start", command=self.start_monitoring)
        self.start_button.pack(pady=10)
        self.stop_button = ctk.CTkButton(self, text="Stop", command=self.stop_monitoring)
        self.stop_button.pack(pady=10)
        self.ollama_button = ctk.CTkButton(self, text="Analyze with Ollama", command=self.analyze_with_ollama)
        self.ollama_button.pack(pady=10)
        self.quit_button = ctk.CTkButton(self, text="Quit", command=self.quit_monitoring)
        self.quit_button.pack(pady=10)

    # Method to start monitoring activities
    def start_monitoring(self):
        """
        Start monitoring activities.
        """
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self.monitor_activities).start()

    # Method to stop monitoring activities
    def stop_monitoring(self):
        """
        Stop monitoring activities.
        """
        self.is_running = False

    # Method to analyze activities using Ollama
    def analyze_with_ollama(self):
        """
        Analyze activities using Ollama.
        """
        detailed_description = generate_answers("vicuna:13b-16k", self.markdown_log, True)
        if detailed_description:
            self.markdown_log = detailed_description
            self.write_markdown_file()

    # Method to quit monitoring and write the log to a file
    def quit_monitoring(self):
        """
        Quit monitoring activities and write the log to a file.
        """
        self.stop_monitoring()
        self.write_markdown_file()
        self.destroy()

    # Method to continuously monitor activities
    def monitor_activities(self):
        """
        Continuously monitor activities.
        """
        screenshot_directory = "screenshots"
        archive_directory = "archives"
        os.makedirs(screenshot_directory, exist_ok=True)
        os.makedirs(archive_directory, exist_ok=True)
        window_title = None
        previous_window = None
        while self.is_running:
            current_clipboard = clipboard.paste()
            self.append_to_markdown(f"\n- **Clipboard Changed**: `{current_clipboard}`")
            window_title = get_active_window_title()
            self.append_to_markdown(f"\n- **Window Selected**: {window_title}")
            if previous_window != window_title:
                self.capture_screenshot(screenshot_directory)
            previous_window = window_title
            # Capture typed keys
            key_events = keyboard.record(until='enter')
            typed_text = ''.join([event.name for event in key_events if event.event_type == 'down' and len(event.name) == 1 or event.name == 'space'])
            if typed_text:
                self.markdown_log += f"\n- **Typed Text**: {typed_text.replace('space', ' ')}"
                self.text_buffer = ""

            time.sleep(1)  # Reduce CPU usage

    # Method to capture screenshots
    def capture_screenshot(self, directory):
        """
        Capture screenshots.
        
        Args:
            directory (str): The directory to save the screenshots.
        
        Returns:
            str: The path of the captured screenshot.
        """
        if platform.system() == "Linux":
            try:
                # Get the window ID of the currently focused window
                window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()

                # Get the geometry of the window (position and size)
                geom_output = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", window_id]).decode()

                # Use a dictionary to store variables from the shell output
                geom_vars = dict(re.findall(r'(\w+)=(\S+)', geom_output))

                # Convert values to integers
                x = int(geom_vars['X'])
                y = int(geom_vars['Y'])
                width = int(geom_vars['WIDTH'])
                height = int(geom_vars['HEIGHT'])

                with mss.mss() as sct:
                    # The screenshot region is a tuple: (x, y, width, height)
                    monitor = {"top": y, "left": x, "width": width, "height": height}
                    screenshot_path = os.path.join(directory, f"{time.time()}_screenshot.png")
                    # Capture the specified region
                    sct_img = sct.grab(monitor)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)
                    return screenshot_path
            except Exception as e:
                print(f"Error capturing screenshot: {e}")
                return "Screenshot capture failed"

        elif platform.system() == "Windows":
            window = gw.getActiveWindow()
            if window:
                screenshot_path = os.path.join(directory, f"{time.time()}_screenshot.png")
                screenshot = ImageGrab.grab(bbox=window.box)
                screenshot.save(screenshot_path)
                return screenshot_path

        return "No active window for screenshot"

    # Method to archive URLs
    def archive_url(self, directory):
        """
        Archive URLs.
        
        Args:
            directory (str): The directory to save the archived URLs.
        """
        window_title = get_active_window_title()
        # Extend or adjust the list of browser window titles as needed
        browsers = ["Brave", "Firefox", "Chrome", "Chromium", "Edge", "Opera"]
        if any(browser in window_title for browser in browsers):
            # Set focus to the address bar and copy URL
            keyboard.send('ctrl+l')  # Focus on address bar
            time.sleep(0.1)  # Briefly wait for focus to be set
            keyboard.send('ctrl+c')  # Copy URL
            time.sleep(0.1)  # Wait for clipboard to update
            keyboard.send('esc')  # Escape

            # Read URL from clipboard
            url = clipboard.paste()
            if url.startswith("http") or url.startswith("https"):
                with open(os.path.join(self.directory, f"{time.time()}_url.txt"), "w", encoding='utf-8') as file:
                    file.write(url)
        else:
            print("The active window is not a recognized browser window.")

    # Method to append content to the markdown log
    def append_to_markdown(self, content):
        """
        Append content to the markdown log.
        
        Args:
            content (str): The content to append.
        """
        if content not in self.markdown_log:
            self.markdown_log += content

    # Method to write the markdown log to a file
    def write_markdown_file(self):
        """
        Write the markdown log to a file.
        """
        with open("activity_log.md", "w", encoding='utf-8') as md_file:
            md_file.write(markdown2.markdown(self.markdown_log))

if __name__ == "__main__":
    app = ActivityMonitor(use_ollama=False)
    app.mainloop()
