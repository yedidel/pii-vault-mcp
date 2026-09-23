import unittest

from vault_sim import _is_approval_choice


class ApprovalChoiceTest(unittest.TestCase):
    def test_accepts_y_variants(self) -> None:
        self.assertTrue(_is_approval_choice("y"))
        self.assertTrue(_is_approval_choice("Y"))
        self.assertTrue(_is_approval_choice(" yes \r\n"))
        self.assertTrue(_is_approval_choice("y\r"))

    def test_rejects_n_and_empty(self) -> None:
        self.assertFalse(_is_approval_choice("n"))
        self.assertFalse(_is_approval_choice(""))
        self.assertFalse(_is_approval_choice("no"))
        self.assertFalse(_is_approval_choice("maybe"))


if __name__ == "__main__":
    unittest.main()
