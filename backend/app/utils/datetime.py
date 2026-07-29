from datetime import datetime, timezone


class DateTimeUtils:
    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def format_dt(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return dt.strftime(fmt)

    @staticmethod
    def iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()
