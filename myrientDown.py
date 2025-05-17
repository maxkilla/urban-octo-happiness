import os
import re
import socket
import time
import urllib.parse
import logging
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tqdm import tqdm

# Set up logging
logging.basicConfig(filename='myrient_downloader.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
BASE_URLS = {
    "No-Intro": "https://myrient.erista.me/files/No-Intro/ ",
    "Redump": "https://myrient.erista.me/files/Redump/ ",
    "Internet Archive": "https://myrient.erista.me/files/Internet  Archive/",
    "Miscellaneous": "https://myrient.erista.me/files/Miscellaneous/ ",
    "TOSEC": "https://myrient.erista.me/files/TOSEC/ ",
    "TOSEC-ISO": "https://myrient.erista.me/files/TOSEC-ISO/ ",
    "TOSEC-PIX": "https://myrient.erista.me/files/TOSEC-PIX/ "
}
ITEMS_PER_PAGE = 50
ROMS_BASE_DIR = "/home/ROMs"

# Region-based folder mapping
REGION_FOLDERS = {
    "Nintendo - Super Nintendo Entertainment System": {"USA": "snesna"},
    "Sega - 32X": {"JAP": "sega32xjp", "USA": "sega32xna"},
    "Sega - Mega Drive - Genesis": {"JAP": "megadrivejp"},
    "Sega - Saturn": {"JAP": "saturnjp"},
    "Sega - Mega CD & Sega CD": {"JAP": "segacdjp"},
}

class MyrientScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Myrient Downloader")
        self.session = requests.Session()
        self.games = []
        self.filtered_games = []
        self.page = 0
        self.sort_order = "asc"
        self.system_to_folder = {
            # [your full system_to_folder dict here] – keep as-is
        }
        self.systems = []
        self.create_widgets()
        self.update_systems()

    def create_widgets(self):
        # [same as before, unchanged]
    
    def update_systems(self, event=None):
        # [same as before, but use self.session instead of requests.get]

    def get_systems(self, collection):
        # [use self.session here instead of requests.get]

    def fetch_data(self):
        # [use self.session, cache data if needed]

    def extract_region(self, name):
        # [unchanged]

    def filter_data(self):
        # [unchanged]

    def sort_data(self):
        # [unchanged]

    def display_page(self):
        # [unchanged]

    def download_file(self, event):
        selected = self.tree.focus()
        if selected:
            item = self.tree.item(selected)
            game_name = item["values"][0]
            game = next((g for g in self.filtered_games if g["name"] == game_name), None)
            if game:
                self.start_download(game)

    def download_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No selection", "Please select at least one game.")
            return
        for item in selected_items:
            game_name = self.tree.item(item)["values"][0]
            game = next((g for g in self.filtered_games if g["name"] == game_name), None)
            if game:
                self.start_download(game)

    def start_download(self, game):
        """Start download in a separate thread"""
        self.download_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_label.config(text=f"Starting download: {game['name']}")
        with ThreadPoolExecutor() as executor:
            executor.submit(self.download_game, game)

    def sanitize_filename(self, filename):
        """Remove illegal characters for filenames"""
        return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', filename)

    def determine_download_path(self, system, region, game_name):
        folder_name = None
        for sys_key, folder in self.system_to_folder.items():
            if system.startswith(sys_key.split(" (")[0]):
                folder_name = folder
                break

        if folder_name:
            # Check region-specific folders
            folder_name = REGION_FOLDERS.get(system, {}).get(region, folder_name)
            download_dir = os.path.join(ROMS_BASE_DIR, folder_name)
        else:
            messagebox.showwarning("Warning", f"No folder mapped for: {system}. Select location.")
            download_dir = filedialog.askdirectory(initialdir=ROMS_BASE_DIR)
            if not download_dir:
                return None
        os.makedirs(download_dir, exist_ok=True)
        return os.path.join(download_dir, self.sanitize_filename(game_name))

    def download_game(self, game):
        system = self.system_var.get()
        region = self.region_var.get()
        url = game["url"]
        game_name = game["name"]

        download_path = self.determine_download_path(system, region, game_name)
        if not download_path:
            self.reset_ui()
            return

        try:
            headers = {}
            downloaded_size = 0
            if os.path.exists(download_path):
                downloaded_size = os.path.getsize(download_path)
                headers = {"Range": f"bytes={downloaded_size}-"}

            response = self.session.get(url, stream=True, headers=headers, timeout=10)
            total_size = int(response.headers.get('content-length', 0)) + downloaded_size
            mode = 'ab' if downloaded_size else 'wb'

            start_time = time.time()
            with open(download_path, mode) as f:
                with tqdm(total=total_size, initial=downloaded_size, unit='B',
                          unit_scale=True, desc=game_name, leave=False) as pbar:

                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            pbar.update(len(chunk))
                            progress = (downloaded_size / total_size) * 100
                            elapsed = time.time() - start_time
                            speed = downloaded_size / elapsed if elapsed > 0 else 0
                            eta = (total_size - downloaded_size) / speed if speed > 0 else 0

                            self.root.after(0, self.update_progress, progress,
                                            f"Downloading {game_name} - {progress:.1f}% ({int(eta)}s remaining)")
            self.root.after(0, self.finish_download, game_name, download_path)
        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            self.root.after(0, messagebox.showerror, "Download Failed", str(e))
        finally:
            self.root.after(0, self.reset_ui)

    def update_progress(self, progress, status_text):
        self.progress_var.set(progress)
        self.status_label.config(text=status_text)

    def finish_download(self, game_name, path):
        self.status_label.config(text=f"Downloaded {game_name} to {path}")
        messagebox.showinfo("Success", f"{game_name} saved to {path}")

    def reset_ui(self):
        self.progress_var.set(0)
        self.status_label.config(text="Ready")
        self.download_button.config(state=tk.NORMAL)

    def next_page(self):
        if (self.page + 1) * ITEMS_PER_PAGE < len(self.filtered_games):
            self.page += 1
            self.display_page()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.display_page()


if __name__ == "__main__":
    root = tk.Tk()
    app = MyrientScraperGUI(root)
    root.mainloop()
