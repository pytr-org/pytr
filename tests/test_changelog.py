import os

import pytest


def test_changelog_exists_and_unreleased_header():
    path = os.path.join(os.getcwd(), "CHANGELOG.md")
    assert os.path.isfile(path), "CHANGELOG.md must exist"
    with open(path, "r") as f:
        text = f.read()
    assert "## [Unreleased]" in text, "CHANGELOG.md must contain an Unreleased section"
