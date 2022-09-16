import TargetCurves
from EQConfig import EQConfig, RoomCorrectionConfig
from RewToGraphEq import get_graph_eq_str, create_eq

#basic calls
eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir")

eq_str = get_graph_eq_str(file_paths=["path/to/file1", "path/to/file2", "path/to/file3"])

#Custom target Curve

target_curve = TargetCurves.downwards_slope(factor=0.5)
eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir", target_curve=target_curve)

#Adjust EQConfig
eq_config = EQConfig(eq_res=256)
eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir", eq_config=eq_config)

eq_config = EQConfig(eq_res=256, eq_from=10, eq_to=22000)
eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir", eq_config=eq_config)

#Adjust room correction Config

rc_config = RoomCorrectionConfig(std_influence=9)  # Increase influence of std in the set of measurements
eq_config = EQConfig(room_correction_config=rc_config)
eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir", eq_config=eq_config)

def weighting(iteration, pos):
    return 1 / (1 + pos) ** iteration

rc_config = RoomCorrectionConfig(weighting_fun=weighting)  # Custom weighting function
eq_config = EQConfig(room_correction_config=rc_config)
get_graph_eq_str(measurements_dir="path/to/measurement/dir", eq_config=eq_config)

#Accessing the eq curve

rc_config = RoomCorrectionConfig(weighting_fun=weighting)  # Custom weighting function
eq_config = EQConfig(room_correction_config=rc_config)
eq = create_eq(measurements_dir="path/to/measurement/dir", eq_config=eq_config)
eq.draw()  # Draw the eq curve
eq(1000)  # evaluate eq curve at 1000 Hz

eq_str = eq_config.format(eq)





