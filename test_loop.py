import pandas as pd
import matplotlib.pyplot as plt


if __name__ == '__main__':
    loop_times: pd.DataFrame = pd.read_csv('Loop A.csv').set_index('Time Tag')
    loop_times.index = pd.to_datetime(loop_times.index, format='mixed')
    print(loop_times)

    day_loop = loop_times.groupby(loop_times.index.date).sum()
    print(day_loop)
    day_loop.plot()
    plt.show()

    print('Do it per day type!')
