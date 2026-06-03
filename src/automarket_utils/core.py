"""Core dataframe and string helpers."""

from datetime import datetime
import importlib
from zoneinfo import ZoneInfo
import unicodedata

MEXICO_TZ = "America/Mexico_City"


def _require_module(module_name, extra_name=None):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        if extra_name:
            raise ModuleNotFoundError(
                f"{module_name} is required for this feature. "
                f"Install it with `pip install \"automarket-utils[{extra_name}]\"`."
            ) from exc
        raise


def get_dates_dataframe(start="2024-03-01"):
    pd = _require_module("pandas")
    today = datetime.now(tz=ZoneInfo(MEXICO_TZ))
    return pd.DataFrame({"date": pd.date_range(start, today.strftime("%Y-%m-%d"))})


def custom_read(csv_path=None, excel_path=None, excel_tab_name=None):
    pd = _require_module("pandas")
    if csv_path:
        return pd.read_csv(csv_path)

    if excel_path is None:
        raise ValueError("excel_path must be provided when csv_path is not given")
    if excel_tab_name is None:
        raise ValueError("excel_tab_name must be provided when reading Excel")

    return pd.read_excel(excel_path, sheet_name=excel_tab_name)


def last_column_with_one(row):
    # Reverse the order of columns to find the last occurrence.
    for col in reversed(row.index[1:]):
        if row[col] == 1:
            return col
    return None


def process_columns(df):
    """Lowercase and normalize column names."""
    unidecode = _require_module("unidecode", "core").unidecode
    df1 = df.copy()
    cols = [
        unidecode(
            c.strip()
            .lower()
            .replace(" ", "_")
            .replace(".", "")
            .replace(":", "")
            .replace("_/_", "_")
        )
        for c in df1.columns
    ]
    df1.columns = cols
    return df1


def millions_formatter(x, pos):
    """Format numbers as millions."""
    return f"{x / 1e6:.1f}M"


def add_year_week(df, date_column="date"):
    """Add year, week, year_week, monday_of_week, and sunday_of_week columns."""
    pd = _require_module("pandas")
    if date_column not in df.columns:
        raise KeyError(f"{date_column!r} not found in dataframe columns")

    dates = pd.to_datetime(df[date_column])
    iso_week = dates.dt.isocalendar().week

    new_df = df.copy().assign(
        year=dates.dt.year,
        week=iso_week.astype(int),
        year_week=dates.dt.year.astype(str) + "-" + iso_week.astype(str),
        monday_of_week=(
            dates - pd.to_timedelta(dates.dt.dayofweek, unit="d")
        ).dt.strftime("%Y-%m-%d"),
        sunday_of_week=(
            dates + pd.to_timedelta(6 - dates.dt.dayofweek, unit="d")
        ).dt.strftime("%Y-%m-%d"),
    )
    return new_df


def remove_accents(text):
    if isinstance(text, str):
        unidecode = _require_module("unidecode", "core").unidecode
        return unidecode(text)
    return text


def clean_mojibake(x):
    pd = _require_module("pandas")
    if pd.isna(x):
        return x

    x = str(x)

    # Repair common mojibake before removing accents.
    for enc in ("macroman", "latin1", "cp1252"):
        try:
            repaired = x.encode(enc).decode("utf-8")
            if repaired != x:
                x = repaired
                break
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    x = unicodedata.normalize("NFKD", x)
    x = x.encode("ascii", "ignore").decode("ascii")

    return x.upper()
