#!/usr/bin/env python3
import shutil
import logging
import pulsectl
import subprocess

from pulsectl import PulseSinkInfo, PulseSourceInfo, PulseSinkInputInfo, PulseSourceOutputInfo

LOG = logging.getLogger('generic')
PULSE = pulsectl.Pulse('pmctl')


def create_device(device_type: str, name: str, channels: int, position: list[str]) -> bool:
    class_map = {'sink': 'Sink', 'source': 'Source/Virtual'}
    data = f'''{{
        factory.name=support.null-audio-sink
        node.name="{name}"
        node.description="{name}"
        media.class=Audio/{class_map[device_type]}
        audio.channels={channels}
        audio.position="{' '.join(position)}"
        monitor.channel-volumes=true
        object.linger=true
    }}'''
    command = ['pw-cli', 'create-node', 'adapter', data]
    ret, stdout, stderr = run_command(command, split=False)
    if ret != 0:
        raise RuntimeError(f"Failed to create device: {stderr}")
    return True


def remove_device(name: str) -> bool:
    command = ['pw-cli', 'destroy', name]
    ret, stdout, stderr = run_command(command)
    if ret != 0:
        raise RuntimeError(f"Failed to remove device: {stderr}")
    return True


def link(input_name: str, output_name: str, state: bool = True) -> bool:
    operation = [] if state else ['-d']
    command = ['pw-link', input_name, output_name, *operation]
    ret, stdout, stderr = run_command(command)
    return True


def link_channels(input_name: str, output_name: str, channel_map: str, state: bool = True) -> bool:
    input_ports = get_ports('output', input_name)
    output_ports = get_ports('input', output_name)

    if not input_ports or not output_ports:
        raise RuntimeError(f'Ports not found for devices {input_name} {output_name}')

    for pair in channel_map.split(' '):
        input_id, output_id = pair.split(':')
        input_port = f'{input_name}:{input_ports[int(input_id)]}'
        output_port = f'{output_name}:{output_ports[int(output_id)]}'
        link(input_port, output_port, state=state)

    return True


def get_ports(port_type: str, device_name: str) -> list[str]:
    """
    Get a list of "ports" (channel indices) for a device.
    port_type: 'input' or 'output'
    device_name: Pulse device name
    """
    device_type = 'sink' if port_type == 'output' else 'source'
    device = get_device_by_name(device_type, device_name)

    if device is None:
        LOG.warning("Device not found: %s", device_name)
        return []

    # Each channel is treated as a port
    return [str(i) for i in range(len(device.volume.values))]


def mute(device_type: str, device_name: str, state: bool, pulse=None) -> int:
    if pulse is None:
        pulse = PULSE
    device = get_device_by_name(device_type, device_name)
    if device is None:
        LOG.error('Device not found %s', device_name)
        return False
    pulse.mute(device, state)
    return True


def set_primary(device_type: str, device_name: str, pulse=None) -> bool:
    if pulse is None:
        pulse = PULSE
    device = get_device_by_name(device_type, device_name)
    if device is None:
        LOG.error('Device not found %s', device_name)
        return False
    pulse.default_set(device)
    return True


def set_volume(device_type: str, device_name: str, val: int, selected_channels: list[bool] = None) -> bool:
    val = min(max(0, val), 153)
    device = get_device_by_name(device_type, device_name)
    if device is None:
        LOG.error('Device not found %s', device_name)
        return False

    volume_value = device.volume
    channels = len(device.volume.values)
    if selected_channels is None:
        volume_value.value_flat = val / 100
        PULSE.volume_set(device, volume_value)
        return True

    volume_list = []
    for channel in range(channels):
        if selected_channels[channel] is True:
            volume_list.append(val / 100)
        else:
            volume_list.append(device.volume.values[channel])

    volume_value = pulsectl.PulseVolumeInfo(volume_list)
    PULSE.volume_set(device, volume_value)
    return True


def device_exists(device_name: str) -> bool:
    source_exists = get_device_by_name('source', device_name)
    sink_exists = get_device_by_name('sink', device_name)
    return source_exists is not None or sink_exists is not None


