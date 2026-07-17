import { useState } from "react";
import LocationInput from "./LocationInput";

export default function TripForm({ onPlan, loading, errors = {} }) {
  const [current, setCurrent] = useState("");
  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [cycleUsed, setCycleUsed] = useState("0");

  function submit(e) {
    e.preventDefault();
    onPlan({
      current_location: current,
      pickup_location: pickup,
      dropoff_location: dropoff,
      current_cycle_used_hrs: Number(cycleUsed) || 0,
    });
  }

  const ready = current && pickup && dropoff;

  return (
    <form className="trip-form" onSubmit={submit}>
      <LocationInput id="current" label="Current location" value={current}
        onChange={setCurrent} placeholder="City, State" fieldError={errors.current_location} />
      <LocationInput id="pickup" label="Pickup location" value={pickup}
        onChange={setPickup} placeholder="City, State" fieldError={errors.pickup_location} />
      <LocationInput id="dropoff" label="Dropoff location" value={dropoff}
        onChange={setDropoff} placeholder="City, State" fieldError={errors.dropoff_location} />
      <div className="field">
        <label htmlFor="cycle">Current cycle used (hrs)</label>
        <input id="cycle" type="number" min="0" max="70" step="0.25"
          value={cycleUsed} onChange={(e) => setCycleUsed(e.target.value)}
          aria-invalid={errors.current_cycle_used_hrs ? "true" : undefined} />
        {errors.current_cycle_used_hrs && (
          <span className="field-error">{errors.current_cycle_used_hrs}</span>
        )}
      </div>
      <button type="submit" disabled={!ready || loading}>
        {loading ? "Planning…" : "Plan trip"}
      </button>
    </form>
  );
}
