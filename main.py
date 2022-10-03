import EQConfig
import TargetCurves
from RewToGraphEq import create_eq, format_eq_str
d = EQConfig.detail()
eq = create_eq(
    target_curve=TargetCurves.downwards_slope(0.5),
    measurements_dir="./example measurements/lz",
    # file_paths=["C:\\Users\Lukas\\Documents\\Measurements\\Export\\BPHS\\1.txt"],
    eq_config=EQConfig.wavelet()
)
eqq = format_eq_str(eq, EQConfig.wavelet())
eq.draw("Equalizer")
ee = 1
