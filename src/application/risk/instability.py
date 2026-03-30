import numpy as np

def instability_risk(speed):
    return np.std([speed]) / (speed + 1e-5) if speed > 0 else 0