from nicegui import ui, app
import asyncio
from process_manager import ProcessManager, STATE_STOPPED, STATE_CONNECTED, STATE_SIMULATING, STATE_ERROR, STATE_STARTING, STATE_TUNNEL_A_RUNNING

# Global Manager Instance
manager: ProcessManager = None

# UI Elements
log_area = None
status_label = None
btn_tunnel_a = None
btn_tunnel_b = None
stop_btn = None
set_loc_btn = None
clear_loc_btn = None
coord_input = None
map_element = None
map_marker = None
# Route UI Elements
gpx_upload = None
play_route_btn = None
noise_input = None
uploaded_gpx_path = None

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
            btn_tunnel_a.enable()
            btn_tunnel_b.disable()
            stop_btn.disable()
            set_loc_btn.disable()
            clear_loc_btn.disable()
            if play_route_btn: play_route_btn.disable()

        elif new_state == STATE_TUNNEL_A_RUNNING:
            status_label.classes('text-yellow-500')
            btn_tunnel_a.disable()
            btn_tunnel_b.enable()
            stop_btn.enable()
            set_loc_btn.disable()
            clear_loc_btn.disable()
            if play_route_btn: play_route_btn.disable()

        elif new_state == STATE_STARTING:
            status_label.classes('text-yellow-500')
            btn_tunnel_a.disable()
            btn_tunnel_b.disable()
            stop_btn.enable()
            set_loc_btn.disable()
            clear_loc_btn.disable()
            if play_route_btn: play_route_btn.disable()

        elif new_state == STATE_CONNECTED:
            status_label.classes('text-green-500')
            btn_tunnel_a.disable()
            btn_tunnel_b.disable()
            stop_btn.enable()
            set_loc_btn.enable()
            clear_loc_btn.enable()
            if play_route_btn and uploaded_gpx_path: play_route_btn.enable()

        elif new_state == STATE_SIMULATING:
            status_label.classes('text-blue-500')
            btn_tunnel_a.disable()
            btn_tunnel_b.disable()
            stop_btn.enable()
            set_loc_btn.enable()
            clear_loc_btn.enable()
            if play_route_btn and uploaded_gpx_path: play_route_btn.enable()

        elif new_state == STATE_ERROR:
            status_label.classes('text-red-500')
            btn_tunnel_a.enable()
            btn_tunnel_b.disable()
            stop_btn.disable()
            set_loc_btn.disable()
            clear_loc_btn.disable()
            if play_route_btn: play_route_btn.disable()

async def handle_start_tunnel_a():
    await manager.start_tunnel_a()

async def handle_start_tunnel_b():
    await manager.start_tunnel_b()

async def handle_stop():
    await manager.stop_services()

def parse_coordinates(text: str):
    try:
        parts = text.split(',')
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon
    except ValueError:
        pass
    return None, None

async def handle_set_location():
    lat, lon = parse_coordinates(coord_input.value)
    if lat is None or lon is None:
        ui.notify('Invalid format. Use "Lat, Lon" (e.g., 25.03, 121.56)', type='warning')
        return
    await manager.set_location(str(lat), str(lon))

async def handle_clear_location():
    await manager.clear_location()

async def handle_play_route():
    if not uploaded_gpx_path:
        ui.notify('Please upload a GPX file first.', type='warning')
        return
    noise_val = noise_input.value if noise_input.value else 500
    await manager.play_route(uploaded_gpx_path, str(int(noise_val)))

def handle_upload(e):
    global uploaded_gpx_path
    try:
        # Save uploaded file
        name = e.name
        content = e.content.read()
        # Save to local directory
        # We can just save it as 'route.gpx' or keep original name
        # Let's save as 'uploaded_route.gpx' to keep it simple and overwrite previous
        uploaded_gpx_path = 'uploaded_route.gpx'
        with open(uploaded_gpx_path, 'wb') as f:
            f.write(content)

        ui.notify(f'Uploaded {name}')
        if manager.state in [STATE_CONNECTED, STATE_SIMULATING]:
            play_route_btn.enable()

    except Exception as ex:
        ui.notify(f'Error uploading file: {ex}', type='negative')

def update_map_from_input():
    lat, lon = parse_coordinates(coord_input.value)
    if lat is not None and lon is not None:
        if map_marker:
            map_marker.move(lat, lon)
        map_element.center = (lat, lon)

def handle_marker_drag(e):
    try:
        # Custom event structure from JavaScript
        lat = e.args['lat']
        lon = e.args['lng']
        coord_input.value = f"{lat:.6f}, {lon:.6f}"
        if manager:
            manager.log(f"DEBUG: Marker dragged to {lat:.6f}, {lon:.6f}")
    except Exception as ex:
        if manager:
            manager.log(f"ERROR in handle_marker_drag: {ex}")
        pass

