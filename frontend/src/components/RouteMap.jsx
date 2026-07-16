import { useEffect, useRef } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Marker semantics: endpoints (current/pickup/dropoff) are labeled pins;
// en-route events (fuel/rest/break/restart) are small colored dots. So size &
// shape carry meaning instead of being incidental.
const META = {
  current: { color: "#0f766e", label: "Current", letter: "C", pin: true },
  pickup: { color: "#2563eb", label: "Pickup", letter: "P", pin: true },
  dropoff: { color: "#16a34a", label: "Dropoff", letter: "D", pin: true },
  fuel: { color: "#f59e0b", label: "Fuel stop", pin: false },
  rest: { color: "#7c3aed", label: "10-hr rest", pin: false },
  break: { color: "#0891b2", label: "30-min break", pin: false },
  restart: { color: "#dc2626", label: "34-hr restart", pin: false },
};
const LEGEND_ORDER = ["current", "pickup", "fuel", "break", "rest", "restart", "dropoff"];

// GeoJSON stores [lng, lat]; Leaflet wants [lat, lng].
const toLatLng = (c) => [c[1], c[0]];

function pinIcon(color, letter) {
  return L.divIcon({
    className: "map-pin",
    html: `<span class="map-pin-body" style="background:${color}">
             <span class="map-pin-letter">${letter}</span>
           </span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24], // tip points at the coordinate
    popupAnchor: [0, -22],
  });
}

// Fit to the route only when the route itself changes (preserve user pan/zoom).
function FitBounds({ positions, signature }) {
  const map = useMap();
  const last = useRef(null);
  useEffect(() => {
    if (positions.length && signature !== last.current) {
      map.fitBounds(positions, { padding: [30, 30] });
      last.current = signature;
    }
  }, [signature, positions, map]);
  return null;
}

export default function RouteMap({ plan }) {
  const line = (plan.route.geometry?.coordinates || []).map(toLatLng);
  if (!line.length) return null;

  const current = plan.route.waypoints?.current;
  const stops = plan.stops.filter((s) => s.coordinates);

  // Endpoints as pins (include the trip start), en-route stops as dots.
  const pins = [];
  if (current) pins.push({ type: "current", coordinates: current, label: plan.inputs?.current_location });
  stops.filter((s) => META[s.type]?.pin).forEach((s) => pins.push(s));
  const dots = stops.filter((s) => !META[s.type]?.pin);

  const present = LEGEND_ORDER.filter(
    (t) => (t === "current" && current) || stops.some((s) => s.type === t)
  );
  const signature = `${line.length}:${line[0]}:${line[line.length - 1]}`;

  return (
    <div className="map-wrap">
      <MapContainer center={line[0]} zoom={6} className="map" scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={line} color="#1d4ed8" weight={4} opacity={0.85} />

        {dots.map((s) => (
          <CircleMarker
            key={`${s.type}-${s.mile}-${s.arrive}`}
            center={toLatLng(s.coordinates)}
            radius={6}
            pathOptions={{ color: "#fff", weight: 1.5, fillColor: META[s.type].color, fillOpacity: 1 }}
          >
            <Popup>
              <strong>{META[s.type].label}</strong>
              {s.label ? ` · ${s.label}` : ""}
              <br />
              {s.duration_hrs} h · mile {s.mile}
            </Popup>
          </CircleMarker>
        ))}

        {pins.map((s, i) => (
          <Marker
            key={`pin-${s.type}-${i}`}
            position={toLatLng(s.coordinates)}
            icon={pinIcon(META[s.type].color, META[s.type].letter)}
          >
            <Popup>
              <strong>{META[s.type].label}</strong>
              {s.label ? ` · ${s.label}` : ""}
            </Popup>
          </Marker>
        ))}

        <FitBounds positions={line} signature={signature} />
      </MapContainer>

      <div className="map-legend" aria-label="Map legend">
        {present.map((t) => (
          <span className="legend-item" key={t}>
            <span
              className={META[t].pin ? "legend-pin" : "legend-dot"}
              style={{ background: META[t].color }}
            />
            {META[t].label}
          </span>
        ))}
      </div>
    </div>
  );
}
