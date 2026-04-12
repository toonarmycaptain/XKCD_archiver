"""Allow running as `python -m XKCD_archiver`."""

import sys

if "--tui" in sys.argv:
    from XKCD_archiver.tui import main

    main()
else:
    from XKCD_archiver.downloadXKCD import cli_run

    cli_run()
