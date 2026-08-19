import shutil
from pathlib import Path


def remove_job_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
