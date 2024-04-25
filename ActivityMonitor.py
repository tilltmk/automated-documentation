import customtkinter as ctk
import keyboard
import clipboard
import time
import markdown2
import threading
import os
import ollama
import pyautogui
import platform
import sys

if platform.system() == "Linux":
    import mss
    import Xlib
    import Xlib.display
elif platform.system() == "Windows":
    import pyscreenshot as ImageGrab
    import pygetwindow as gw

def generate_answers(model_name, prompt, use_ollama):
    if not use_ollama:
        return prompt
    
    model_name = "vicuna:13b-16k"
    messages = [{'role': 'user', 'content': prompt}]
    try:
        response = ollama.chat(model=model_name, messages=messages)
        return response['message']['content']
    except Exception as e:
        print(f"There was an error communicating with the Ollama model: {e}")
        return None

def get_active_window_title():
    if platform.system() == "Linux":
        display = Xlib.display.Display()
        root = display.screen().root
        window_id = root.get_full_property(display.intern_atom('_NET_ACTIVE_WINDOW'), Xlib.X.AnyPropertyType).value[0]
        window = display.create_resource_object('window', window_id)
        return window.get_wm_name()
    elif platform.system() == "Windows":
        window = gw.getActiveWindow()
        return window.title if window else "No active window"

class ActivityMonitor(ctk.CTk):
    def __init__(self, use_ollama=False):
        super().__init__()
        self.title("Activity Monitor")
        self.geometry("300x150")
        self.use_ollama = use_ollama
        self.is_running = False
        self.markdown_log = ""

        self.start_button = ctk.CTkButton(self, text="Start", command=self.start_monitoring)
        self.start_button.pack(pady=10)
        self.stop_button = ctk.CTkButton(self, text="Stop", command=self.stop_monitoring)
        self.stop_button.pack(pady=10)
        self.ollama_button = ctk.CTkButton(self, text="Analyze with Ollama", command=self.analyze_with_ollama)
        self.ollama_button.pack(pady=10)
        self.quit_button = ctk.CTkButton(self, text="Quit", command=self.quit_monitoring)
        self.quit_button.pack(pady=10)

    def start_monitoring(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self.monitor_activities).start()

    def stop_monitoring(self):
        self.is_running = False

    def analyze_with_ollama(self):
        detailed_description = generate_answers("vicuna:13b-16k", self.markdown_log, self.use_ollama)
        if detailed_description:
            self.markdown_log = detailed_description
            self.write_markdown_file()

    def quit_monitoring(self):
        self.stop_monitoring()
        self.write_markdown_file()
        self.destroy()

    def monitor_activities(self):
        screenshot_directory = "screenshots"
        archive_directory = "archives"
        os.makedirs(screenshot_directory, exist_ok=True)
        os.makedirs(archive_directory, exist_ok=True)

        while self.is_running:
            current_clipboard = clipboard.paste()
            self.append_to_markdown(f"\n- **Clipboard Changed**: `{current_clipboard}`")
            window_title = get_active_window_title()
            self.append_to_markdown(f"\n- **Window Selected**: {window_title}")
            screenshot_path = self.capture_screenshot(screenshot_directory)
            url = self.capture_url()
            self.archive_url(url, archive_directory)
            time.sleep(1)

    def capture_screenshot(self, directory):
        if platform.system() == "Linux":
            with mss.mss() as sct:
                screenshot_path = os.path.join(directory, f"{time.time()}_screenshot.png")
                sct.shot(output=screenshot_path)
                return screenshot_path
        elif platform.system() == "Windows":
            window = gw.getActiveWindow()
            if window:
                screenshot_path = os.path.join(directory, f"{time.time()}_screenshot.png")
                screenshot = ImageGrab.grab(bbox=window.box)
                screenshot.save(screenshot_path)
                return screenshot_path
        return "No active window for screenshot"

    def capture_url(self):
        try:
            pyautogui.moveTo(100, 100)  # Move to likely position of address bar
            pyautogui.click()
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)  # Wait for clipboard to update
            url = clipboard.paste()
            return url
        except Exception as e:
            print(f"Error capturing URL: {e}")
            return "Error"

    def archive_url(self, url, directory):
        if url.startswith("http"):
            with open(os.path.join(directory, f"{time.time()}_url.txt"), "w") as file:
                file.write(url)

    def append_to_markdown(self, content):
        if content not in self.markdown_log:
            self.markdown_log += content

    def write_markdown_file(self):
        with open("activity_log.md", "w", encoding='utf-8') as md_file:
            md_file.write(markdown2.markdown(self.markdown_log))

if __name__ == "__main__":
    app = ActivityMonitor(use_ollama=True)
    app.mainloop()
