import json

SYRINGE_ML_PER_MM = 30/78
SYRINGE_LARGE_ML_PER_MM = 50 / 98
SHAFT_LEAD_MM = 0.5 
STEPS_PER_REVOLUTION = 2038 // 4
STEPS_PER_REVOLUTION_BULLDOG = 1600
HAHRDWARE_CONFIG_FILE = 'configs/hardware_config.json'
EXPERIMENT_CONFIG_FILE = 'configs/experiment_config.json'


def calculate_vol_per_step(steps_per_revolution, shaft_lead_mm, syringe_ml_per_mm):
    """ Calculate the volume of liquid dispenced per *full rotation* of the stepper rotor."""
    angle_per_step = 1 / steps_per_revolution # fraction of the full rotation per step 
    return angle_per_step * shaft_lead_mm * syringe_ml_per_mm 
 
class HardwareConfig: 

    def __init__(self, config):
        self._config = config
        self.incubator_stirrer_top_speed_frac = config['incubator_stirrer_top_speed_frac']
        self.lagoon_stirrer_top_speed_frac = config['lagoon_stirrer_top_speed_frac']
        self.pump_medium_to_incubator_speed_frac = config['pumps_speed_frac']
        self.pump_incubator_to_lagoon_speed_frac = config['pumps_speed_frac']
        self.pump_incubator_to_lagoon_burst_vol_ml = config['pump_incubator_to_lagoon_burst_vol_ml']
        self.pump_incubator_to_lagoon_burst_duration_s = config['pump_incubator_to_lagoon_burst_duration_s']
        self.pump_lagoon_to_waste_burst_duration_s = config['pump_lagoon_to_waste_burst_duration_s']
        self.induction_ml_per_step = config['induction_ml_per_step']
        self.stepper_direction = config['stepper_direction'] # 1 or -1

    
    def incubator_od_convert(self, measurement): 
        intercept, slope = self._config['incubator_od']['intercept'], self._config['incubator_od']['slope']
        return slope * measurement + intercept
    
    def incubator_temp_convert(self, measurement): 
        intercept, slope = self._config['incubator_temp']['intercept'], self._config['incubator_temp']['slope']
        return slope * measurement + intercept
    
    def lagoon_temp_convert(self, measurement): 
        intercept, slope = self._config['lagoon_temp']['intercept'], self._config['lagoon_temp']['slope']
        return slope * measurement + intercept
     

def default_config() -> HardwareConfig:
    cfg =  {
        'incubator_od': {'intercept': -14.706894907315895, 'slope': 0.00024892679660541},
        'incubator_temp': {'intercept': 0, 'slope': 1},
        'lagoon_temp': {'intercept': 0, 'slope': 1},
        'incubator_stirrer_top_speed_frac': 0.24,
        'lagoon_stirrer_top_speed_frac': 0.4,
        'pumps_speed_frac':  0.4,
        'pump_incubator_to_lagoon_burst_vol_ml': 0.165,
        'pump_incubator_to_lagoon_burst_duration_s': 0.5,
        'pump_lagoon_to_waste_burst_duration_s': 0.6,
        'induction_ml_per_step': calculate_vol_per_step(STEPS_PER_REVOLUTION_BULLDOG, SHAFT_LEAD_MM, SYRINGE_LARGE_ML_PER_MM),
        'stepper_direction': 1
    } 
    return HardwareConfig(cfg)

def load_hardware_config(file = HAHRDWARE_CONFIG_FILE) -> HardwareConfig: 
    with open(file, 'r') as f: 
        return HardwareConfig(json.load(f))
    

