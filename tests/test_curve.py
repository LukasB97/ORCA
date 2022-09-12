import unittest


class CurveTestCase(unittest.TestCase):


    def test_n_n_mul(self):
        a = Matrix(
            [
                [6, 345, 237, 464],
                [3, 8, 2, 7],
                [5, -54, 1, 5],
                [5, 1, 8, 4]
            ]
        )
        b = Matrix(
            [
                [6, -7, 46, 4],
                [3, -5, 2, 7],
                [5, 4, -1, 55],
                [5, -1, 8, 8]
            ]
        )
        self.assertEqual(a * b, Matrix(
            [
                [4576, -1283, 4441, 19186],
                [87, -60, 208, 234],
                [-102, 234, 161, -263],
                [93, -12, 256, 499]
            ]
        ))
        self.assertEqual(
            b * a,
            Matrix(
                [
                    [265, -466, 1486, 2981],
                    [48, 894, 759, 1395],
                    [312, 1866, 1632, 2563],
                    [107, 1293, 1255, 2385]
                ]
            )
        )


if __name__ == '__main__':
    unittest.main()
