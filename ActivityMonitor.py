import time
import os
import platform
import subprocess
import threading
import customtkinter as ctk
import keyboard
import clipboard
import re
import ollama

if platform.system() == "Linux":
    import mss
    import mss.tools
elif platform.system() == "Windows":
    import pyscreenshot as ImageGrab
    import pygetwindow as gw

screenshot_directory = "screenshots"
archive_directory = "archives"

def generate_answers(model_name, prompt):
    messages = [{'role': 'user', 'content': prompt}]
    try:
        response = ollama.chat(model=model_name, messages=messages)
        return response['message']['content']
    except Exception as e:
        print(f"Error communicating with the Ollama model: {e}")
        return None
    
def get_active_window_title():
    """
    Get the title of the active window.
    
    Returns:
        str: The title of the active window.
    """
    if platform.system() == "Linux":
        return get_linux_active_window()
    elif platform.system() == "Windows":
        return get_windows_active_window()
    return None

def get_linux_active_window():
    """
    Get the active window title on Linux.
    
    Returns:
        str: The title of the active window.
    """
    try:
        window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()
        window_name = subprocess.check_output(["xdotool", "getwindowname", window_id]).decode().strip()
        geom_output = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", window_id]).decode()
        geom_vars = dict(re.findall(r'(\w+)=(\S+)', geom_output))
        x, y = int(geom_vars['X']), int(geom_vars['Y'])
        width, height = int(geom_vars['WIDTH']), int(geom_vars['HEIGHT'])

        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            screenshot_path = os.path.join(screenshot_directory, f"{time.time()}_screenshot.png")
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)

        return window_name
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving window title: {e}")
        return None

def get_windows_active_window():
    """
    Get the active window title on Windows.
    
    Returns:
        str: The title of the active window.
    """
    active_window = gw.getActiveWindow()
    if active_window:
        try:
            screenshot_path = os.path.join(screenshot_directory, f"{time.time()}_screenshot.png")
            screenshot = ImageGrab.grab(bbox=active_window.box)
            screenshot.save(screenshot_path)
            return active_window.title if active_window.title else "Unknown Window"
        except Exception as e:
            print(f"Error getting active window: {e}")
            return None
    return None

class ActivityMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.title("Activity Monitor")
        self.geometry("400x400")
        self.is_running = False
        self.text_buffer = ""
        self.markdown_log = ""

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.button_frame = ctk.CTkFrame(self, corner_radius=10)
        self.button_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.model_entry = ctk.CTkEntry(self.button_frame, placeholder_text="Enter Ollama model name")
        self.model_entry.pack(pady=(20, 10), padx=20, fill="x")

        self.start_button = ctk.CTkButton(self.button_frame, text="Start", command=self.start_monitoring, width=120, height=40, font=("Arial", 14))
        self.start_button.pack(pady=10, padx=20)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop", command=self.stop_monitoring, width=120, height=40, font=("Arial", 14))
        self.stop_button.pack(pady=10, padx=20)

        self.ollama_button = ctk.CTkButton(self.button_frame, text="Analyze with Ollama", command=self.analyze_with_ollama, width=120, height=40, font=("Arial", 14))
        self.ollama_button.pack(pady=10, padx=20)

        self.quit_button = ctk.CTkButton(self.button_frame, text="Quit", command=self.quit_monitoring, width=120, height=40, font=("Arial", 14))
        self.quit_button.pack(pady=(10, 20), padx=20)

        self.status_label = ctk.CTkLabel(self, text="Status: Not Running", font=("Arial", 16))
        self.status_label.pack(pady=(10, 20))

    def start_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.status_label.configure(text="Status: Running")
            threading.Thread(target=self.monitor_activities).start()

    def stop_monitoring(self):
        self.is_running = False
        self.status_label.configure(text="Status: Stopped")

    def analyze_with_ollama(self):
        prompt: str = f"Please analyze the following activities and add your comments:\n\n{self.markdown_log}"
        model_name = self.model_entry.get()
        if not model_name:
            model_name = "vicuna:13b-16k"  # Default model name if not provided
        self.status_label.configure(text="Status: Analyzing with Ollama.. Please wait.")
        detailed_description = generate_answers(model_name=model_name, prompt=prompt)
        if detailed_description:
            self.markdown_log += f"\n\n## Ollama's Analysis\n\n{detailed_description}"
            self.write_markdown_file()
        self.status_label.configure(text="Status: Analysis Complete")

    def quit_monitoring(self):
        self.stop_monitoring()
        self.write_markdown_file()
        self.destroy()

    def monitor_activities(self):
        previous_clipboard = ""
        previous_window = None
        os.makedirs(screenshot_directory, exist_ok=True)
        os.makedirs(archive_directory, exist_ok=True)
        window_title = None

        while self.is_running:
            # Capture clipboard content
            current_clipboard = clipboard.paste()
            if current_clipboard != previous_clipboard:
                self.markdown_log += f"\n- **Clipboard Changed**:\n```\n{current_clipboard}\n```\n"
                previous_clipboard = current_clipboard

            # Capture active window and screenshot
            window_title = get_active_window_title()
            if previous_window != window_title:
                screenshot_counter = 0
                while screenshot_counter < 4:
                    self.markdown_log += f"\n## Window Selected: {window_title}\n\n![Screenshot]({screenshot_directory}/{time.time()}_screenshot.png)\n"
                    time.sleep(5)
                    screenshot_counter += 1
                previous_window = window_title

            # Capture typed keys (improved version)
            key_events = keyboard.record(until='enter')
            typed_text = ''.join([event.name for event in key_events if event.event_type == 'down' and len(event.name) == 1 or event.name == 'space'])
            if typed_text:
                self.markdown_log += f"\n- **Typed Text**: {typed_text.replace('space', ' ')}\n"
                self.text_buffer = ""
            elif any(event.name in ['ctrl', 'alt', 'shift'] for event in key_events):
                self.markdown_log += f"\n- **Typed Text**: {self.text_buffer}\n"
                self.text_buffer = ""

            # Archive URLs
            self.archive_url(archive_directory)

            time.sleep(1)  # Reduce CPU usage

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
                with open(os.path.join(directory, f"{time.time()}_url.txt"), "w", encoding='utf-8') as file:
                    file.write(url)
        else:
            print("The active window is not a recognized browser window.")

    def write_markdown_file(self):
        with open("activity_log.md", "w", encoding='utf-8') as md_file:
            md_file.write(self.markdown_log)

if __name__ == "__main__":
    app = ActivityMonitor()
    app.mainloop()
