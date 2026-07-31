"""Automarket utility helpers."""

from importlib import import_module

__version__ = "0.1.0"

_EXPORTS = {
    "AWSToolbox": "automarket_utils.aws",
    "add_year_week": "automarket_utils.core",
    "clean_mojibake": "automarket_utils.core",
    "create_csv_file_in_drive_folder": "automarket_utils.drive",
    "create_folder_in_drive_folder": "automarket_utils.drive",
    "create_sheets_in_drive_folder": "automarket_utils.drive",
    "custom_read": "automarket_utils.core",
    "from_drive_to_local": "automarket_utils.drive",
    "get_dates_dataframe": "automarket_utils.core",
    "get_last_modification_date_drive": "automarket_utils.drive",
    "insert_value_by_row_id_and_column_name": "automarket_utils.drive",
    "last_column_with_one": "automarket_utils.core",
    "list_file_ids_for_drive_folder": "automarket_utils.drive",
    "millions_formatter": "automarket_utils.core",
    "process_columns": "automarket_utils.core",
    "read_csv_from_drive": "automarket_utils.drive",
    "read_from_google_sheets": "automarket_utils.drive",
    "remove_accents": "automarket_utils.core",
    "send_google_chat_notification": "automarket_utils.drive",
    "update_sheets_in_drive_folder": "automarket_utils.drive",
    "update_sheets_in_drive_folder_chunked": "automarket_utils.drive",
    "write_csv_to_drive": "automarket_utils.drive",
}

__all__ = ["__version__", *_EXPORTS]


def __getattr__(name):
    if name in _EXPORTS:
        module = import_module(_EXPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
