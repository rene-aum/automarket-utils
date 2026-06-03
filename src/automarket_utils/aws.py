"""AWS and S3 helpers."""

import getpass
import importlib
import os
import re


def _require_module(module_name, extra_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise ModuleNotFoundError(
            f"{module_name} is required for this feature. "
            f"Install it with `pip install \"automarket-utils[{extra_name}]\"`."
        ) from exc


class AWSToolbox:
    """
    Small Colab-friendly toolbox for S3 + parquet workflows.

    Design goals:
    - configure AWS once
    - no need to pass fs in every call
    - allow default bucket
    - lazy initialization of S3FileSystem
    """

    def __init__(
        self,
        bucket=None,
        profile=None,
        region=None,
        key=None,
        secret=None,
        token=None,
    ):
        self.bucket = bucket
        self.profile = profile
        self.region = region
        self.key = key
        self.secret = secret
        self.token = token

        self._fs = None
        self._session = None

    def set_credentials_interactive(self, store_in_env=True):
        """Prompt interactively for AWS credentials."""
        self.key = getpass.getpass("Enter your AWS_ACCESS_KEY_ID: ")
        self.secret = getpass.getpass("Enter your AWS_SECRET_ACCESS_KEY: ")
        token = getpass.getpass("Enter your AWS_SESSION_TOKEN (optional): ")
        self.token = token or None

        if store_in_env:
            os.environ["AWS_ACCESS_KEY_ID"] = self.key
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.secret
            if self.token:
                os.environ["AWS_SESSION_TOKEN"] = self.token

        self._fs = None
        self._session = None
        return "Successfully stored credentials"

    def set_credentials_colab(self, store_in_env=True):
        """Load AWS credentials from Google Colab userdata."""
        try:
            from google.colab import userdata
        except ImportError as e:
            raise RuntimeError(
                "set_credentials_colab can only be used inside Google Colab."
            ) from e

        def _get_optional_secret(name):
            try:
                return userdata.get(name)
            except Exception as e:
                if e.__class__.__name__ == "SecretNotFoundError":
                    return None
                raise

        self.key = userdata.get("AWS_ACCESS_KEY_ID")
        self.secret = userdata.get("AWS_SECRET_ACCESS_KEY")
        self.token = _get_optional_secret("AWS_SESSION_TOKEN") or None

        if not self.key or not self.secret:
            raise ValueError(
                "Missing Colab AWS secrets. Please set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY in Colab userdata."
            )

        if store_in_env:
            os.environ["AWS_ACCESS_KEY_ID"] = self.key
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.secret
            if self.token:
                os.environ["AWS_SESSION_TOKEN"] = self.token
            else:
                os.environ.pop("AWS_SESSION_TOKEN", None)

        self._fs = None
        self._session = None
        return "Successfully stored credentials from Colab"

    @property
    def session(self):
        """Lazily create a boto3 Session."""
        if self._session is None:
            boto3 = _require_module("boto3", "aws")
            session_kwargs = {}
            if self.profile:
                session_kwargs["profile_name"] = self.profile
            if self.region:
                session_kwargs["region_name"] = self.region

            if self.key and self.secret:
                session_kwargs["aws_access_key_id"] = self.key
                session_kwargs["aws_secret_access_key"] = self.secret
                if self.token:
                    session_kwargs["aws_session_token"] = self.token

            self._session = boto3.Session(**session_kwargs)

        return self._session

    @property
    def fs(self):
        """Lazily create and cache an s3fs filesystem."""
        if self._fs is None:
            s3fs = _require_module("s3fs", "aws")
            fs_kwargs = {}
            if self.profile:
                fs_kwargs["profile"] = self.profile

            if self.key and self.secret:
                fs_kwargs["key"] = self.key
                fs_kwargs["secret"] = self.secret
                if self.token:
                    fs_kwargs["token"] = self.token

            if self.region:
                fs_kwargs["client_kwargs"] = {"region_name": self.region}

            self._fs = s3fs.S3FileSystem(**fs_kwargs)

        return self._fs

    def test_credentials(self, bucket=None):
        """Check that credentials can access a bucket."""
        bucket = bucket or self.bucket
        if not bucket:
            raise ValueError("You must provide a bucket or set a default bucket.")

        try:
            s3 = self.session.client("s3")
            s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
            return True
        except Exception as e:
            print(f"AWS credentials test failed: {e}")
            return False

    def _normalize_path(self, path):
        """
        Accept:
        - full s3://bucket/key
        - bucket/key
        - key (if default bucket is set)
        Return a path suitable for s3fs/pandas.
        """
        path = path.rstrip("/")

        if path.startswith("s3://"):
            return path

        if self.bucket is not None:
            if not path.startswith(f"{self.bucket}/"):
                return f"{self.bucket}/{path}"

        return path

    @staticmethod
    def _partition_dirs(fs, path, key):
        """Return [(value, full_path), ...] for directories like key=123 under `path`."""
        out = []
        for item in fs.ls(path, detail=True):
            name = item["name"].rstrip("/")
            leaf = name.split("/")[-1]

            m = re.fullmatch(rf"{re.escape(key)}=(\d+)", leaf)
            if not m:
                continue

            item_type = item.get("type", "")
            if item_type in ("directory", "dir", ""):
                out.append((int(m.group(1)), name))

        return out

    def latest_partition_path(self, base_path, levels=("year", "month", "day")):
        """Find the latest hive-style partition path."""
        path = self._normalize_path(base_path)

        for key in levels:
            candidates = self._partition_dirs(self.fs, path, key)
            if not candidates:
                raise FileNotFoundError(
                    f"No partitions found for '{key}' under: {path}"
                )

            _, path = max(candidates, key=lambda x: x[0])

        return path + "/"

    def read_parquet(self, path, engine="pyarrow", **kwargs):
        """Read parquet using the toolbox filesystem automatically."""
        pd = importlib.import_module("pandas")
        path = self._normalize_path(path)
        return pd.read_parquet(
            path,
            filesystem=self.fs,
            engine=engine,
            **kwargs,
        )

    def read_latest_partition(
        self,
        base_path,
        levels=("year", "month", "day"),
        engine="pyarrow",
        verbose=True,
        **kwargs,
    ):
        """Read the latest available partition into a DataFrame."""
        pd = importlib.import_module("pandas")
        path = self.latest_partition_path(base_path, levels=levels)
        if verbose:
            print(path)

        return pd.read_parquet(
            path,
            filesystem=self.fs,
            engine=engine,
            **kwargs,
        )
