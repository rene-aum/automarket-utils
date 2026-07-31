import sys
import types

import pandas as pd

from automarket_utils.drive import (
    create_folder_in_drive_folder,
    get_last_modification_date_drive,
    read_from_google_sheets,
)


class FakeFile:
    def __init__(self, revisions=None, dataframe=None, file_id=None):
        self._revisions = revisions or []
        self.result = dataframe
        self._id = file_id

    def GetRevisions(self):
        return self._revisions

    def GetContentFile(self, file_name):
        self.file_name = file_name

    def Upload(self):
        self.uploaded = True

    def __getitem__(self, key):
        if key == "id":
            return self._id
        raise KeyError(key)


class FakeSheet:
    def __init__(self, title, dataframe):
        self.title = title
        self.sheet1 = self
        self._dataframe = dataframe

    def worksheet(self, name):
        return self


class FakeClient:
    def __init__(self, dataframe):
        self._spreadsheet = FakeSheet("Demo Sheet", dataframe)

    def open_by_key(self, spreadsheet_id):
        return self._spreadsheet


def test_get_last_modification_date_drive():
    drive = types.SimpleNamespace(
        CreateFile=lambda payload: FakeFile(
            revisions=[{"modifiedDate": "2024-06-01T06:00:00Z"}]
        )
    )

    assert get_last_modification_date_drive(drive, "sheet-id") == "2024-06-01"


def test_read_from_google_sheets(monkeypatch):
    expected = pd.DataFrame({"a": [1, 2]})
    fake_client = FakeClient(expected)

    fake_module = types.SimpleNamespace(
        get_as_dataframe=lambda worksheet, **kwargs: worksheet._dataframe,
        set_with_dataframe=lambda *args, **kwargs: None,
    )
    monkeypatch.setitem(sys.modules, "gspread_dataframe", fake_module)

    result = read_from_google_sheets(fake_client, "sheet-id")

    pd.testing.assert_frame_equal(result, expected)


def test_create_folder_in_drive_folder(capsys):
    captured_payload = {}

    def create_file(payload):
        captured_payload.update(payload)
        return FakeFile(file_id="new-folder-id")

    drive = types.SimpleNamespace(CreateFile=create_file)

    result = create_folder_in_drive_folder(drive, "Demo Folder", "parent-folder-id")

    assert result == "new-folder-id"
    assert captured_payload == {
        "title": "Demo Folder",
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [{"id": "parent-folder-id"}],
    }
    assert "Created folder ID: new-folder-id" in capsys.readouterr().out
