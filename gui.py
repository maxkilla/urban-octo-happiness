import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor
import logging
from scraper import get_systems, fetch_games, BASE_URLS
# from theming import apply_theme  # For future dark mode
# from boxart import fetch_box_art  # For future box art
import urllib.parse
import re
import os

ITEMS_PER_PAGE = 50
ROMS_BASE_DIR = "/home/ROMs"
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
        self.games = []
        self.filtered_games = []
        self.page = 0
        self.sort_order = "asc"
        self.system_to_folder = {}
        self.systems = []
        self.create_widgets()
        self.update_collections()

    def create_widgets(self):
        logging.info("create_widgets called")
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_label = ttk.Label(main_frame, text="Myrient Downloader", font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=7, pady=(0, 10))
        # Source dropdown
        ttk.Label(main_frame, text="Source:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.source_var = tk.StringVar()
        self.source_combo = ttk.Combobox(main_frame, textvariable=self.source_var, state="readonly")
        self.source_combo['values'] = list(BASE_URLS.keys())
        self.source_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 15))
        self.source_combo.bind("<<ComboboxSelected>>", self.update_collections)
        self.source_var.set("Myrient")
        # Collection dropdown
        ttk.Label(main_frame, text="Collection:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        self.collection_var = tk.StringVar()
        self.collection_combo = ttk.Combobox(main_frame, textvariable=self.collection_var, state="readonly")
        self.collection_combo.grid(row=1, column=3, sticky=tk.W, padx=(0, 15))
        self.collection_combo.bind("<<ComboboxSelected>>", self.update_systems)
        # System dropdown
        ttk.Label(main_frame, text="System:").grid(row=1, column=4, sticky=tk.W, padx=(0, 5))
        self.system_var = tk.StringVar()
        self.system_combo = ttk.Combobox(main_frame, textvariable=self.system_var, state="readonly")
        self.system_combo.grid(row=1, column=5, sticky=tk.W, padx=(0, 15))
        self.system_combo.bind("<<ComboboxSelected>>", self.on_system_selected)
        # Region dropdown
        ttk.Label(main_frame, text="Region:").grid(row=1, column=6, sticky=tk.W, padx=(0, 5))
        self.region_var = tk.StringVar()
        self.region_combo = ttk.Combobox(main_frame, textvariable=self.region_var, state="readonly")
        self.region_combo['values'] = ["USA", "JAP", "EUR", "Other"]
        self.region_combo.grid(row=1, column=7, sticky=tk.W)
        self.region_combo.bind("<<ComboboxSelected>>", self.filter_data)
        # Search/filter entry
        ttk.Label(main_frame, text="Search:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(main_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        self.search_entry.bind("<Return>", self.filter_data)
        columns = ("Name", "Size", "Region", "Year")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150 if col == "Name" else 80, anchor=tk.W)
        self.tree.grid(row=3, column=0, columnspan=8, sticky="nsew", pady=(10, 0))
        self.tree.bind("<Double-1>", self.download_file)
        tree_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=tree_scroll.set)
        tree_scroll.grid(row=3, column=8, sticky="ns", pady=(10, 0))
        self.prev_button = ttk.Button(main_frame, text="Previous", command=self.prev_page)
        self.prev_button.grid(row=4, column=0, pady=(10, 0), sticky=tk.W)
        self.next_button = ttk.Button(main_frame, text="Next", command=self.next_page)
        self.next_button.grid(row=4, column=1, pady=(10, 0), sticky=tk.W)
        self.page_label = ttk.Label(main_frame, text="Page 1")
        self.page_label.grid(row=4, column=2, pady=(10, 0), sticky=tk.W)
        self.download_button = ttk.Button(main_frame, text="Download Selected", command=self.download_selected)
        self.download_button.grid(row=4, column=7, pady=(10, 0), sticky=tk.E)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, columnspan=8, sticky="ew", pady=(10, 0))
        self.status_label = ttk.Label(main_frame, text="Ready", anchor="w")
        self.status_label.grid(row=6, column=0, columnspan=8, sticky="ew", pady=(5, 0))
        for i in range(8):
            main_frame.columnconfigure(i, weight=1)
        main_frame.rowconfigure(3, weight=1)

    def update_collections(self, event=None):
        source = self.source_var.get()
        collections = list(BASE_URLS[source].keys())
        self.collection_combo['values'] = collections
        if collections:
            self.collection_var.set(collections[0])
        else:
            self.collection_var.set("")
        self.update_systems()

    def update_systems(self, event=None):
        logging.info("update_systems called")
        source = self.source_var.get()
        collection = self.collection_var.get()
        systems_encoded = get_systems(source, collection)
        self.system_display_to_encoded = {}
        systems_display = []
        for encoded in systems_encoded:
            display = urllib.parse.unquote(encoded)
            self.system_display_to_encoded[display] = encoded
            systems_display.append(display)
        self.system_combo['values'] = systems_display
        if systems_display:
            self.system_var.set(systems_display[0])
        else:
            self.system_var.set("")
        self.fetch_data()

    def on_system_selected(self, event=None):
        logging.info(f"on_system_selected called: {self.system_var.get()}")
        self.fetch_data()

    def fetch_data(self):
        source = self.source_var.get()
        collection = self.collection_var.get()
        system_display = self.system_var.get()
        system = self.system_display_to_encoded.get(system_display, system_display)
        logging.info(f"fetch_data called for source: {source}, collection: {collection}, system: {system}")
        if not collection or not system:
            self.games = []
            self.filter_data()
            return
        games = fetch_games(source, collection, system, system_display)
        self.games = games
        self.filter_data()

    def filter_data(self, event=None):
        logging.info("filter_data called")
        system = self.system_var.get()
        region = self.region_var.get()
        search = self.search_var.get().lower()
        filtered = self.games
        if system:
            filtered = [g for g in filtered if g["system"] == system]
        if region:
            filtered = [g for g in filtered if g["region"] == region]
        if search:
            filtered = [g for g in filtered if search in g["name"].lower()]
        self.filtered_games = filtered
        self.page = 0
        self.display_page()

    def display_page(self):
        logging.info("display_page called")
        for row in self.tree.get_children():
            self.tree.delete(row)
        start = self.page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        for game in self.filtered_games[start:end]:
            self.tree.insert("", tk.END, values=(game.get("name", "Sample Game"), game.get("size", "10MB"), game.get("region", "USA"), game.get("year", "1990")))
        total_pages = max(1, (len(self.filtered_games) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self.page_label.config(text=f"Page {self.page + 1} of {total_pages}")

    def download_file(self, event):
        logging.info("download_file called")
        selected = self.tree.focus()
        if selected:
            item = self.tree.item(selected)
            game_name = item["values"][0]
            messagebox.showinfo("Download", f"Would download: {game_name}")

    def download_selected(self):
        logging.info("download_selected called")
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No selection", "Please select at least one game.")
            return
        for item in selected_items:
            game_name = self.tree.item(item)["values"][0]
            messagebox.showinfo("Download", f"Would download: {game_name}")

    def start_download(self, game):
        self.download_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_label.config(text=f"Starting download: {game['name']}")
        with ThreadPoolExecutor() as executor:
            executor.submit(self.download_game, game)

    def reset_ui(self):
        self.progress_var.set(0)
        self.status_label.config(text="Ready")
        self.download_button.config(state=tk.NORMAL)

    def next_page(self):
        logging.info("next_page called")
        if (self.page + 1) * ITEMS_PER_PAGE < len(self.filtered_games):
            self.page += 1
            self.display_page()

    def prev_page(self):
        logging.info("prev_page called")
        if self.page > 0:
            self.page -= 1
            self.display_page() 