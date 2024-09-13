import json

SYRINGE_ML_PER_MM = 30/78
SYRINGE_LARGE_ML_PER_MM = 50 / 98
SHAFT_LEAD_MM = 2 # x-displacement of the stepper shaft per rotation.
STEPS_PER_REVOLUTION = 2038 // 4
STEPS_PER_REVOLUTION_BULLDOG = 1600
HAHRDWARE_CONFIG_FILE = 'configs/hardware_config.json'
EXPERIMENT_CONFIG_FILE = 'configs/experiment_config.json'


def calculate_vol_per_step(steps_per_revolution, shaft_lead_mm, syringe_ml_per_mm):
    """ Calculate the volume of liquid dispenced per step of the stepper rotor."""
    angle_per_step = 1 / steps_per_revolution # angle in fraction of a full revolution.
    displacement_per_step = angle_per_step * shaft_lead_mm
    volume_per_step = displacement_per_step * syringe_ml_per_mm
    return volume_per_step
    
 
class IncubatorConfig:
    def __init__(self, config):
        self._config = config
        self.od_intercept = config['od']['intercept']
        self.od_slope = config['od']['slope']
        self.temp_intercept = config['temp']['intercept']
        self.temp_slope = config['temp']['slope']
        self.stirrer_top_speed_frac = config['stirrer_top_speed_frac']
    
    def od_convert(self, measurement): 
        return self.od_slope * measurement + self.od_intercept
    
    def temp_convert(self, measurement): 
        return self.temp_slope * measurement + self.temp_intercept
    
class HardwareConfig: 

    def __init__(self, config):
        self._config = config
        self.inc_left = IncubatorConfig(config['inc_left'])
        self.inc_right = IncubatorConfig(config['inc_right'])
        self.lagoon_stirrer_top_speed_frac = config['lagoon_stirrer_top_speed_frac']
        self.pump_medium_to_incubator_speed_frac = config['pumps_speed_frac']
        self.pump_lagoon_to_waste_burst_duration_s = config['pump_lagoon_to_waste_burst_duration_s']
        self.induction_stepper_ml_per_step = config['induction_stepper_ml_per_step']
        self.induction_stepper_direction = config['induction_stepper_direction'] # 1 or -1
        self.bact_stepper_ml_per_step = config['bact_stepper_ml_per_step']

    def lagoon_temp_convert(self, measurement): 
        intercept, slope = self._config['lagoon_temp']['intercept'], self._config['lagoon_temp']['slope']
        return slope * measurement + intercept
     

def default_config() -> HardwareConfig:
    cfg =  {
        'inc_left': {
            'od': {'intercept': -14.706894907315895, 'slope': 0.00024892679660541},
            'temp': {'intercept': 0, 'slope': 1},
            'stirrer_top_speed_frac': 0.24,
        },
        'inc_right': {
            'od': {'intercept': -14.706894907315895, 'slope': 0.00024892679660541},
            'temp': {'intercept': 0, 'slope': 1},
            'stirrer_top_speed_frac': 0.24,
        },
        'lagoon_temp': {'intercept': 0, 'slope': 1},
        'lagoon_stirrer_top_speed_frac': 0.4,
        'pumps_speed_frac':  0.4,
        'pump_lagoon_to_waste_burst_duration_s': 0.6,
        'induction_stepper_direction': 1,
        'induction_stepper_ml_per_step': calculate_vol_per_step(STEPS_PER_REVOLUTION_BULLDOG, SHAFT_LEAD_MM, SYRINGE_LARGE_ML_PER_MM),
        'bact_stepper_ml_per_step': 0.0001
    } 
    return HardwareConfig(cfg)

def load_hardware_config(file = HAHRDWARE_CONFIG_FILE) -> HardwareConfig: 
    with open(file, 'r') as f: 
        return HardwareConfig(json.load(f))
    

