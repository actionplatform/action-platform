import logging
import sys

from action_platform.core.process import stream
from action_platform.logging import attach, capture, emit, logger
from action_platform.testing.fixtures import TempCase


class LogSinkTest(TempCase):
    def test_records_and_emits_reach_the_sink_only_inside_capture(self):
        seen: list[str] = []

        emit("outside")
        logger.info("outside too")

        with capture(seen.append):
            emit("one\n")
            logger.info("two %s", 2)
            logger.debug("hidden")

        emit("after")

        self.assertEqual(seen, ["one", "two 2"])

    def test_another_logger_can_be_attached(self):
        seen: list[str] = []
        attach("apx_test")
        attach("apx_test")

        with capture(seen.append):
            logging.getLogger("apx_test").warning("careful")

        self.assertEqual(seen, ["careful"])

    def test_stream_emits_every_line_and_keeps_the_tail(self):
        seen: list[str] = []
        code = "import sys\nfor i in range(5): print('out', i)\nprint('err', file=sys.stderr)\nsys.exit(3)"

        with capture(seen.append):
            result = stream([sys.executable, "-u", "-c", code], tail=2)

        self.assertEqual(result.returncode, 3)
        self.assertFalse(result.ok)
        self.assertTrue(seen[0].startswith("$ "))
        self.assertEqual(seen[1:6], [f"out {i}" for i in range(5)])
        self.assertIn("err", seen)
        self.assertEqual(result.output.splitlines()[-1], "err")
        self.assertEqual(len(result.output.splitlines()), 2)
