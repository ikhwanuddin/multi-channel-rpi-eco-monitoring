#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactive setup script for multi-channel Raspberry Pi ecosystem monitoring.
This script generates a config.json file based on user input.
"""

import json
import os
import sys
import sensors
import inspect


def config_parse(opt, cnfg):
    """
    Method to parse a config option (dictionary with name, prompt, type, optional default,
    optional list of valid values), validate and append the choice to an existing
    config dictionary.

    Parameters:
        opt: A config option dictionary.
        cnfg: The config dictionary to extend.
    """

    if 'default' in opt.keys():
        opt['dft_str'] = '\nPress return to accept default value [{}]'.format(opt['default'])
    else:
        opt['dft_str'] = ""

    if 'valid' in opt.keys():
        opt['vld_str'] = ', valid options: '
        vld_opts = ', '.join([str(vl) for vl in opt['valid']])
        opt['vld_str'] += vld_opts
    else:
        opt['vld_str'] = ""

    valid_choice = False
    target_type = opt['type']

    print('{prompt} [{name}{vld_str}]{dft_str}'.format(**opt))

    while not valid_choice:
        try:
            value = input()  # Changed from raw_input() for Python 3 compatibility
        except NameError:
            value = raw_input()  # Fallback for Python 2
        try:
            # check for input and handle defaults
            if value == '' and 'default' in opt.keys():
                value = opt['default']
                valid_choice = True
            elif value == '' and 'default' not in opt.keys():
                print('No value entered and no default value is set')
                continue

            # need to be a little careful here in parsing raw inputs because
            # bool() convert anything but an empty string to True, so handle
            # those differently
            if target_type.__name__ == 'bool' and not isinstance(value, bool):
                if value.lower() in ['t', 'true']:
                    value = True
                    valid_choice = True
                elif value.lower() in ['f', 'false']:
                    value = False
                    valid_choice = True
                else:
                    print('Value not recognized as true or false')
                    continue
            else:
                try:
                    value = target_type(value)
                except ValueError:
                    print('Value "{}" cannot be converted to type {}'.format(value, target_type.__name__))
                    continue

            # check if entries appear in the list of valid options, if there is one
            if 'valid' in opt.keys() and value not in opt['valid']:
                print('Value not in {}'.format(vld_opts))
            else:
                valid_choice = True
                cnfg[opt['name']] = value
        except (ValueError, AttributeError):
            print('Unable to validate entered value. Please try again.')


def main():
    # Don't try and merge existing configs - could be a clash of option names
    # in different sensor types which might be problematic. Replace entirely or leave alone.

    config_file = 'config.json'
    if os.path.exists(config_file):
        replace = {}
        config_parse({'prompt': 'Config file already exists. Replace?',
                      'default': 'n',
                      'type': str,
                      'name': 'replace',
                      'valid': ['y', 'n']}, replace)
        if replace['replace'] == 'n':
            sys.exit()
        else:
            os.remove(config_file)

    # Get the config options for the sensors by loading the available sensor classes from
    # the sensors module, ignoring the base class.
    # The sensor_classes variable is list of tuples: (name, class_reference)
    sensor_classes = inspect.getmembers(sensors, inspect.isclass)
    sensor_classes = [sc for sc in sensor_classes if sc[0] != 'SensorBase']
    sensor_numbers = [idx + 1 for idx in range(len(sensor_classes))]
    sensor_options = {nm: tp for nm, tp in zip(sensor_numbers, sensor_classes)}
    sensor_menu = [str(ky) + ": " + tp[0] for ky, tp in sensor_options.items()]

    sensor_prompt = ('Hello! Follow these instructions to perform a one-off set up of your '
                     'ecosystem monitoring unit\nFirst lets do the sensor setup. Select one '
                     'of the following available sensor types:\n')
    sensor_prompt += '\n'.join(sensor_menu) + '\n'

    # select a sensor and then call the config method of the selected class to
    # get the config options
    sensor_config = {}
    config_parse({'prompt': sensor_prompt,
                  'valid': sensor_numbers,
                  'type': int,
                  'name': 'sensor_index'}, sensor_config)

    # convert index to name by looking up the index in the dictionary
    sensor_config['sensor_type'] = sensor_options[sensor_config['sensor_index']][0]
    # and also call the options method
    sensor_config_options = sensor_options[sensor_config['sensor_index']][1].options()

    # populate the sensor config dictionary
    for option in sensor_config_options:
        config_parse(option, sensor_config)

    # test for offline mode
    offline_options = [{'name': 'offline_mode',
                        'type': int,
                        'prompt': 'Should the recorder run in offline mode (1) or use rclone (0) to upload data to cloud storage?\n',
                        'default': 0,
                        'valid': [0, 1]}]

    offline_config = {}

    # populate the offline config dictionary
    for option in offline_options:
        config_parse(option, offline_config)

    # Ask about internet connectivity for deployment information
    deployment_info_options = [{'name': 'has_internet',
                                'type': int,
                                'prompt': ('Will this deployment have internet connectivity for long-term monitoring?\n'
                                          '1 = Yes (data will be uploaded periodically to server. Reboot can clear live_data)\n'
                                          '0 = No (data stays on micro SD card. Reboot only refreshes internal memory)'),
                                'default': 1,
                                'valid': [0, 1]}]

    deployment_config = {}

    # populate the deployment config dictionary
    for option in deployment_info_options:
        config_parse(option, deployment_config)

    # Populate the rclone config unless the user has chosen offline mode

    rclone_config = {}

    if not offline_config['offline_mode']:

        rclone_config_options = [
                      {'name': 'remote_name',
                       'type': str,
                       'prompt': 'Enter the rclone remote name (e.g., mybox, gdrive)',
                       'default': 'mybox'},
                      {'name': 'config_path',
                       'type': str,
                       'prompt': 'Enter the path to rclone config file (leave empty for default ~/.config/rclone/rclone.conf)',
                       'default': '/home/pi/.config/rclone/rclone.conf'}]

        print("\nNow let's do the rclone cloud storage details...")

        # populate the rclone config dictionary
        for option in rclone_config_options:
            config_parse(option, rclone_config)

    # Populate the system config options

    #TODO add in the pre-upload dir option here
    sys_config_options = [
                  {'name': 'working_dir',
                   'type': str,
                   'prompt': 'Enter the working directory path',
                   'default': '/home/pi/tmp_dir'},
                  {'name': 'upload_dir',
                   'type': str,
                   'prompt': 'Enter the upload directory path',
                   'default': '/home/pi/multi_channel_monitoring_data'},
                  {'name': 'reboot_time',
                   'type': str,
                   'prompt': 'Enter the time for the daily reboot',
                   'default': '02:00'},
                  {'name': 'wipe_data_on_boot',
                   'type': int,
                   'prompt': 'Should old data be wiped on boot to prevent storage overflow? (1 for yes, 0 for no)',
                   'default': 0,
                   'valid': [0, 1]}]

    print("Now let's do the system details...")
    sys_config = {}

    # populate the sensor config dictionary
    for option in sys_config_options:
        config_parse(option, sys_config)

    config = {'rclone': rclone_config, 'offline_mode': offline_config['offline_mode'],
              'has_internet': deployment_config['has_internet'],
              'sensor': sensor_config, 'sys': sys_config}

    # save the config
    with open(config_file, 'w') as fp:
        json.dump(config, fp, indent=4)

    print('All done!')


if __name__ == "__main__":
    main()