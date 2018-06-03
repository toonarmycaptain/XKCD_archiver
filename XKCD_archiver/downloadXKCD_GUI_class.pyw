#!.downloadXKCD_envScriptspythonw.exe
# downloadXKCD_GUI_class.pyw - classed GUI
"""
downloadXKCD_GUI_class - classed GUI


Created on Sun Mar 25 122442 2018
@author David Antonini  toonarmycaptain
"""

__version__ = '0.1.0+GUI_class'

import tkinter as tk


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'XKCD archiver v{__version__}')
        self.geometry('400x400')
        self.main_frame = tk.Frame(self)
        self.descr = tk.Label(self.main_frame,
                         text='This script searches xkcd.com '
                              'and downloads each comic.')

        self.descr.pack()
        self.main_frame.pack()



if __name__ == "__main__":
    app = Application()
    app.mainloop()


