'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import weather
import define

if __name__ == '__main__':
    parameters_file_name = 'ChaProEV.toml'
    print('Do solar panel efficiency')
    print('Multiple runs in output files/DB')
    print('Avoid swap by arranging before? And explain/improve in all hourly')
    print('Clarrify what theperature efficiency of vehicles actually is')
    print('Test leg.electricity_use_kWh')
    print('Implement road and hour in day factors')
    print('Go through class definitions (espcially Trip')
    weather.setup_weather(parameters_file_name)
    legs, vehicles, locations, trips = define.declare_all_instances(
        parameters_file_name)
