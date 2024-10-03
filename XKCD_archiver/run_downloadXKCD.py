#!./downloadXKCD_env/Scripts/python
# rundownloadXKCD.py - runs downloadXKCD.py
"""
Created on Mon Oct 23 10:20:14 2017

@author: david.antonini // toonarmycaptain
"""

if __name__ == "__main__":
    import subprocess

    subprocess.Popen(["start", "downloadXKCD.py"], shell=True)
