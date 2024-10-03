XKCD_archiver - Downloads every single XKCD comic.

Webscraper that downloads xkcd comics.
Uses multithreading, checks if comic already downloaded for increased
    efficiency on rerun.

Two run modes: Full and Quick
Full mode goes through every comic.
Quick mode checked latest 100 comics, quits when it reaches the
    first comic that is already downloaded.

Basic GUI included.     
Windows .bat file included, which ensures dependencies are installed before running.    

This project is semi-abandoned. It is without tests, and I have no plans to work on tests or improvements at this time.

Derived from original project: https://automatetheboringstuff.com/chapter11/
