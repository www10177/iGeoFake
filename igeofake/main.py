from nicegui import ui, app
import asyncio
from process_manager import ProcessManager, STATE_STOPPED, STATE_CONNECTED, STATE_SIMULATING, STATE_ERROR, STATE_STARTING

# Global Manager Instance
manager: ProcessManager = None

# UI Elements
log_area = None
status_label = None
start_btn = None
stop_btn = None
set_loc_btn = None
clear_loc_btn = None
lat_input = None
lon_input = None

def on_log(message: str):
    """Callback for appending logs."""
    if log_area:
        log_area.push(message)

def on_status_change(new_state: str):
    """Callback for status updates."""
    if status_label:
        status_label.set_text(f"Status: {new_state}")
        status_label.classes(remove='text-red-500 text-green-500 text-blue-500 text-yellow-500 text-gray-500')

        if new_state == STATE_STOPPED:
            status_label.classes('text-gray-500')
            start_btn.enable()
            stop_btn.disable()
            set_loc_btn.disable()
            clear_loc_btn.disable()

        elif new_state == STATE_STARTING:
            status_label.classes('text-yellow-500')
            start_btn.disable()
            stop_btn.enable()
            set_loc_btn.disable()
            clear_loc_btn.disable()

        elif new_state == STATE_CONNECTED:
            status_label.classes('text-green-500')
            start_btn.disable()
            stop_btn.enable()
            set_loc_btn.enable()
            clear_loc_btn.enable()

        elif new_state == STATE_SIMULATING:
            status_label.classes('text-blue-500')
            start_btn.disable()
            stop_btn.enable()
            set_loc_btn.enable()
            clear_loc_btn.enable()

        elif new_state == STATE_ERROR:
            status_label.classes('text-red-500')
            start_btn.enable()
            stop_btn.disable()
            set_loc_btn.disable()
            clear_loc_btn.disable()

async def handle_start():
    await manager.start_services()

async def handle_stop():
    await manager.stop_services()

async def handle_set_location():
    if lat_input.value is None or lon_input.value is None:
        ui.notify('Please enter valid Latitude and Longitude', type='warning')
        return
    await manager.set_location(str(lat_input.value), str(lon_input.value))

async def handle_clear_location():
    await manager.clear_location()

@ui.page('/')
def main_page():
    global log_area, status_label, start_btn, stop_btn, set_loc_btn, clear_loc_btn, lat_input, lon_input, manager

    # Initialize Manager
    if not manager:
        manager = ProcessManager(on_log, on_status_change)

    # Admin Check on Startup
    if not manager.check_admin():
        ui.label('ERROR: Must run as Administrator').classes('text-4xl text-red-600 font-bold m-4')
        ui.label('Please restart the application with "Run as Administrator".').classes('text-xl m-4')
        return

    # Layout
    with ui.column().classes('w-full h-full p-4'):
        ui.label('iGeoFake - iOS Location Simulator').classes('text-2xl font-bold mb-4')

        status_label = ui.label(f'Status: {manager.state}').classes('text-xl font-bold text-gray-500 mb-4')

        with ui.row().classes('w-full gap-4'):
            start_btn = ui.button('Start Services', on_click=handle_start)
            stop_btn = ui.button('Stop Services', on_click=handle_stop).props('color=red')
            stop_btn.set_enabled(False)

        with ui.row().classes('w-full gap-4 mt-4 items-center'):
            lat_input = ui.number(label='Latitude', value=25.0330, format='%.6f', step=0.0001).classes('w-32')
            lon_input = ui.number(label='Longitude', value=121.5654, format='%.6f', step=0.0001).classes('w-32')
            set_loc_btn = ui.button('Set Location', on_click=handle_set_location)
            set_loc_btn.set_enabled(False)
            clear_loc_btn = ui.button('Clear Location', on_click=handle_clear_location).props('outline')
            clear_loc_btn.set_enabled(False)

        ui.label('Process Logs:').classes('font-bold mt-4')
        log_area = ui.log(max_lines=1000).classes('w-full h-64 border p-2 bg-gray-100 font-mono text-sm')

    # Initial State Sync
    on_status_change(manager.state)

def run():
    ui.run(title='iGeoFake', reload=False, port=8080)

if __name__ in {"__main__", "__mp_main__"}:
    run()
