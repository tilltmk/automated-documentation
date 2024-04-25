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

if platform.system() == "Linux":
    import mss
    import mss.tools
elif platform.system() == "Windows":
    import pyscreenshot as ImageGrab
    import pygetwindow as gw

def generate_answers(model_name, prompt, use_ollama):
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
    if platform.system() == "Linux":
        try:
            # Erhalte die Window ID des aktuell fokussierten Fensters
            window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()

            # Erhalte den Namen des Fensters mit dieser ID
            window_name = subprocess.check_output(["xdotool", "getwindowname", window_id]).decode().strip()

            return window_name
        except subprocess.CalledProcessError as e:
            print(f"Fehler beim Abrufen des Fenstertitels: {e}")
            return None
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
            # Capture typed keys (improved version)
            key_events = keyboard.record(until='enter')
            typed_text = ''.join([event.name for event in key_events if event.event_type == 'down' and len(event.name) == 1 or event.name == 'space'])
            if typed_text:
                self.markdown_log += f"\n- **Typed Text**: {typed_text.replace('space', ' ')}"
                self.text_buffer = ""

            time.sleep(1)  # Reduce CPU usage

    def capture_screenshot(self, directory):
        if platform.system() == "Linux":
            try:
                # Erhalte die Window ID des aktuell fokussierten Fensters
                window_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode().strip()

                # Erhalte die Geometrie des Fensters (Position und Größe)
                geom_output = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", window_id]).decode()

                # Verwende ein Wörterbuch, um die Variablen aus der Shell-Ausgabe zu speichern
                geom_vars = dict(re.findall(r'(\w+)=(\S+)', geom_output))

                # Wandelt die Werte in Integer um
                x = int(geom_vars['X'])
                y = int(geom_vars['Y'])
                width = int(geom_vars['WIDTH'])
                height = int(geom_vars['HEIGHT'])

                with mss.mss() as sct:
                    # Der Screenshot-Bereich ist ein Tupel: (x, y, width, height)
                    monitor = {"top": y, "left": x, "width": width, "height": height}
                    screenshot_path = os.path.join(directory, f"{time.time()}_screenshot.png")
                    # Erfasse den spezifizierten Bereich
                    sct_img = sct.grab(monitor)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)
                    return screenshot_path
            except Exception as e:
                print(f"Fehler beim Erfassen des Screenshots: {e}")
                return "Screenshot capture failed"

        elif platform.system() == "Windows":
            window = gw.getActiveWindow()
            if window:
                screenshot_path = os.path.join(directory, f"{time.time()}_screenshot.png")
                screenshot = ImageGrab.grab(bbox=window.box)
                screenshot.save(screenshot_path)
                return screenshot_path

        return "No active window for screenshot"

    def archive_url(self, directory):
        window_title = get_active_window_title()
        # Liste der Browserfenstertitel erweitern oder anpassen
        browsers = ["Brave", "Firefox", "Chrome", "Chromium", "Edge", "Opera"]
        if any(browser in window_title for browser in browsers):
            # Fokus auf die Adressleiste setzen und URL kopieren
            keyboard.send('ctrl+l')  # Fokus auf Adressleiste
            time.sleep(0.1)  # Kurz warten, damit der Fokus sicher gesetzt ist
            keyboard.send('ctrl+c')  # Kopieren der URL
            time.sleep(0.1)  # Warten, damit die Zwischenablage aktualisiert wird
            keyboard.send('esc')  # Escapen

            # URL aus der Zwischenablage lesen
            url = clipboard.paste()
            if url.startswith("http") or url.startswith("https"):
                with open(os.path.join(self.directory, f"{time.time()}_url.txt"), "w", encoding='utf-8') as file:
                    file.write(url)
        else:
            print("Das aktive Fenster ist kein erkanntes Browserfenster.")

    def append_to_markdown(self, content):
        if content not in self.markdown_log:
            self.markdown_log += content

    def write_markdown_file(self):
        with open("activity_log.md", "w", encoding='utf-8') as md_file:
            md_file.write(markdown2.markdown(self.markdown_log))

if __name__ == "__main__":
    app = ActivityMonitor(use_ollama=False)
    app.mainloop()
