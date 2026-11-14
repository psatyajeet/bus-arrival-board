import json
import unittest
from pathlib import Path

from muni_board.api import parse_511_time
from muni_board.core import PayloadError, build_board, minutes_until, parse_arrivals
from muni_board.render import render_matrix

FIXTURE = Path(__file__).parent / "fixtures" / "stop_monitoring.json"
NOW = parse_511_time("2025-01-02T00:00:00Z")


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.east = {
            "key": "row1",
            "agency": "DEMO",
            "stop_code": "90001",
            "route": "38",
            "label": "EAST",
        }

    def test_filters_sorts_deduplicates_and_prefers_arrival_time(self):
        arrivals = parse_arrivals(self.payload, self.east, NOW, parse_511_time, limit=2)

        self.assertEqual([4, 12], [minutes_until(item["eta_epoch"], NOW) for item in arrivals])
        self.assertEqual(["Library", "Central Station"], [item["destination"] for item in arrivals])
        self.assertTrue(all(item["route"] == "38" for item in arrivals))
        self.assertTrue(all(item["time_kind"] == "ExpectedArrivalTime" for item in arrivals))

    def test_accepts_direct_root_and_singleton_visit(self):
        visit = self.payload["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][
            "MonitoredStopVisit"
        ][1]
        direct = {"ServiceDelivery": {"StopMonitoringDelivery": {"MonitoredStopVisit": visit}}}

        arrivals = parse_arrivals(direct, self.east, NOW, parse_511_time)

        self.assertEqual(1, len(arrivals))
        self.assertEqual("Library", arrivals[0]["destination"])

    def test_empty_visits_are_valid(self):
        payload = {
            "Siri": {"ServiceDelivery": {"StopMonitoringDelivery": {"MonitoredStopVisit": []}}}
        }
        self.assertEqual([], parse_arrivals(payload, self.east, NOW, parse_511_time))

    def test_failed_semantic_status_raises(self):
        payload = {"Siri": {"ServiceDelivery": {"Status": "false"}}}
        with self.assertRaises(PayloadError):
            parse_arrivals(payload, self.east, NOW, parse_511_time)

    def test_matrix_model_contains_both_directions(self):
        second = dict(self.east, key="row2", label="WEST", stop_code="90002")
        settings = {"badge": "38", "title": "BUS", "stops": [self.east, second]}
        payloads = {"row1": self.payload, "row2": self.payload}
        board = build_board(payloads, settings, NOW, parse_511_time)

        output = render_matrix(board)

        self.assertIn("EAST  4  12", output)
        self.assertIn("WEST  4  12", output)

    def test_due_rounding(self):
        self.assertEqual(0, minutes_until(NOW + 59, NOW))
        self.assertEqual(1, minutes_until(NOW + 60, NOW))
        self.assertEqual(1, minutes_until(NOW + 119, NOW))
        self.assertEqual(2, minutes_until(NOW + 120, NOW))


if __name__ == "__main__":
    unittest.main()
