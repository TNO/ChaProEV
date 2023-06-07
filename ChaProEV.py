'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import weather

if __name__ == '__main__':
    parameters_file_name = 'ChaProEV.toml'
    run_weather_data = weather.get_run_weather_data(parameters_file_name)
    print(run_weather_data)
