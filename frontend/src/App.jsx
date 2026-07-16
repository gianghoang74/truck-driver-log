import { useState } from "react";
import TripForm from "./components/TripForm";
import RouteMap from "./components/RouteMap";
import LogSheet from "./components/LogSheet";
import { planTrip } from "./api";
import demoPlan from "./demoPlan";

// ?demo=1 seeds a sample plan so the map + logs can be previewed without an API key.
const useDemo = new URLSearchParams(window.location.search).get("demo") === "1";

export default function App() {
  const [plan, setPlan] = useState(useDemo ? demoPlan : null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handlePlan(input) {
    setLoading(true);
    setError(null);
    try {
      setPlan(await planTrip(input));
    } catch (err) {
      setError(err.message);
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>ELD Trip Planner</h1>
        <p>Plan a property-carrying trip and generate the driver's daily logs.</p>
      </header>

      <main className="layout">
        <section className="panel form-panel">
          <h2>Trip details</h2>
          <TripForm onPlan={handlePlan} loading={loading} />
          {error && <p className="error">{error}</p>}
        </section>

        <section className="panel result-panel">
          {loading && (
            <div className="empty">
              <div className="spinner" aria-hidden="true" />
              Planning your trip…
            </div>
          )}
          {!plan && !loading && (
            <div className="empty">Enter trip details to see the route and logs.</div>
          )}
          {plan && (
            <>
              <div className="result-toolbar">
                <button className="btn-secondary" onClick={() => window.print()}>
                  Print / Save PDF
                </button>
              </div>
              <div className="summary">
                <div><span>{plan.route.distance_mi}</span> miles</div>
                <div><span>{plan.route.drive_hrs}</span> drive hrs</div>
                <div><span>{plan.days.length}</span> log day(s)</div>
              </div>
              <RouteMap plan={plan} />
              <h2>Daily logs</h2>
              <div className="logs">
                {plan.days.map((day) => <LogSheet key={day.index} day={day} />)}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
