import shutil
from datetime import datetime
from pathlib import Path


def main():
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_path = Path("data/bnsai.db")
    if db_path.exists():
        shutil.copy(db_path, backup_dir / f"bnsai_{timestamp}.db")
        print(f"Backup created: backups/bnsai_{timestamp}.db")
    else:
        print("No database found to backup")


if __name__ == "__main__":
    main()
