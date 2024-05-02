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
        self.geometry("400x300")

        self.is_running = False
        self.text_buffer = ""
        self.markdown_log = ""

        # Set theme and color scheme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Create a frame for the buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=20)

        # Create buttons with icons
        self.start_button = ctk.CTkButton(self.button_frame, text="Start", command=self.start_monitoring, width=120, height=40, font=("Arial", 14))
        self.start_button.pack(pady=10)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop", command=self.stop_monitoring, width=120, height=40, font=("Arial", 14))
        self.stop_button.pack(pady=10)

        self.ollama_button = ctk.CTkButton(self.button_frame, text="Analyze with Ollama", command=self.analyze_with_ollama, width=120, height=40, font=("Arial", 14))
        self.ollama_button.pack(pady=10)

        self.quit_button = ctk.CTkButton(self.button_frame, text="Quit", command=self.quit_monitoring, width=120, height=40, font=("Arial", 14))
        self.quit_button.pack(pady=10)

        # Create a label to display the current status
        self.status_label = ctk.CTkLabel(self, text="Status: Not Running", font=("Arial", 16))
        self.status_label.pack(pady=10)

    def start_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.status_label.configure(text="Status: Running")
            threading.Thread(target=self.monitor_activities).start()

    def stop_monitoring(self):
        self.is_running = False
        self.status_label.configure(text="Status: Stopped")

    def analyze_with_ollama(self):
        prompt = f"Please analyze the following activities and add your comments:\n\n{self.markdown_log}"
        detailed_description = generate_answers("vicuna:13b-16k", prompt)
        if detailed_description:
            self.markdown_log += f"\n\n## Ollama's Analysis\n\n{detailed_description}"
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
                self.markdown_log += f"\n- **Clipboard Changed**:\n```\n{current_clipboard}\n```\n"
                previous_clipboard = current_clipboard

            # Capture active window and screenshot
            active_window = gw.getActiveWindow()
            if active_window and (active_window != previous_window):
                try:
                    # save screenshot
                    screenshot_path = os.path.join(screenshot_directory, f"{time.time()}_screenshot.png")
                    screenshot = ImageGrab.grab(bbox=active_window.box)
                    screenshot.save(screenshot_path)

                    # save title and screenshot in markdown log
                    window_title = active_window.title if active_window.title else "Unknown Window"
                    self.markdown_log += f"\n## Window Selected: {window_title}\n\n![Screenshot]({screenshot_path})\n"
                    previous_window = active_window
                except Exception as e:
                    print(f"Error getting active window: {e}")

            # Capture typed keys (improved version)
            key_events = keyboard.record(until='enter')
            typed_text = ''.join([event.name for event in key_events if event.event_type == 'down' and len(event.name) == 1 or event.name == 'space'])
            if typed_text:
                self.markdown_log += f"\n- **Typed Text**: {typed_text.replace('space', ' ')}\n"
                self.text_buffer = ""

            time.sleep(1)  # Reduce CPU usage

    def write_markdown_file(self):
        with open("activity_log.md", "w", encoding='utf-8') as md_file:
            md_file.write(self.markdown_log)

if __name__ == "__main__":
    app = ActivityMonitor()
    app.mainloop()
