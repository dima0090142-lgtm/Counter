"""One A4 page check through LibreOffice (skipped when it is not installed)."""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools"))
import check_print  # noqa: E402

from ptw import storage  # noqa: E402


@pytest.mark.skipif(not check_print.find_soffice(), reason="LibreOffice not installed")
def test_worst_case_permits_print_on_one_page(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(storage, "save", storage.save)  # restored after the test
    store = storage.Store()
    store.history = []
    # a few of the biggest teams plus the stress permit keep the test fast
    store.jobs = sorted(store.jobs, key=lambda j: -(j["officers"][1] + j["ratings"][1]))[:4]
    results, _ = check_print.run(store, str(tmp_path / "out"), check_print.find_soffice())
    assert [r for r in results if r[1] != 1 or r[2]] == []
    assert len(results) == 7  # 4 jobs + stress + 2 with the long A.O.
    shutil.rmtree(tmp_path / "out", ignore_errors=True)
