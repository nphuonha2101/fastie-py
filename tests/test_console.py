import unittest

from fastie.core.utils.console import FastieConsole


class ConsoleMarkupTests(unittest.TestCase):
    def test_message_markup_is_rendered_instead_of_printed_literally(self):
        message = FastieConsole._message_text(
            "[ INFO ]",
            "Starting [bold]http://127.0.0.1:8000[/bold]",
        )

        self.assertEqual(message.plain, " [ INFO ] Starting http://127.0.0.1:8000")
        self.assertNotIn("[bold]", message.plain)
        self.assertNotIn("[/bold]", message.plain)


if __name__ == "__main__":
    unittest.main()
