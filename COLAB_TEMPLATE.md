# Colab Bootstrap Template

This is a notebook-ready bootstrap for the new split between `Atlas` and `automarket-utils`.

## Cell 1: Environment bootstrap

```python
import os

from_drive = True  # same flag you use everywhere

if os.environ.get("ATLAS_BOOTSTRAPPED") != "1":
    # ---------- GIT ON COLAB ONLY ----------
    try:
        from google.colab import userdata

        git_token = userdata.get("gitToken")
        git_user = userdata.get("gitUser")
        atlas_branch = "dev"
        utils_ref = "main"  # change to a version tag for more reproducibility

        os.chdir("/content")

        # Clone Atlas only if the notebook still needs Atlas-specific code.
        if not os.path.isdir("Atlas"):
            atlas_url = f"https://{git_token}@github.com/rene-aum/Atlas.git"
            !git clone {atlas_url}

        # Install the shared utilities as a separate package.
        !pip -q install --upgrade pip
        !pip -q install "git+https://github.com/rene-aum/automarket-utils.git@{utils_ref}"

        %cd Atlas
        !git fetch origin {atlas_branch}
        !git checkout {atlas_branch}
        !git pull origin {atlas_branch}

        # Keep the Atlas-specific project requirements here.
        !pip -q install -r PipelinesConsumo/src/requirements.txt
        %cd PipelinesConsumo

    except Exception as e:
        print(e)
        print("Running in another environment, probably not Colab.")

    # ---------- DRIVE + SHEETS ----------
    if from_drive:
        from pydrive2.auth import GoogleAuth
        from pydrive2.drive import GoogleDrive
        from google.colab import auth
        from oauth2client.client import GoogleCredentials
        import gspread
        from google.auth import default

        auth.authenticate_user()
        gauth = GoogleAuth()
        gauth.credentials = GoogleCredentials.get_application_default()
        drive = GoogleDrive(gauth)

        creds, _ = default()
        gc = gspread.authorize(creds)

    os.environ["ATLAS_BOOTSTRAPPED"] = "1"
else:
    print("Bootstrap already done, assuming orchestrator ran it.")
```

## Cell 2: Imports

```python
import warnings
from datetime import datetime, timedelta

import glob
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys

from automarket_utils import (
    AWSToolbox,
    add_year_week,
    clean_mojibake,
    create_csv_file_in_drive_folder,
    create_sheets_in_drive_folder,
    custom_read,
    from_drive_to_local,
    get_dates_dataframe,
    get_last_modification_date_drive,
    insert_value_by_row_id_and_column_name,
    list_file_ids_for_drive_folder,
    process_columns,
    read_csv_from_drive,
    read_from_google_sheets,
    remove_accents,
    send_google_chat_notification,
    update_sheets_in_drive_folder,
    update_sheets_in_drive_folder_chunked,
    write_csv_to_drive,
)

from PipelinesConsumo.src.rawAtlas import RawAtlas
from PipelinesConsumo.src.processedAtlas import ProcessedAtlas
from src.constants import (
    atlas_consumo_output_folder_id,
    atlas_raw_output_folder_id,
    consumo_sheets_ids_dict,
    data_source_folder_id,
    folder_id_bauto_gabo,
    id_edas_referenciados,
    id_reporte_ventas,
    id_torre_de_control,
    raw_output_ids,
)

warnings.filterwarnings("ignore")
```

## Cell 3: Optional path helper

```python
# If the notebook ever needs to import local Atlas modules not already on sys.path,
# prefer explicit paths over repeated relative sys.path.append calls.
import sys

if "/content/Atlas" not in sys.path:
    sys.path.append("/content/Atlas")
```

## Notes

- Prefer pinning `automarket-utils` to a tag, not `main`, once the package is stable.
- Keep Atlas-specific code in Atlas and shared helpers in `automarket-utils`.
- New notebook code should import from `automarket_utils`, not `utils`.
