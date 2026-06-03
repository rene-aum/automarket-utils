"""Google Drive and Google Sheets helpers."""

import importlib
import io
import json
import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo


MEXICO_TZ = "America/Mexico_City"


def _require_module(module_name, extra_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise ModuleNotFoundError(
            f"{module_name} is required for this feature. "
            f"Install it with `pip install \"automarket-utils[{extra_name}]\"`."
        ) from exc


def from_drive_to_local(drive, id_file, file_name):
    """Move a file from Google Drive to the current local directory."""
    links = drive.CreateFile({"id": id_file})
    links.GetContentFile(file_name)


def get_last_modification_date_drive(drive, sheet_id):
    id_ = sheet_id
    link = drive.CreateFile({"id": id_})
    timestamp_utc = link.GetRevisions()[-1].get("modifiedDate")
    dt_utc = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
    dt_mexico_city = dt_utc.astimezone(ZoneInfo(MEXICO_TZ))
    return dt_mexico_city.strftime("%Y-%m-%d")


def create_sheets_in_drive_folder(gc, file_name, folder_id, df_to_set=None):
    spreadsheet = gc.create(file_name, folder_id=folder_id)
    worksheet = spreadsheet.sheet1
    if df_to_set is not None:
        gspread_dataframe = _require_module("gspread_dataframe", "drive")
        gspread_dataframe.set_with_dataframe(worksheet, df_to_set)
    print(f"Google Sheet {file_name} created and updated in folder ID: {folder_id}")


def update_sheets_in_drive_folder(
    gc,
    spreadsheet_id,
    worksheet_name,
    df_to_update,
    retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
):
    """Update a Google Sheets worksheet with a DataFrame, retrying on failure.
    """
    gspread_dataframe = _require_module("gspread_dataframe", "drive")

    attempt = 0
    delay = initial_delay
    while attempt < retries:
        attempt += 1
        spreadsheet_title = spreadsheet_id
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            spreadsheet_title = spreadsheet.title
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet.clear()
            gspread_dataframe.set_with_dataframe(worksheet, df_to_update)

            print(
                f"[attempt {attempt}/{retries}] "
                f"Google Sheet {spreadsheet_title!r} - {worksheet_name!r} "
                f"updated with new data."
            )
            return
        except Exception as e:
            print(
                f"[attempt {attempt}/{retries}] "
                f"Failed to update sheet {spreadsheet_title!r} - {worksheet_name!r}: {e}"
            )

            if attempt >= retries:
                print("Exhausted all retries; giving up.")
                raise

            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= backoff_factor


def read_from_google_sheets(
    gc,
    spreadsheet_id,
    sheetname=None,
    retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
):
    """Read a Google Sheets worksheet into a DataFrame, retrying on failure."""
    gspread_dataframe = _require_module("gspread_dataframe", "drive")

    attempt = 0
    delay = initial_delay
    while attempt < retries:
        attempt += 1
        spreadsheet_title = spreadsheet_id
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            spreadsheet_title = spreadsheet.title
            if sheetname is None:
                worksheet = spreadsheet.sheet1
            else:
                worksheet = spreadsheet.worksheet(sheetname)
            df = gspread_dataframe.get_as_dataframe(
                worksheet,
                evaluate_formulas=True,
                value_render_option="UNFORMATTED_VALUE",
            )
            print(
                f"[attempt {attempt}/{retries}] "
                f"Google Sheet {spreadsheet_title!r} - {sheetname or 'sheet1'!r} "
                f"read successfully."
            )
            return df
        except Exception as e:
            print(
                f"[attempt {attempt}/{retries}] "
                f"Failed to read sheet {spreadsheet_title!r} - {sheetname or 'sheet1'!r}: {e}"
            )
            if attempt >= retries:
                print("Exhausted all retries; giving up.")
                raise
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= backoff_factor


def list_file_ids_for_drive_folder(drive, folder_id: str):
    file_list = drive.ListFile({"q": f"'{folder_id}' in parents and trashed=false"}).GetList()
    file_id_dict = {}
    for file in file_list:
        file_id_dict[file["title"]] = file["id"]
    return file_id_dict


def read_csv_from_drive(drive, file_id):
    pd = importlib.import_module("pandas")
    file = drive.CreateFile({"id": file_id})
    csv_bytes = file.GetContentString()
    return pd.read_csv(io.StringIO(csv_bytes))


def write_csv_to_drive(drive, file_id, df):
    """Overwrite an existing CSV in Drive using its file ID."""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    file = drive.CreateFile({"id": file_id})
    file.SetContentString(csv_buffer.getvalue())
    file.Upload()

    print("Updated successfully.")


def create_csv_file_in_drive_folder(drive, folder_id, df, filename):
    """Create a CSV file in a Drive folder."""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    csv_str = csv_buffer.getvalue()
    file_metadata = {
        "title": filename,
        "mimeType": "text/csv",
        "parents": [{"id": folder_id}],
    }
    file = drive.CreateFile(file_metadata)
    file.SetContentString(csv_str)
    file.Upload()
    print("Uploaded file ID:", file["id"])
    return file["id"]


def send_google_chat_notification(webhook_url: str, msg: str):
    try:
        requests = importlib.import_module("requests")
        payload = {"text": f"*{msg}*"}
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json; charset=UTF-8"},
        )

        if response.status_code == 200:
            print("Notificación enviada a Google Chat.")
        else:
            print(f"Error al enviar: {response.status_code}")
    except Exception as e:
        print(f"Error en la función: {e}")


