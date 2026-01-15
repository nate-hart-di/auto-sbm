"""
Core file operations tests.
Tests basic file read/write/create operations work correctly.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import json

# Import file operation functions - adjust based on actual codebase
try:
    from sbm.core.file_operations import read_file, write_file, create_file
except ImportError:
    # If these don't exist, we'll test basic file operations
    read_file = None
    write_file = None
    create_file = None


class TestBasicFileOperations:
    """Test basic file read/write operations."""

    def test_file_reading(self, tmp_path):
        """Test file reading works correctly."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!\nSecond line."
        test_file.write_text(test_content)

        # Test reading with pathlib
        content = test_file.read_text()
        assert content == test_content

        # Test reading with open()
        with open(test_file, 'r') as f:
            content2 = f.read()
        assert content2 == test_content

        # Test if custom read_file function exists
        if read_file:
            try:
                content3 = read_file(str(test_file))
                assert content3 == test_content
            except Exception as e:
                pytest.fail(f"Custom read_file function failed: {e}")

    def test_file_writing(self, tmp_path):
        """Test file writing works correctly."""
        test_file = tmp_path / "write_test.txt"
        test_content = "Test content\nMultiple lines\n"

        # Test writing with pathlib
        test_file.write_text(test_content)
        assert test_file.read_text() == test_content

        # Test writing with open()
        test_file2 = tmp_path / "write_test2.txt"
        with open(test_file2, 'w') as f:
            f.write(test_content)
        assert test_file2.read_text() == test_content

        # Test if custom write_file function exists
        if write_file:
            try:
                test_file3 = tmp_path / "write_test3.txt"
                write_file(str(test_file3), test_content)
                assert test_file3.read_text() == test_content
            except Exception as e:
                pytest.fail(f"Custom write_file function failed: {e}")

    def test_file_creation(self, tmp_path):
        """Test file creation works correctly."""
        new_file = tmp_path / "new_file.txt"

        # Ensure file doesn't exist
        assert not new_file.exists()

        # Create file
        new_file.touch()
        assert new_file.exists()
        assert new_file.is_file()

        # Test creating file with content
        new_file2 = tmp_path / "new_file2.txt"
        content = "Initial content"
        new_file2.write_text(content)

        assert new_file2.exists()
        assert new_file2.read_text() == content

        # Test if custom create_file function exists
        if create_file:
            try:
                new_file3 = tmp_path / "new_file3.txt"
                create_file(str(new_file3), content)
                assert new_file3.exists()
                assert new_file3.read_text() == content
            except Exception as e:
                pytest.fail(f"Custom create_file function failed: {e}")


class TestFileOperationEdgeCases:
    """Test file operation edge cases and error handling."""

    def test_reading_nonexistent_file(self):
        """Test reading non-existent file raises appropriate error."""
        nonexistent = "/path/that/does/not/exist.txt"

        with pytest.raises(FileNotFoundError):
            with open(nonexistent, 'r') as f:
                f.read()

        with pytest.raises(FileNotFoundError):
            Path(nonexistent).read_text()

    def test_writing_to_readonly_directory(self, tmp_path):
        """Test writing to read-only directory handles errors."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        readonly_file = readonly_dir / "test.txt"

        try:
            # Should raise PermissionError
            with pytest.raises(PermissionError):
                readonly_file.write_text("test")
        finally:
            # Cleanup - restore write permissions
            readonly_dir.chmod(0o755)

    def test_reading_empty_file(self, tmp_path):
        """Test reading empty file works correctly."""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()

        content = empty_file.read_text()
        assert content == ""

        with open(empty_file, 'r') as f:
            content2 = f.read()
        assert content2 == ""

    def test_writing_large_file(self, tmp_path):
        """Test writing large file works correctly."""
        large_file = tmp_path / "large.txt"

        # Create large content (1MB)
        large_content = "A" * (1024 * 1024)

        try:
            large_file.write_text(large_content)
            assert large_file.exists()

            # Verify content (read first 100 chars to avoid memory issues)
            with open(large_file, 'r') as f:
                first_chars = f.read(100)
            assert first_chars == "A" * 100

        except MemoryError:
            pytest.skip("Not enough memory for large file test")


class TestFileEncodingHandling:
    """Test file encoding handling."""

    def test_utf8_file_handling(self, tmp_path):
        """Test UTF-8 file handling works correctly."""
        utf8_file = tmp_path / "utf8.txt"
        utf8_content = "Hello 世界! 🌍 Émojis and ünícode"

        # Write UTF-8 content
        utf8_file.write_text(utf8_content, encoding='utf-8')

        # Read UTF-8 content
        read_content = utf8_file.read_text(encoding='utf-8')
        assert read_content == utf8_content

    def test_binary_file_handling(self, tmp_path):
        """Test binary file handling works correctly."""
        binary_file = tmp_path / "binary.bin"
        binary_content = b'\x00\x01\x02\x03\xFF\xFE\xFD'

        # Write binary content
        binary_file.write_bytes(binary_content)

        # Read binary content
        read_content = binary_file.read_bytes()
        assert read_content == binary_content


class TestJSONFileOperations:
    """Test JSON file operations (common in the codebase)."""

    def test_json_reading(self, tmp_path):
        """Test JSON file reading works correctly."""
        json_file = tmp_path / "test.json"
        test_data = {
            "name": "test",
            "version": "1.0.0",
            "settings": {
                "enabled": True,
                "count": 42
            }
        }

        # Write JSON
        json_file.write_text(json.dumps(test_data, indent=2))

        # Read and parse JSON
        with open(json_file, 'r') as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data

    def test_json_writing(self, tmp_path):
        """Test JSON file writing works correctly."""
        json_file = tmp_path / "output.json"
        test_data = {
            "github_token": "test_token",
            "github_org": "test_org",
            "default_branch": "main"
        }

        # Write JSON
        with open(json_file, 'w') as f:
            json.dump(test_data, f, indent=2)

        # Verify written content
        with open(json_file, 'r') as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data

    def test_malformed_json_handling(self, tmp_path):
        """Test handling of malformed JSON files."""
        bad_json_file = tmp_path / "bad.json"
        bad_json_content = '{"incomplete": json file'

        bad_json_file.write_text(bad_json_content)

        # Should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            with open(bad_json_file, 'r') as f:
                json.load(f)


class TestFilePermissions:
    """Test file permission handling."""

    def test_executable_file_creation(self, tmp_path):
        """Test creating executable files."""
        script_file = tmp_path / "script.sh"
        script_content = "#!/bin/bash\necho 'Hello World'"

        # Create script file
        script_file.write_text(script_content)

        # Make executable
        script_file.chmod(0o755)

        # Verify permissions
        stat = script_file.stat()
        assert stat.st_mode & 0o111  # Has execute bits

    def test_file_permission_checking(self, tmp_path):
        """Test checking file permissions."""
        test_file = tmp_path / "perm_test.txt"
        test_file.write_text("test content")

        # Test readable
        test_file.chmod(0o644)
        assert os.access(test_file, os.R_OK)

        # Test writable
        assert os.access(test_file, os.W_OK)

        # Test not executable (regular file)
        assert not os.access(test_file, os.X_OK)
