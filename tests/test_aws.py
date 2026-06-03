import sys
import types

from automarket_utils.aws import AWSToolbox


class FakeS3FileSystem:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def ls(self, path, detail=True):
        self.calls.append(path)
        mapping = {
            "bucket/prefix": [
                {"name": "bucket/prefix/year=2024", "type": "directory"},
                {"name": "bucket/prefix/year=2025", "type": "directory"},
            ],
            "bucket/prefix/year=2025": [
                {"name": "bucket/prefix/year=2025/month=2", "type": "directory"},
                {"name": "bucket/prefix/year=2025/month=11", "type": "directory"},
            ],
            "bucket/prefix/year=2025/month=11": [
                {"name": "bucket/prefix/year=2025/month=11/day=3", "type": "directory"},
                {"name": "bucket/prefix/year=2025/month=11/day=15", "type": "directory"},
            ],
        }
        return mapping[path]


def test_normalize_path_and_latest_partition(monkeypatch):
    fake_fs = FakeS3FileSystem()
    monkeypatch.setitem(
        sys.modules,
        "s3fs",
        types.SimpleNamespace(S3FileSystem=lambda **kwargs: fake_fs),
    )
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        types.SimpleNamespace(Session=lambda **kwargs: types.SimpleNamespace(client=lambda name: None)),
    )

    toolbox = AWSToolbox(bucket="bucket")

    assert toolbox._normalize_path("prefix") == "bucket/prefix"
    assert toolbox._normalize_path("s3://other/path") == "s3://other/path"
    assert toolbox.latest_partition_path("prefix") == "bucket/prefix/year=2025/month=11/day=15/"
