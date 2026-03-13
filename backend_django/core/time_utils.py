from datetime import datetime


def get_current_season() -> str:
    month = datetime.utcnow().month
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    if month in (9, 10, 11):
        return "Autumn"
    return "Winter"
