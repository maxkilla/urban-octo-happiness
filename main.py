import logging
import tkinter as tk
from gui import MyrientScraperGUI

if __name__ == "__main__":
    logging.basicConfig(filename='myrient_downloader.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    root = tk.Tk()
    app = MyrientScraperGUI(root)
    root.mainloop() 