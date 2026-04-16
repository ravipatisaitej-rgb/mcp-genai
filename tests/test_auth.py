"""
Simple Authentication Tests
Tests the basic user authentication system
"""

import sys
import unittest
import os
import tempfile
from datetime import datetime

# Add project to path
sys.path.insert(0, '/Users/rst/Documents/GitHub/mcp-genai')

from auth import SimpleAuth, User, require_auth


class TestSimpleAuth(unittest.TestCase):
    """Test simple authentication system"""

    def setUp(self):
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.auth = SimpleAuth(self.temp_file.name)

    def tearDown(self):
        # Clean up temp file
        try:
            os.unlink(self.temp_file.name)
        except:
            pass

    def test_create_user(self):
        """Test user creation"""
        success = self.auth.create_user("testuser", "test@example.com", "Test User")
        self.assertTrue(success)

        user = self.auth.get_user("testuser")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.full_name, "Test User")

    def test_create_duplicate_user(self):
        """Test creating duplicate user fails"""
        self.auth.create_user("testuser")
        success = self.auth.create_user("testuser")
        self.assertFalse(success)

    def test_authenticate_valid_user(self):
        """Test authentication of valid user"""
        self.auth.create_user("testuser")
        success, token = self.auth.authenticate("testuser")
        self.assertTrue(success)
        self.assertIsNotNone(token)

    def test_authenticate_invalid_user(self):
        """Test authentication of invalid user fails"""
        success, token = self.auth.authenticate("nonexistent")
        self.assertFalse(success)
        self.assertIsNone(token)

    def test_validate_session(self):
        """Test session validation"""
        self.auth.create_user("testuser")
        success, token = self.auth.authenticate("testuser")
        self.assertTrue(success)

        valid, username = self.auth.validate_session(token)
        self.assertTrue(valid)
        self.assertEqual(username, "testuser")

    def test_logout(self):
        """Test logout"""
        self.auth.create_user("testuser")
        success, token = self.auth.authenticate("testuser")
        self.assertTrue(success)

        # Logout
        logged_out = self.auth.logout(token)
        self.assertTrue(logged_out)

        # Session should be invalid now
        valid, username = self.auth.validate_session(token)
        self.assertFalse(valid)

    def test_update_user(self):
        """Test user update"""
        self.auth.create_user("testuser", "old@example.com")
        success = self.auth.update_user("testuser", email="new@example.com", full_name="New Name")
        self.assertTrue(success)

        user = self.auth.get_user("testuser")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.full_name, "New Name")

    def test_delete_user(self):
        """Test user deletion"""
        self.auth.create_user("testuser")
        success = self.auth.delete_user("testuser")
        self.assertTrue(success)

        user = self.auth.get_user("testuser")
        self.assertIsNone(user)

    def test_list_users(self):
        """Test listing users"""
        self.auth.create_user("user1", "user1@example.com")
        self.auth.create_user("user2", "user2@example.com")

        users = self.auth.list_users()
        self.assertEqual(len(users), 2)
        self.assertIn("user1", users)
        self.assertIn("user2", users)


class TestUser(unittest.TestCase):
    """Test User model"""

    def test_user_creation(self):
        """Test user object creation"""
        user = User("testuser", "test@example.com", "Test User")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.full_name, "Test User")
        self.assertIsNotNone(user.created_at)

    def test_user_to_dict(self):
        """Test user serialization"""
        user = User("testuser", "test@example.com", "Test User")
        data = user.to_dict()
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["full_name"], "Test User")
        self.assertIn("created_at", data)

    def test_user_from_dict(self):
        """Test user deserialization"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "created_at": "2024-01-01T00:00:00",
            "last_login": None
        }
        user = User.from_dict(data)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.full_name, "Test User")


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSimpleAuth))
    suite.addTests(loader.loadTestsFromTestCase(TestUser))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)