All staged project files are preserved. Files larger than 10 MiB use Git LFS.
After cloning, run `git lfs pull`, then `python restore-large-files.py` to restore files split to meet the 2 GiB LFS limit. SHA-256 checks verify restoration.
The original local repository and files have not been rewritten.
