#!/usr/bin/env python3
"""
Tests for CLI File Organizer
=============================
Run: python -m pytest test_organizer.py -v
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from organizer import get_category, organize_folder, EXTENSION_MAP


class TestGetCategory(unittest.TestCase):
    """Test file extension → category mapping."""

    def test_image_extensions(self):
        self.assertEqual(get_category(Path("photo.jpg")), "Images")
        self.assertEqual(get_category(Path("logo.PNG")), "Images")
        self.assertEqual(get_category(Path("icon.svg")), "Images")

    def test_document_extensions(self):
        self.assertEqual(get_category(Path("report.pdf")), "Documents")
        self.assertEqual(get_category(Path("notes.txt")), "Documents")
        self.assertEqual(get_category(Path("data.csv")), "Documents")

    def test_video_extensions(self):
        self.assertEqual(get_category(Path("movie.mp4")), "Videos")
        self.assertEqual(get_category(Path("clip.MKV")), "Videos")

    def test_audio_extensions(self):
        self.assertEqual(get_category(Path("song.mp3")), "Audio")
        self.assertEqual(get_category(Path("track.flac")), "Audio")

    def test_code_extensions(self):
        self.assertEqual(get_category(Path("script.py")), "Code")
        self.assertEqual(get_category(Path("app.js")), "Code")
        self.assertEqual(get_category(Path("main.go")), "Code")

    def test_archive_extensions(self):
        self.assertEqual(get_category(Path("backup.zip")), "Archives")
        self.assertEqual(get_category(Path("data.tar.gz")), "Archives")

    def test_unknown_extension(self):
        self.assertEqual(get_category(Path("file.xyz123")), "Others")

    def test_case_insensitive(self):
        self.assertEqual(get_category(Path("FILE.JPG")), "Images")
        self.assertEqual(get_category(Path("Document.PDF")), "Documents")


class TestOrganizeFolder(unittest.TestCase):
    """Test the folder organization logic."""

    def setUp(self):
        """Create a temporary directory with sample files."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.sample_files = [
            "photo.jpg",
            "document.pdf",
            "song.mp3",
            "video.mp4",
            "archive.zip",
            "script.py",
            "mystery_file",
        ]
        for f in self.sample_files:
            (self.test_dir / f).touch()

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_files_organized_into_categories(self):
        organize_folder(self.test_dir)
        self.assertTrue((self.test_dir / "Images" / "photo.jpg").exists())
        self.assertTrue((self.test_dir / "Documents" / "document.pdf").exists())
        self.assertTrue((self.test_dir / "Audio" / "song.mp3").exists())
        self.assertTrue((self.test_dir / "Videos" / "video.mp4").exists())
        self.assertTrue((self.test_dir / "Archives" / "archive.zip").exists())
        self.assertTrue((self.test_dir / "Code" / "script.py").exists())
        self.assertTrue((self.test_dir / "Others" / "mystery_file").exists())

    def test_dry_run_does_not_move_files(self):
        organize_folder(self.test_dir, dry_run=True)
        # Files should still be in the root folder
        for f in self.sample_files:
            self.assertTrue((self.test_dir / f).exists())

    def test_no_category_folders_created_in_dry_run(self):
        organize_folder(self.test_dir, dry_run=True)
        # No subfolders should be created
        subdirs = [d for d in self.test_dir.iterdir() if d.is_dir()]
        self.assertEqual(len(subdirs), 0)

    def test_recursive_flag(self):
        # Create a subfolder with files
        sub = self.test_dir / "subfolder"
        sub.mkdir()
        (sub / "nested.jpg").touch()

        organize_folder(self.test_dir, recursive=True)
        # The nested file should be moved to Images
        self.assertTrue((self.test_dir / "Images" / "nested.jpg").exists())

    def test_empty_folder(self):
        empty = Path(tempfile.mkdtemp())
        result = organize_folder(empty)
        self.assertEqual(result, {})
        shutil.rmtree(empty)

    def test_duplicate_filename_handling(self):
        # Create two files with the same name in different locations
        sub = self.test_dir / "subfolder"
        sub.mkdir()
        (sub / "photo.jpg").touch()  # same name as root photo.jpg

        organize_folder(self.test_dir, recursive=True)
        # Both should exist in Images folder
        images_dir = self.test_dir / "Images"
        jpg_files = list(images_dir.glob("photo*"))
        self.assertEqual(len(jpg_files), 2)

    def test_extension_map_completeness(self):
        """Verify all category extensions are in the reverse map."""
        for category, extensions in [
            ("Images", [".jpg", ".png", ".gif"]),
            ("Documents", [".pdf", ".txt", ".docx"]),
            ("Videos", [".mp4", ".mkv"]),
            ("Audio", [".mp3", ".wav"]),
        ]:
            for ext in extensions:
                self.assertIn(ext, EXTENSION_MAP)
                self.assertEqual(EXTENSION_MAP[ext], category)


if __name__ == "__main__":
    unittest.main()


class TestUndoFeature(unittest.TestCase):
    """Test the undo/restore functionality."""

    def setUp(self):
        """Create a temporary directory with sample files."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.sample_files = [
            "photo.jpg",
            "document.pdf",
            "song.mp3",
            "video.mp4",
            "archive.zip",
            "script.py",
        ]
        for f in self.sample_files:
            (self.test_dir / f).touch()

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_log_file_created_after_organize(self):
        organize_folder(self.test_dir)
        log_path = self.test_dir / ".organizer_log.json"
        self.assertTrue(log_path.exists())

    def test_log_file_not_created_in_dry_run(self):
        organize_folder(self.test_dir, dry_run=True)
        log_path = self.test_dir / ".organizer_log.json"
        self.assertFalse(log_path.exists())

    def test_undo_restores_files(self):
        organize_folder(self.test_dir)

        # Verify files were moved
        self.assertTrue((self.test_dir / "Images" / "photo.jpg").exists())
        self.assertFalse((self.test_dir / "photo.jpg").exists())

        # Undo
        from organizer import undo_organize
        undo_organize(self.test_dir)

        # Verify files are back
        for f in self.sample_files:
            self.assertTrue((self.test_dir / f).exists(), f"{f} should be restored")

        # Verify category folders are cleaned up
        self.assertFalse((self.test_dir / "Images").exists())
        self.assertFalse((self.test_dir / "Documents").exists())

    def test_undo_without_log_shows_message(self):
        from organizer import undo_organize
        # Should not raise an error
        undo_organize(self.test_dir)

    def test_log_file_contains_correct_data(self):
        organize_folder(self.test_dir)
        from organizer import load_log
        log = load_log(self.test_dir)
        self.assertIn("timestamp", log)
        self.assertIn("moves", log)
        self.assertEqual(len(log["moves"]), len(self.sample_files))
        for entry in log["moves"]:
            self.assertIn("original", entry)
            self.assertIn("current", entry)
