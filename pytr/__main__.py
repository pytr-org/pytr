#!/usr/bin/env python3
import logging

from pytr.main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log = logging.getLogger(__name__)
        log.info("Exiting...")
        exit()
    except Exception as e:
        log = logging.getLogger(__name__)
        log.fatal(e)
        raise
