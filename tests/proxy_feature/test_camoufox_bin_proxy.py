from camoufox.sync_api import Camoufox
import os

bin_path = "/Users/lugon/dev/2026-3/tegufox-browser/build/Tegufox.app/Contents/MacOS/tegufox"

with Camoufox(
    headless=True,
    i_know_what_im_doing=True,
    executable_path=bin_path
) as browser:
    os.system("ps -ax | grep -E 'tegufox|camoufox|firefox' | grep -v grep | head -3")
