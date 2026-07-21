import { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { motion } from 'framer-motion';

// Component to dynamically set bounds based on routes
function ChangeView({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    // Smoothly fly to the corridor's coordinates
    map.flyTo(center, 4, { duration: 1.5 });
  }, [center, map]);
  return null;
}

interface MapProps {
  corridor: string;
  routes?: any[];
  approved?: boolean;
}

const supplierCoords: Record<string, [number, number]> = {
  // Exact matches for routes.json source_supplier names
  'Saudi Arabia - Arab Light (Yanbu)': [24.1, 38.1],
  'UAE - Murban (Fujairah)': [25.1, 56.3],
  'Iraq - Basra Medium': [29.9, 48.4],
  'Russia - Urals (Baltic)': [59.7, 28.4],
  'Russia - Urals (Black Sea)': [44.7, 37.8],
  'Russia - ESPO (Far East)': [42.8, 132.8],
  'Nigeria - Bonny Light': [4.4, 7.2],
  'Angola - Girassol': [-8.8, 13.2],
  'United States - WTI Midland': [29.7, -95.2],
  'Brazil - Tupi': [-23.9, -46.3],
  // Historical event supplier names (abqaiq/us_iran)
  'Iraq - Basra': [29.9, 48.4],
  'UAE - Murban': [25.1, 56.3],
  'United States - WTI': [29.7, -95.2],
  'Nigeria - Agbami': [4.4, 7.2],
  'Oman': [23.6, 58.5],
  'Russia - Urals': [59.7, 28.4],
  // Fallback generic names
  'US Gulf Coast': [29.7, -95.2],
  'Brazil (Tupi)': [-23.9, -46.3],
  'West Africa (Angola)': [-8.8, 13.2],
  'Saudi Arabia (Arab Light)': [26.5, 50.0],
};

export default function MapComponent({ corridor, routes = [], approved = false }: MapProps) {
  // Hardcoded coordinates for the primary disruption corridor
  const corridorCoords: Record<string, [number, number]> = {
    hormuz: [26.56, 56.26],
    malacca: [2.5, 101.3],
    suez: [30.6, 32.35]
  };

  const center = corridorCoords[corridor] || [15, 60];
  const jamnagar: [number, number] = [22.33, 69.8];

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-full h-full relative z-0"
    >
      <MapContainer 
        center={center} 
        zoom={3} 
        scrollWheelZoom={false}
        className="w-full h-full bg-zinc-900"
      >
        <ChangeView center={center} />
        {/* Dark theme tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Primary Disruption Marker */}
        <CircleMarker 
          center={center} 
          pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.5 }} 
          radius={12}
        >
          <Popup className="font-mono text-xs">
            <strong className="uppercase">Primary Disruption</strong><br/>
            {corridor.replace('_', ' ').toUpperCase()}
          </Popup>
        </CircleMarker>

        {/* Destination Marker */}
        <CircleMarker 
          center={jamnagar} 
          pathOptions={{ color: '#3f3f46', fillColor: '#a1a1aa', fillOpacity: 0.8 }} 
          radius={6}
        >
          <Popup className="font-mono text-xs">
            <strong className="uppercase">Destination</strong><br/>
            JAMNAGAR (RIL)
          </Popup>
        </CircleMarker>

        {/* Alternative Routes Polylines */}
        {routes?.map((route, idx) => {
          const start = supplierCoords[route.source_supplier] || [0, 0];
          const isApproved = approved && idx === 0;
          const color = isApproved ? '#22c55e' : (idx === 0 ? '#f4f4f5' : '#52525b');
          const weight = idx === 0 ? 3 : 1.5;
          const dashArray = isApproved ? undefined : "5, 10";
          
          return (
            <Polyline 
              key={idx} 
              positions={[start, jamnagar]} 
              pathOptions={{ color, weight, dashArray }} 
            >
              <Popup className="font-mono text-xs">
                <strong className="uppercase">{route.source_supplier} to Jamnagar</strong><br/>
                Rank: {route.rank}<br/>
                Time: {route.transit_time_days} days<br/>
                {isApproved && <span className="text-green-600 font-bold mt-1 block uppercase">Route Approved</span>}
              </Popup>
            </Polyline>
          );
        })}

      </MapContainer>
      
      {/* Overlay to style the map edges sharply and blend with our theme */}
      <div className="absolute inset-0 border border-zinc-700 pointer-events-none z-[1000]" />
    </motion.div>
  );
}