def handle_map_click(e):
    try:
        lat = e.args['latlng']['lat']
        lon = e.args['latlng']['lng']
        coord_input.value = f"{lat:.6f}, {lon:.6f}"
        if map_marker:
            map_marker.move(lat, lon)
    except Exception as ex:
        if manager:
            manager.log(f"ERROR in handle_map_click: {ex}, args: {e.args}")

def handle_marker_drag(e):
    """Handle marker drag events from JavaScript"""
    try:
        lat = e.args['lat']
        lng = e.args['lng']
        coord_input.value = f"{lat:.6f}, {lng:.6f}"
        if manager:
            manager.log(f"DEBUG: Marker dragged to {lat:.6f}, {lng:.6f}")
    except Exception as ex:
        if manager:
            manager.log(f"ERROR in handle_marker_drag: {ex}, args: {e.args}")


@ui.page('/')
def main_page():
    global log_area, status_label, btn_tunnel_a, btn_tunnel_b, stop_btn, set_loc_btn, clear_loc_btn, coord_input, manager, map_element, map_marker
    global gpx_upload, play_route_btn, noise_input

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
            btn_tunnel_a = ui.button('Start Remote Tunneld', on_click=handle_start_tunnel_a)
            btn_tunnel_b = ui.button('Start Lockdown Tunnel', on_click=handle_start_tunnel_b)
            btn_tunnel_b.disable()
            
            stop_btn = ui.button('Stop Services', on_click=handle_stop).props('color=red')
            stop_btn.disable()

        with ui.row().classes('w-full gap-4 mt-4 items-center'):
            coord_input = ui.input(
                label='Coordinates (Lat, Lon)', 
                value='25.033000, 121.565400',
                on_change=update_map_from_input
            ).classes('w-96').props('clearable')
            
            set_loc_btn = ui.button('Set Location', on_click=handle_set_location)
            set_loc_btn.disable()
            clear_loc_btn = ui.button('Clear Location', on_click=handle_clear_location).props('outline')
            clear_loc_btn.disable()

        # Route Simulation
        ui.label('Route Simulation (GPX)').classes('font-bold mt-4')
        with ui.row().classes('w-full gap-4 items-center'):
            gpx_upload = ui.upload(
                label='Upload GPX',
                on_upload=handle_upload,
                max_files=1,
                auto_upload=True
            ).props('accept=.gpx').classes('w-64')

            noise_input = ui.number(
                label='Timing Noise (ms)',
                value=500,
                min=0,
                max=5000
            ).classes('w-40')

            play_route_btn = ui.button('Play Route', on_click=handle_play_route)
            play_route_btn.disable()

        # Map
        with ui.card().classes('w-full h-96 mt-4 p-0'):
            map_element = ui.leaflet(center=(25.0330, 121.5654), zoom=13).classes('w-full h-full')
            map_marker = map_element.marker(latlng=(25.0330, 121.5654), options={'draggable': True})
            map_element.on('marker-drag', handle_marker_drag)
            
            # Bind dragend event using external JavaScript file
            map_id = map_element.id
            
            # Add the JavaScript file to the page
            ui.add_head_html('<script src="/static/marker_drag.js"></script>')
            
            # Call the function after a delay to ensure everything is loaded
            def bind_drag_events():
                if manager:
                    manager.log(f"DEBUG: Calling bindMarkerDragEvents for map ID: {map_id}")
                ui.run_javascript(f'bindMarkerDragEvents({map_id});')
            
            ui.timer(0.5, bind_drag_events, once=True)

        ui.label('Process Logs:').classes('font-bold mt-4')
        log_area = ui.log(max_lines=1000).classes('w-full h-64 border p-2 bg-gray-100 font-mono text-sm')

    # Initial State Sync
    on_status_change(manager.state)

def run():
    from pathlib import Path
    # Mount static files directory
    app.add_static_files('/static', Path(__file__).parent / 'static')
    ui.run(title='iGeoFake', reload=False, port=8080)

if __name__ in {"__main__", "__mp_main__"}:
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='iGeoFake - iOS Location Simulator')
    parser.add_argument('--mock', action='store_true', 
                        help='Run in mock mode (no admin required, for development/testing)')
    args = parser.parse_args()
    
    if args.mock:
        os.environ['IGEOFAKE_MOCK'] = '1'
        print("Running in MOCK MODE - no admin required")
    
    run()

