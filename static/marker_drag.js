// Bind drag events to the Leaflet marker
function bindMarkerDragEvents(mapId) {
    try {
        console.log('Attempting to bind drag events for map ID:', mapId);
        const mapElement = getElement(mapId);

        if (mapElement && mapElement.map) {
            const map = mapElement.map;
            console.log('Leaflet map found');

            // Find the marker by iterating through layers
            map.eachLayer(function (layer) {
                if (layer instanceof L.Marker && layer.options.draggable) {
                    console.log('Found draggable marker');

                    layer.on('dragend', function (e) {
                        const latlng = e.target.getLatLng();
                        console.log('Marker dragged to:', latlng.lat, latlng.lng);
                        emitEvent('marker-drag', { lat: latlng.lat, lng: latlng.lng });
                    });

                    console.log('Drag events bound successfully to marker');
                }
            });
        } else {
            console.error('Map or map element not found');
        }
    } catch (err) {
        console.error('Error binding drag events:', err);
    }
}
