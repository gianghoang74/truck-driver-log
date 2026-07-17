import { useEffect, useState } from "react";
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
  const [fieldErrors, setFieldErrors] = useState({});
  const [activeDay, setActiveDay] = useState(0);

  // While the blocking overlay is up, prevent the page behind it from scrolling.
  useEffect(() => {
    document.body.style.overflow = loading ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [loading]);

  async function handlePlan(input) {
    setLoading(true);
    setError(null);
    setFieldErrors({});
    try {
      setPlan(await planTrip(input));
      setActiveDay(0);
    } catch (err) {
      setError(err.message);
      setFieldErrors(err.fieldErrors || {});
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      {loading && (
        <div className="loading-overlay" role="alert" aria-busy="true" aria-live="assertive">
          <div className="loading-box">
            <div className="spinner" aria-hidden="true" />
            <span>Planning your trip…</span>
          </div>
        </div>
      )}

      <header className="app-header">
        <h1>ELD Trip Planner</h1>
        <p>Plan a property-carrying trip and generate the driver's daily logs.</p>
      </header>

      <main className="layout">
        <section className="panel form-panel">
          <h2>Trip details</h2>
          <TripForm onPlan={handlePlan} loading={loading} errors={fieldErrors} />
          {error && <p className="error" role="alert">{error}</p>}
        </section>

        <section className="panel result-panel">
          {!plan && (
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

              <div className="logs-head">
                <h2>Daily logs</h2>
                {plan.days.length > 1 && (
                  <nav className="day-pager" aria-label="Select log day">
                    <button className="pager-arrow" disabled={activeDay === 0}
                      onClick={() => setActiveDay((d) => Math.max(0, d - 1))}
                      aria-label="Previous day">‹</button>
                    {plan.days.map((day, i) => (
                      <button key={day.index}
                        className={`pager-day${i === activeDay ? " active" : ""}`}
                        onClick={() => setActiveDay(i)}
                        aria-current={i === activeDay ? "true" : undefined}>
                        {day.index}
                      </button>
                    ))}
                    <button className="pager-arrow" disabled={activeDay === plan.days.length - 1}
                      onClick={() => setActiveDay((d) => Math.min(plan.days.length - 1, d + 1))}
                      aria-label="Next day">›</button>
                  </nav>
                )}
              </div>

              {/* All sheets stay in the DOM so Print outputs every day; only the
                  active one is shown on screen (see .log-page in index.css). */}
              <div className="logs">
                {plan.days.map((day, i) => (
                  <div key={day.index} className={`log-page${i === activeDay ? " active" : ""}`}>
                    <LogSheet day={day} />
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