def update_sheets_in_drive_folder_chunked(
    gc,
    spreadsheet_id,
    worksheet_name,
    df_to_update,
    chunk_size: int = 10000,
    retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    clear_first: bool = True,
    include_header: bool = True,
):
    """Update a Google Sheets worksheet with a DataFrame in row chunks."""
    pd = importlib.import_module("pandas")

    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    if clear_first:
        worksheet.clear()

    n_rows, n_cols = df_to_update.shape
    total_rows_to_write = n_rows + 1 if include_header else n_rows

    if total_rows_to_write == 0:
        print(f"Sheet {spreadsheet_id!r} - {worksheet_name!r}: nothing to write.")
        return

    def _colnum_to_a1(col_num: int) -> str:
        result = ""
        while col_num > 0:
            col_num, rem = divmod(col_num - 1, 26)
            result = chr(65 + rem) + result
        return result

    last_col_letter = _colnum_to_a1(n_cols)

    start_row = 1
    if include_header:
        header_values = [df_to_update.columns.astype(str).tolist()]
        header_range = f"A1:{last_col_letter}1"
        worksheet.update(
            range_name=header_range,
            values=header_values,
            value_input_option="RAW",
        )
        start_row = 2

    n_chunks = math.ceil(n_rows / chunk_size)

    for chunk_idx in range(n_chunks):
        row_start = chunk_idx * chunk_size
        row_end = min((chunk_idx + 1) * chunk_size, n_rows)

        chunk_df = df_to_update.iloc[row_start:row_end]
        values = chunk_df.where(pd.notnull(chunk_df), "").values.tolist()

        sheet_row_start = start_row + row_start
        sheet_row_end = sheet_row_start + len(values) - 1
        range_name = f"A{sheet_row_start}:{last_col_letter}{sheet_row_end}"

        attempt = 0
        delay = initial_delay

        while attempt < retries:
            attempt += 1
            try:
                worksheet.update(
                    range_name=range_name,
                    values=values,
                    value_input_option="RAW",
                )
                print(
                    f"[chunk {chunk_idx + 1}/{n_chunks}] "
                    f"[attempt {attempt}/{retries}] "
                    f"Wrote rows {row_start}:{row_end} "
                    f"to {spreadsheet_id!r} - {worksheet_name!r}."
                )
                break
            except Exception as e:
                print(
                    f"[chunk {chunk_idx + 1}/{n_chunks}] "
                    f"[attempt {attempt}/{retries}] "
                    f"Failed writing rows {row_start}:{row_end} "
                    f"to {spreadsheet_id!r} - {worksheet_name!r}: {e}"
                )

                if attempt >= retries:
                    print("Exhausted retries for current chunk; giving up.")
                    raise

                print(f"Retrying chunk in {delay} seconds...")
                time.sleep(delay)
                delay *= backoff_factor


def insert_value_by_row_id_and_column_name(
    gc,
    spreadsheet_id: str,
    worksheet_name: str,
    row_id,
    column_name: str,
    value_to_insert,
    id_col: int = 1,
    header_row: int = 1,
    retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
):
    """Insert/update a value in a column by matching the row ID."""
    attempt = 0
    delay = initial_delay

    while attempt < retries:
        attempt += 1
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)

            headers = worksheet.row_values(header_row)
            headers_normalized = [str(h).strip() for h in headers]

            if column_name not in headers_normalized:
                raise ValueError(
                    f"Column {column_name!r} not found in header row {header_row}."
                )

            target_col = headers_normalized.index(column_name) + 1

            id_values = worksheet.col_values(id_col)
            row_id_str = str(row_id).strip()

            matched_row = None
            for i, current_id in enumerate(id_values, start=1):
                if str(current_id).strip() == row_id_str:
                    matched_row = i
                    break

            if matched_row is None:
                raise ValueError(f"Row ID {row_id!r} not found in column {id_col}.")

            worksheet.update_cell(matched_row, target_col, value_to_insert)

            print(
                f"[attempt {attempt}/{retries}] "
                f"Updated sheet {spreadsheet_id!r} - {worksheet_name!r}: "
                f"row_id={row_id!r}, matched_row={matched_row}, "
                f"column_name={column_name!r}, value={value_to_insert!r}"
            )

            return {
                "updated": True,
                "row_id": row_id,
                "matched_row": matched_row,
                "column_name": column_name,
                "value_inserted": value_to_insert,
            }
        except Exception as e:
            print(
                f"[attempt {attempt}/{retries}] "
                f"Failed to insert value into sheet {spreadsheet_id!r} - {worksheet_name!r}: {e}"
            )

            if attempt >= retries:
                print("Exhausted all retries; giving up.")
                raise

            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= backoff_factor
