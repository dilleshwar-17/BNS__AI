from pathlib import Path


class FileUtils:
    @staticmethod
    def ensure_dir(path: str):
        Path(path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_filename(filename: str) -> str:
        import re

        return re.sub(r"[^\w\.\-]", "_", filename)

    @staticmethod
    def get_extension(filename: str) -> str:
        return Path(filename).suffix.lower()
