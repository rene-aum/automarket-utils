# automarket-utils

Internal Python utilities for dataframe cleaning, AWS/S3 helpers, and Google Drive / Sheets workflows.

## Install

From a local checkout:

```bash
pip install .
```

With optional integrations:

```bash
pip install ".[aws]"
pip install ".[drive]"
pip install ".[dev]"
```

If you publish this package to an internal index or install from Git, the distribution name is `automarket-utils` and the import name is `automarket_utils`.

## Package Layout

- `automarket_utils.core` for dataframe and string helpers
- `automarket_utils.aws` for `AWSToolbox`
- `automarket_utils.drive` for Google Drive and Google Sheets helpers

## Legacy Imports

For transition purposes, the repository keeps thin compatibility shims at the root level:

- `utils.py`
- `aws_toolbox.py`
- `drive_toolbox.py`

New code should import from `automarket_utils` instead of the legacy module names.

## Example

```python
from automarket_utils import AWSToolbox, process_columns

clean_df = process_columns(df)
aws = AWSToolbox(bucket="my-bucket")
```
