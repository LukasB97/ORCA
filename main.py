import EQConfig
import TargetCurves
from RewToGraphEq import create_eq


eq = create_eq(
    target_curve=TargetCurves.downwards_slope(0.5),
    measurements_dir="./example measurements/lz",
    # file_paths=["C:\\Users\Lukas\\Documents\\Measurements\\Export\\BPHS\\1.txt"],
    eq_config=EQConfig.wavelet()
)
eqq = EQConfig.wavelet().format(eq)
eq.draw()
ee = 1
