import pandas as pd

from automarket_utils.core import add_year_week, clean_mojibake, custom_read, process_columns


def test_process_columns_normalizes_text():
    df = pd.DataFrame(columns=[" Café Total ", "Order.Date"])

    result = process_columns(df)

    assert list(result.columns) == ["cafe_total", "orderdate"]


def test_add_year_week_uses_requested_date_column():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2024-01-01", "2024-01-07"]),
            "value": [1, 2],
        }
    )

    result = add_year_week(df, date_column="event_date")

    assert list(result["year"]) == [2024, 2024]
    assert list(result["week"]) == [1, 1]
    assert list(result["year_week"]) == ["2024-1", "2024-1"]
    assert list(result["monday_of_week"]) == ["2024-01-01", "2024-01-01"]
    assert list(result["sunday_of_week"]) == ["2024-01-07", "2024-01-07"]


def test_clean_mojibake_repairs_text():
    assert clean_mojibake("EspaÃ±a") == "ESPANA"


def test_custom_read_reads_csv(tmp_path):
    path = tmp_path / "sample.csv"
    pd.DataFrame({"a": [1, 2]}).to_csv(path, index=False)

    result = custom_read(csv_path=path)

    pd.testing.assert_frame_equal(result, pd.DataFrame({"a": [1, 2]}))
