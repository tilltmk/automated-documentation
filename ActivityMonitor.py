import customtkinter as ctk
import keyboard
import clipboard
import pygetwindow as gw
import pyscreenshot as ImageGrab
import time
import markdown2
import threading
import os
import ollama

def generate_answers(model_name, prompt):
    model_name = "vicuna:13b-16k"
    messages = [
        {
            'role': 'user',
            'content': prompt,
        },
    ]
    try:
        response = ollama.chat(model=model_name, messages=messages)
        return response['message']['content']
    except Exception as e:
        print(f"There was an error communicating with the Ollama model: {e}")
        return None

class ActivityMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Activity Monitor")
        self.geometry("300x150")

        self.is_running = False
        self.text_buffer = ""
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
        # Hier nehmen Sie an, dass `self.markdown_log` Ihre gesammelten Daten enthält
        detailed_description = generate_answers("vicuna:13b-16k", self.markdown_log)
        if detailed_description:
            self.markdown_log = detailed_description
            self.write_markdown_file()

    def quit_monitoring(self):
        self.stop_monitoring()
        self.write_markdown_file()
        self.destroy()

    def monitor_activities(self):
        previous_clipboard = ""
        previous_window = None
        screenshot_directory = "screenshots"
        os.makedirs(screenshot_directory, exist_ok=True)

        while self.is_running:
            # Capture clipboard content
            current_clipboard = clipboard.paste()
            if current_clipboard != previous_clipboard:
                self.markdown_log += f"\n- **Clipboard Changed**: `{current_clipboard}`"
                previous_clipboard = current_clipboard

            # Capture active window and screenshot
            active_window = gw.getActiveWindow()
            if active_window and (active_window != previous_window):
                try:
                    # Screenshot aufnehmen und speichern
                    screenshot_path = os.path.join(screenshot_directory, f"{time.time()}_screenshot.png")
                    screenshot = ImageGrab.grab(bbox=active_window.box)
                    screenshot.save(screenshot_path)

                    # Titel und Screenshot im Markdown-Log speichern
                    window_title = active_window.title if active_window.title else "Unbekanntes Fenster"
                    self.markdown_log += f"\n- **Window Selected**: {window_title} ![Screenshot]({screenshot_path})"
                    previous_window = active_window
                except Exception as e:
                    print(f"Error getting active window: {e}")

            # Capture typed keys (improved version)
            key_events = keyboard.record(until='enter')
            typed_text = ''.join([event.name for event in key_events if event.event_type == 'down' and len(event.name) == 1 or event.name == 'space'])
            if typed_text:
                self.markdown_log += f"\n- **Typed Text**: {typed_text.replace('space', ' ')}"
                self.text_buffer = ""

            time.sleep(1)  # Reduce CPU usage

    def write_markdown_file(self):
        with open("activity_log.md", "w", encoding='utf-8') as md_file:
            md_file.write(self.markdown_log)

if __name__ == "__main__":
    app = ActivityMonitor()
    app.mainloop()
