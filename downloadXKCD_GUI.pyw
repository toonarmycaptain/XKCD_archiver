#!./downloadXKCD_env/Scripts/pythonw.exe
# downloadXKCD GUI.py - run downloadXKCD inside a GUI
"""
downloadXKCD GUI - run downloadXKCD inside a GUI using Tkinter

1.1.1 changes:
    -config download_comics to take run_mode as an argument

1.2.1 changes:
    - added version number to main window title.
    - fixed/updated venv
    - added Quit button

1.2.2 changes:
    - refactored venv
    - refactored window/GUI setup, button/widget creation into
        separate functions to eliminate repitition
    - fixed documentation
    - added button ghosting/disable functionality


>>>make full_mode button disappear after run NB when adding option for
    archive locations, will need to rejig UI
>>>run download code in a separate thread, but don't allow multiple button
clicks to spawn multiple runs concurrently.

Created on Wed Feb 28 11:23:42 2018

@author: David Antonini // toonarmycaptain
"""

__version__ = '1.2.2+GUI'

import sys
import tkinter as tk

import downloadXKCD


def venv_test(frame):
    """
    Test if script is running in a virtualenv or system python, returning a
    label with test result.

    Args:
        frame (tkinter.Frame): frame label will be placed in.

    Returns: tkinter.Label
    """
    # Test if successfully running in virtualenv
    if downloadXKCD.is_venv():
        venv_text = 'This script is running in its own virtualenv.'
    else:
        venv_text = 'Script running outside virtualenv or venv.'

    venv = tk.Label(
        frame,
        text=venv_text)
    return venv


def mode_picked(mode):
    """
    Runs downloadXKCD download script in chosen mode.

    Args:
        mode (bool): True for full, False for quick/update

    Returns: None
    """
    downloadXKCD.download_comics(mode)


def run_quick_mode():
    """
    Runs downloadXKCD download logic in quick/update mode.
    Ghosts/disables while running to prevent multiple runs.

    Returns: None
    """

    for child in quick_mode_frame.winfo_children():
        child.configure(state='disable')
    main_window.update()

    downloadXKCD.download_comics(False)

    for child in quick_mode_frame.winfo_children():
        child.configure(state='active')


def run_full_mode():
    """
    Runs downloadXKCD download logic in full mode.
    Ghosts/disables button and label, to prevent multiple full runs.

    Returns: None
    """
    for child in full_mode_frame.winfo_children():
        child.configure(state='disable')

    main_window.update()
    downloadXKCD.download_comics(True)


def regular_exit():
    """
    Check whether exit status should be 0 or 1, (one is error), exits.
    """
    main_window.destroy()
    sys.exit(0)


def full_button(frame):
    """
    Creates a Full mode button, with explanatory label.

    Args:
        frame(tkinter.Frame)

    Returns: tkinter.Frame
    """
    full_mode_button = tk.Button(frame,
                                 text='Full mode',
                                 command=run_full_mode)
    full_mode_expl = tk.Label(frame,
                              text='Checks for every comic, '
                                   'downloads undownloaded comics.')
    full_mode_button.pack()
    full_mode_expl.pack()
    return frame


def quick_button(frame):
    """
    Creates a quick mode button, with explanatory label.

    Args:
        frame(tkinter.Frame)

    Returns: tkinter.Frame
    """
    quick_mode_button = tk.Button(frame,
                                  text='Quick mode',
                                  command=run_quick_mode)
    quick_mode_expl = tk.Label(frame,
                               text='Or "refresh mode", checked until it '
                                    'finds a previously downloaded comic.')
    quick_mode_button.pack()
    quick_mode_expl.pack()
    return frame


def mode_frame_set(main_window):
    """
    Creates frame with explanatory text, mode buttons/text each in subframes.

    Args:
        frame(tkinter.Frame)

    Returns: tkinter.Frame
    """
    mode_frame = tk.Frame(main_window)

    mode_opt = tk.Label(mode_frame,
                        text='There are two mode options:\n')
    mode_opt.pack()

    full_mode_frame = tk.Frame(mode_frame)
    full_mode_button = full_button(full_mode_frame)
    full_mode_frame.pack()

    quick_mode_frame = tk.Frame(mode_frame)
    quick_mode_button = quick_button(quick_mode_frame)
    #    quick_button(quick_mode_frame)
    quick_mode_frame.pack()

    mode_frame.pack()
    return mode_frame, full_mode_frame, quick_mode_frame


def main_setup():
    """
    Sets up main Tkinter window and widgets.

    Returns: tkinter.Frame, tkinter.Button
    """
    main_window = tk.Tk()
    main_window.title(f'XKCD archiver v{__version__}')
    main_window.geometry('400x400')

    descr = tk.Label(main_window,
                     text='This script searches xkcd.com '
                          'and downloads each comic.')
    descr.pack()

    venv = venv_test(main_window)
    venv.pack()

    mode_frame, full_mode_frame, quick_mode_frame = mode_frame_set(main_window)

    exit_app = tk.Button(main_window,
                         text='Quit',
                         command=main_window.destroy)
    exit_app.pack()

    return main_window, mode_frame, full_mode_frame, quick_mode_frame, exit_app


if __name__ == '__main__':
    main_window, mode_frame, full_mode_frame, quick_mode_frame, exit_app = main_setup()
    main_window.mainloop()