def get_primary(device_type: str, pulse=None) -> PulseSinkInfo | PulseSourceInfo:
    if pulse is None:
        pulse = PULSE
    if device_type == 'sink':
        return pulse.sink_default_get()
    return pulse.source_default_get()


def get_device_by_name(device_type: str, device_name: str) -> PulseSinkInfo | PulseSourceInfo:
    try:
        if device_type == 'sink':
            return PULSE.get_sink_by_name(device_name)
        return PULSE.get_source_by_name(device_name)
    except pulsectl.pulsectl.PulseIndexError:
        return None


def get_device_by_index(device_type: str, device_index: str) -> PulseSinkInfo | PulseSourceInfo:
    try:
        if device_type == 'sink':
            return PULSE.sink_info(device_index)
        return PULSE.source_info(device_index)
    except pulsectl.pulsectl.PulseIndexError:
        return None


def run_command(command: list[str], split: bool = False) -> tuple[int, str, str]:
    import os
    if split and isinstance(command, str):
        command = command.split()
    LOG.debug('Running command: %s', command)
    env = os.environ.copy()
    env["PATH"] = os.getcwd() + ":" + env.get("PATH", "")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()

def is_pipewire() -> bool:
    """
    Check if PipeWire is available on the system.
    Returns:
        bool: True if PipeWire is available, False otherwise.
    """
    import shutil
    return shutil.which('pipewire-pulse') is not None

def get_app_device(app_type: str, app: PulseSinkInputInfo | PulseSourceOutputInfo) -> PulseSinkInfo | PulseSourceInfo:
    try:
        if app_type == 'sink_input':
            return PULSE.sink_info(app.sink)
        return PULSE.source_info(app.source)
    except pulsectl.pulsectl.PulseIndexError:
        return None

def list_apps(app_type: str) -> list[PulseSinkInputInfo | PulseSourceOutputInfo]:
    app_list = []
    full_app_list = PULSE.sink_input_list() if app_type == 'sink_input' else PULSE.source_output_list()
    for app in full_app_list:
        hasname = app.proplist.get('application.name', False)
        is_peak = '_peak' in app.proplist.get('application.name', '')
        is_pavucontrol = app.proplist.get('application.id') == 'org.PulseAudio.pavucontrol'
        if is_peak or is_pavucontrol or not hasname:
            continue
        app.device_name = get_app_device(app_type, app).name
        app_list.append(app)
    return app_list

def list_devices(device_type: str) -> list[PulseSinkInfo | PulseSourceInfo]:
    '''
    List all hardware devices of a given type (sink or source).
    Args:
        device_type (str): 'sink' or 'source'.
    Returns:
        list: List of hardware device objects.
    '''
    pulse = pulsectl.Pulse()
    list_pa_devices = pulse.sink_list if device_type == 'sink' else pulse.source_list
    device_list = []
    for device in list_pa_devices():
        if is_hardware_device(device):
            device_list.append(device)

    return device_list

def is_hardware_device(device: PulseSinkInfo | PulseSourceInfo) -> bool:
    """
    Determine if a device is a hardware device (not a monitor or null sink).
    Args:
        device: The device object to check.
    Returns:
        bool: True if hardware, False otherwise.
    """
    is_easy = 'easyeffects_' in device.name
    is_monitor = device.proplist.get('device.class') == "monitor"
    is_null = device.proplist.get('factory.name') == 'support.null-audio-sink'

    if not is_monitor and (not is_null or is_easy):
        return True

    return False

def move_app_device(app_type: str, index: int, device_name: str) -> bool:
    """
    Move an application stream to a different device.
    Args:
        app_type (str): 'sink_input' or 'source_output'.
        index (int): Index of the application stream.
        device_name (str): Name of the new device.
    Returns:
        bool: True on success, False on failure.
    """
    device_type = 'sink' if app_type == 'sink_input' else 'source'
    device = get_device_by_name(device_type, device_name)
    if not device:
        LOG.warning("Target device not found: %s", device_name)
        return False

    move = PULSE.sink_input_move if app_type == 'sink_input' else PULSE.source_output_move
    try:
        move(index, device.index)
    except pulsectl.PulseOperationFailed:
        LOG.debug("App #%d device can't be moved", index)
        return False

    return True

