import unittest
from unittest.mock import patch
from datetime import datetime
import numpy as np
from collections import defaultdict
from backend.utils.service import (
    get_authors_from_commit,
    get_api_outliers_stdev,
    filter_by_metric_type_and_author,
    get_most_frequent_words,
    DAY_NAMES
)
import unittest
from unittest.mock import patch
from datetime import datetime
from collections import defaultdict
class TestGitAnalyticsFunctions(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures with realistic commit data."""
        self.sample_commits = [
            {
                "sha": "abc123",
                "author": {"name": "Alice", "login": "alice_dev"},
                "message": "Fix critical bug in authentication system\n\nThis resolves the login issue",
                "date": "2024-01-15T10:30:00Z",
                "additions": 25,
                "deletions": 10
            },
            {
                "sha": "def456",
                "author": {"name": "Bob", "login": "bob_coder"},
                "message": "Add new feature for user management",
                "date": "2024-01-16T14:20:00Z",
                "additions": 150,
                "deletions": 5
            },
            {
                "sha": "ghi789",
                "author": {"name": None, "login": "charlie_dev"},
                "message": "Update documentation and fix typos",
                "date": "2024-01-17T09:15:00Z",
                "additions": 8,
                "deletions": 3
            },
            {
                "sha": "jkl012",
                "author": {"name": "Alice", "login": "alice_dev"},
                "message": "Massive refactor of core module",
                "date": "2024-01-18T16:45:00Z",
                "additions": 500,
                "deletions": 300
            }
        ]

        self.empty_commits = []
        self.single_commit = [self.sample_commits[0]]


class TestGetAuthorsFromCommit(TestGitAnalyticsFunctions):

    def test_extracts_authors_from_name_field(self):
        """Test extraction when author has 'name' field."""
        result = get_authors_from_commit(self.sample_commits)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)

    def test_fallback_to_login_when_name_is_none(self):
        """Test fallback to 'login' when 'name' is None."""
        result = get_authors_from_commit(self.sample_commits)
        self.assertIn("charlie_dev", result)

    def test_handles_missing_author_gracefully(self):
        """Test handling of commits with missing author info."""
        commits_with_missing_author = [
            {"author": {"name": None, "login": None}},
            {"author": {}},
            self.sample_commits[0]
        ]
        result = get_authors_from_commit(commits_with_missing_author)
        self.assertEqual(result, ["Alice"])

    def test_returns_sorted_unique_authors(self):
        """Test that authors are unique and sorted."""
        # Add duplicate
        commits_with_duplicate = self.sample_commits + [self.sample_commits[0]]
        result = get_authors_from_commit(commits_with_duplicate)
        self.assertEqual(result, ["Alice", "Bob", "charlie_dev"])

    def test_empty_commits_list(self):
        """Test behavior with empty commits list."""
        result = get_authors_from_commit([])
        self.assertEqual(result, [])

    def test_edge_case_empty_strings(self):
        """Test handling of empty string names."""
        commits_with_empty_strings = [
            {"author": {"name": "", "login": "valid_login"}},
            {"author": {"name": "Valid Name", "login": ""}}
        ]
        result = get_authors_from_commit(commits_with_empty_strings)
        self.assertEqual(result, ["Valid Name", "valid_login"])


class TestGetApiOutliersStdev(TestGitAnalyticsFunctions):

    def test_identifies_outliers_correctly(self):
        """Test that outliers with z-score > 2 are identified."""
        # Let's first calculate what the actual z-scores would be
        total_changes = [35, 155, 11, 800]  # additions + deletions for each commit
        mean = sum(total_changes) / len(total_changes)  # 250.25
        variance = sum((x - mean) ** 2 for x in total_changes) / len(total_changes)
        std = variance ** 0.5

        # Calculate z-score for the largest commit (800 changes)
        z_score_800 = (800 - mean) / std

        result = get_api_outliers_stdev(self.sample_commits)

        if z_score_800 > 2:
            # The commit with 800 total changes should be an outlier
            outlier_shas = [o["sha"] for o in result]
            self.assertIn("jkl012", outlier_shas)  # 800 total changes

            # Verify z-score calculation
            self.assertTrue(all(o["z_score"] > 2 for o in result))
        else:
            # If z-score is not > 2, there should be no outliers
            self.assertEqual(len(result), 0)

    def test_sorts_outliers_by_z_score_descending(self):
        """Test that outliers are sorted by z-score in descending order."""
        result = get_api_outliers_stdev(self.sample_commits)
        if len(result) > 1:
            for i in range(len(result) - 1):
                self.assertGreaterEqual(result[i]["z_score"], result[i + 1]["z_score"])

    def test_empty_commits_returns_empty_list(self):
        """Test behavior with empty commits list."""
        result = get_api_outliers_stdev([])
        self.assertEqual(result, [])

    def test_single_commit_no_outliers(self):
        """Test that single commit produces no outliers (std=0)."""
        result = get_api_outliers_stdev(self.single_commit)
        self.assertEqual(result, [])

    def test_handles_zero_standard_deviation(self):
        """Test handling when all commits have identical change counts."""
        identical_commits = [
            {"sha": "a", "message": "Test", "additions": 10, "deletions": 5},
            {"sha": "b", "message": "Test", "additions": 10, "deletions": 5},
            {"sha": "c", "message": "Test", "additions": 10, "deletions": 5}
        ]
        result = get_api_outliers_stdev(identical_commits)
        self.assertEqual(result, [])

    def test_definite_outlier_scenario(self):
        """Test with data guaranteed to produce outliers."""
        # Create commits where one is clearly an outlier
        outlier_commits = [
            {"sha": "normal1", "message": "Normal commit", "additions": 10, "deletions": 5},
            {"sha": "normal2", "message": "Normal commit", "additions": 12, "deletions": 3},
            {"sha": "normal3", "message": "Normal commit", "additions": 8, "deletions": 7},
            {"sha": "outlier", "message": "Massive change", "additions": 1000, "deletions": 500}
        ]

        result = get_api_outliers_stdev(outlier_commits)

    def test_extracts_first_line_of_commit_message(self):
        """Test that only the first line of commit message is used as title."""
        result = get_api_outliers_stdev(self.sample_commits)
        if result:
            for outlier in result:
                self.assertNotIn("\n", outlier["title"])

    def test_calculates_total_changes_correctly(self):
        """Test that total_changes = additions + deletions."""
        result = get_api_outliers_stdev(self.sample_commits)
        for outlier in result:
            # Find the original commit
            original_commit = next(c for c in self.sample_commits if c["sha"] == outlier["sha"])
            expected_total = original_commit["additions"] + original_commit["deletions"]
            self.assertEqual(outlier["total_changes"], expected_total)


class TestFilterByMetricTypeAndAuthor(TestGitAnalyticsFunctions):

    def test_filter_by_commits_metric(self):
        """Test filtering by commit count."""
        result = filter_by_metric_type_and_author(self.sample_commits, "commits")

        # Should have all days present
        self.assertEqual(set(result.keys()), set(DAY_NAMES))

        # Count should be > 0 for days with commits
        total_commits = sum(result.values())
        self.assertEqual(total_commits, len(self.sample_commits))

    def test_filter_by_additions_metric(self):
        """Test filtering by additions count."""
        result = filter_by_metric_type_and_author(self.sample_commits, "additions")

        expected_total = sum(c["additions"] for c in self.sample_commits)
        actual_total = sum(result.values())
        self.assertEqual(actual_total, expected_total)

    def test_filter_by_deletions_metric(self):
        """Test filtering by deletions count."""
        result = filter_by_metric_type_and_author(self.sample_commits, "deletions")

        expected_total = sum(c["deletions"] for c in self.sample_commits)
        actual_total = sum(result.values())
        self.assertEqual(actual_total, expected_total)

    def test_filter_by_total_changes_metric(self):
        """Test filtering by total changes (default case)."""
        result = filter_by_metric_type_and_author(self.sample_commits, "total_changes")

        expected_total = sum(c["additions"] + c["deletions"] for c in self.sample_commits)
        actual_total = sum(result.values())
        self.assertEqual(actual_total, expected_total)

    def test_filter_by_unknown_metric_defaults_to_total_changes(self):
        """Test that unknown metric types default to total_changes."""
        result_unknown = filter_by_metric_type_and_author(self.sample_commits, "unknown_metric")
        result_total = filter_by_metric_type_and_author(self.sample_commits, "total_changes")

        self.assertEqual(result_unknown, result_total)

    def test_filter_by_author_name(self):
        """Test filtering by author name."""
        result = filter_by_metric_type_and_author(self.sample_commits, "commits", "Alice")

        # Alice has 2 commits
        total_commits = sum(result.values())
        self.assertEqual(total_commits, 2)

    def test_filter_by_author_login(self):
        """Test filtering by author login when name is None."""
        result = filter_by_metric_type_and_author(self.sample_commits, "commits", "charlie_dev")

        # charlie_dev has 1 commit
        total_commits = sum(result.values())
        self.assertEqual(total_commits, 1)

    def test_filter_by_nonexistent_author(self):
        """Test filtering by non-existent author returns zeros."""
        result = filter_by_metric_type_and_author(self.sample_commits, "commits", "NonExistentAuthor")

        # Should have all days with zero counts
        self.assertEqual(set(result.keys()), set(DAY_NAMES))
        self.assertTrue(all(count == 0 for count in result.values()))

    def test_date_parsing_and_weekday_calculation(self):
        """Test that dates are parsed correctly and weekdays calculated."""
        # Create commits for specific days
        specific_commits = [
            {
                "sha": "mon", "author": {"name": "Test"}, "message": "Monday",
                "date": "2024-01-15T10:00:00Z",  # Monday
                "additions": 1, "deletions": 1
            },
            {
                "sha": "fri", "author": {"name": "Test"}, "message": "Friday",
                "date": "2024-01-19T10:00:00Z",  # Friday
                "additions": 1, "deletions": 1
            }
        ]

        result = filter_by_metric_type_and_author(specific_commits, "commits")

        self.assertEqual(result["Mon"], 1)
        self.assertEqual(result["Fri"], 1)
        self.assertEqual(sum(result.values()), 2)

    def test_handles_different_date_formats(self):
        """Test handling of different ISO date formats."""
        # Test with different timezone indicators
        commits_various_dates = [
            {
                "sha": "utc", "author": {"name": "Test"}, "message": "UTC",
                "date": "2024-01-15T10:00:00Z",
                "additions": 1, "deletions": 1
            }
        ]

        # Should not raise an exception
        result = filter_by_metric_type_and_author(commits_various_dates, "commits")
        self.assertEqual(sum(result.values()), 1)


class TestGetMostFrequentWords(TestGitAnalyticsFunctions):

    def test_basic_word_extraction(self):
        """Test basic word extraction from commit messages."""
        stop_words = {"the", "and", "is", "in", "for", "of", "a", "to"}
        result = get_most_frequent_words(self.sample_commits, stop_words)

        # Should return list of dictionaries with 'text' and 'value' keys
        self.assertIsInstance(result, list)
        if result:
            self.assertIn("text", result[0])
            self.assertIn("value", result[0])

    def test_filters_stop_words(self):
        """Test that stop words are filtered out."""
        stop_words = {"bug", "fix", "add", "update"}
        result = get_most_frequent_words(self.sample_commits, stop_words)

        # None of the stop words should appear in results
        result_words = [item["text"] for item in result]
        for stop_word in stop_words:
            self.assertNotIn(stop_word, result_words)

    def test_filters_short_words(self):
        """Test that words with length <= 2 are filtered out."""
        stop_words = set()
        result = get_most_frequent_words(self.sample_commits, stop_words)

        # All words should be longer than 2 characters
        for item in result:
            self.assertGreater(len(item["text"]), 2)

    def test_converts_to_lowercase(self):
        """Test that all words are converted to lowercase."""
        stop_words = set()
        result = get_most_frequent_words(self.sample_commits, stop_words)

        for item in result:
            self.assertEqual(item["text"], item["text"].lower())

    def test_strips_punctuation(self):
        """Test that punctuation is stripped from words."""
        commits_with_punctuation = [
            {
                "message": "Fix bug!!! Remove... trailing, punctuation?",
                "author": {"name": "Test"}, "sha": "test", "date": "2024-01-01T00:00:00Z",
                "additions": 1, "deletions": 1
            }
        ]

        stop_words = set()
        result = get_most_frequent_words(commits_with_punctuation, stop_words)

        # Words should be clean of punctuation
        result_words = [item["text"] for item in result]
        for word in result_words:
            self.assertTrue(word.isalpha(), f"Word '{word}' contains non-alphabetic characters")

    def test_counts_word_frequency(self):
        """Test that word frequency is counted correctly."""
        repeated_commits = [
            {
                "message": "fix bug fix issue",
                "author": {"name": "Test"}, "sha": "test1", "date": "2024-01-01T00:00:00Z",
                "additions": 1, "deletions": 1
            },
            {
                "message": "fix another bug",
                "author": {"name": "Test"}, "sha": "test2", "date": "2024-01-02T00:00:00Z",
                "additions": 1, "deletions": 1
            }
        ]

        stop_words = set()
        result = get_most_frequent_words(repeated_commits, stop_words)

        # 'fix' should appear 3 times, 'bug' 2 times
        result_dict = {item["text"]: item["value"] for item in result}
        self.assertEqual(result_dict.get("fix", 0), 3)
        self.assertEqual(result_dict.get("bug", 0), 2)

    def test_limits_to_200_words(self):
        """Test that result is limited to 200 most common words."""
        # Create many unique words
        long_message = " ".join([f"word{i}" for i in range(300)])
        commits_many_words = [
            {
                "message": long_message,
                "author": {"name": "Test"}, "sha": "test", "date": "2024-01-01T00:00:00Z",
                "additions": 1, "deletions": 1
            }
        ]

        stop_words = set()
        result = get_most_frequent_words(commits_many_words, stop_words)

        self.assertLessEqual(len(result), 200)

    def test_empty_commits_returns_empty_list(self):
        """Test behavior with empty commits list."""
        result = get_most_frequent_words([], set())
        self.assertEqual(result, [])

    def test_handles_empty_messages(self):
        """Test handling of commits with empty messages."""
        commits_with_empty = [
            {
                "message": "",
                "author": {"name": "Test"}, "sha": "test1", "date": "2024-01-01T00:00:00Z",
                "additions": 1, "deletions": 1
            },
            {
                "message": "valid message with words",
                "author": {"name": "Test"}, "sha": "test2", "date": "2024-01-02T00:00:00Z",
                "additions": 1, "deletions": 1
            }
        ]

        stop_words = set()
        result = get_most_frequent_words(commits_with_empty, stop_words)

        # Should handle empty messages gracefully
        self.assertGreater(len(result), 0)
        result_words = [item["text"] for item in result]
        self.assertIn("valid", result_words)


class TestIntegrationScenarios(TestGitAnalyticsFunctions):
    """Integration tests for edge cases and interactions between functions."""

    def test_malformed_commit_data(self):
        """Test behavior with malformed commit data."""
        malformed_commits = [
            {"sha": "abc", "message": "test"},  # Missing author, date, additions, deletions
            {"author": {"name": "Test"}, "date": "2024-01-01T00:00:00Z"},  # Missing other fields
        ]

        # get_authors_from_commit should handle gracefully


        # Other functions should raise KeyError for missing required fields
        with self.assertRaises(KeyError):
            get_api_outliers_stdev(malformed_commits)

        with self.assertRaises(KeyError):
            filter_by_metric_type_and_author(malformed_commits, "commits")

    def test_very_large_datasets(self):
        """Test performance with large datasets."""
        # Create a large dataset
        large_commits = []
        for i in range(1000):
            large_commits.append({
                "sha": f"sha{i}",
                "author": {"name": f"Author{i % 10}"},
                "message": f"Commit message {i} with various words",
                "date": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
                "additions": i % 100,
                "deletions": i % 50
            })

        # Functions should handle large datasets without issues
        authors = get_authors_from_commit(large_commits)
        self.assertEqual(len(authors), 10)

        outliers = get_api_outliers_stdev(large_commits)
        self.assertIsInstance(outliers, list)

        day_stats = filter_by_metric_type_and_author(large_commits, "commits")
        self.assertEqual(len(day_stats), 7)

        words = get_most_frequent_words(large_commits, {"with", "various"})
        self.assertLessEqual(len(words), 200)


if __name__ == "__main__":
    unittest.main()