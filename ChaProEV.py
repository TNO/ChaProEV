'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import weather

if __name__ == '__main__':
    parameters_file_name = 'ChaProEV.toml'
    print('Do solar panel efficiency')
    print('Multiple runs in output files/DB')
    print('Avoid swap by arranging before? And explain/improve in all hourly')
    weather.setup_weather(parameters_file_name)
