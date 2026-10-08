import unittest

from rdp_cua.coordinates import denormalize_coordinate, normalize_coordinate


class CoordinateTests(unittest.TestCase):
    def test_center_maps_to_center(self) -> None:
        self.assertEqual(denormalize_coordinate((500, 500), 1920, 1080), (960, 540))

    def test_round_trip_edges(self) -> None:
        self.assertEqual(normalize_coordinate((0, 0), 1920, 1080), (0, 0))
        self.assertEqual(normalize_coordinate((1919, 1079), 1920, 1080), (1000, 1000))

    def test_rejects_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            denormalize_coordinate((1001, 500), 1920, 1080)


if __name__ == "__main__":
    unittest.main()

