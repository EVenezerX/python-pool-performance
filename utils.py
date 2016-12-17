import psutil
import time
import os


def lower_bound(sequence, bound=0):
    """
    Maps the given sequence such that the data points
    are greater than or equal to the bound.
    """
    return map(
        lambda point:
            point if point > bound
            else bound,
        sequence
    )


def lower_bound_immediate(sequence, bound=0):
    return list(lower_bound(sequence, bound=bound))


def power_range(start, stop=None, step=2):
    """
    Generates a sequence starting at start and multiplying
    consecutive numbers by step until stop is reached.
    """
    if stop is None:
        stop = start
        start = 1
    assert start > 0 and start < stop and step > 1
    while start < stop:
        yield start
        start *= step


def time_it(func):
    """
    Run a function and return the time it took to execute in seconds.
    """
    def timed_func(*args, **kwargs):
        start_time = time.time()
        func(*args, **kwargs)
        end_time = time.time()
        return end_time - start_time
    timed_func.__name__ = func.__name__
    return timed_func


def invert_array_of_dicts(array, keys):
    # TODO: streamline this
    result = {}
    for item in array:
        for key in keys:
            if key not in result:
                result[key] = []
            result[key].append(item[key])
    return result


def plot_dict(name_to_data_mapping, *args, **kwargs):
    """Creates a plot of the given data in any order."""
    return plot_tuple_array(name_to_data_mapping.items(), *args, **kwargs)


def plot_tuple_array(name_to_data_mapping, x_label, y_label,
                     custom_x_label=None, custom_y_label=None, y_mapping=None):
    """Creates a plot of the given data in the order it is given."""
    from matplotlib import pyplot as plt

    def plot_inner_arr(name, inverted_array):
        data = invert_array_of_dicts(inverted_array, inverted_array[0].keys())
        y_data = data[y_label]
        if y_mapping is not None:
            y_data = y_mapping(y_data)
        return plt.plot(data[x_label], y_data, label=name)[0]

    plots = list(map(
        lambda result_tuple: plot_inner_arr(*result_tuple),
        name_to_data_mapping.items()
    ))
    plt.legend(handles=plots, fontsize='small', loc='best')
    if custom_x_label is None:
        plt.xlabel(x_label)
    else:
        plt.xlabel(custom_x_label)
    if custom_y_label is None:
        plt.ylabel(y_label)
    else:
        plt.ylabel(custom_y_label)
    return plt


def memory_percent():
    current_process = psutil.Process(os.getpid())
    return current_process.memory_percent() + sum(
        map(
            psutil.Process.memory_percent,
            current_process.children(recursive=True)
        )
    )
