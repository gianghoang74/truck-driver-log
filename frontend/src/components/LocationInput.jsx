import { useEffect, useRef, useState } from "react";
import { autocomplete } from "../api";

// Debounced type-ahead over the Django geocode proxy (>= 3 chars), with a
// stale-response guard, in-flight abort, keyboard navigation and ARIA combobox
// semantics.
export default function LocationInput({ id, label, value, onChange, placeholder }) {
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [active, setActive] = useState(-1);

  const abortRef = useRef(null);
  const reqIdRef = useRef(0);
  const justSelectedRef = useRef(false);
  const boxRef = useRef(null);

  useEffect(() => {
    // Don't refetch immediately after the user picked a suggestion.
    if (justSelectedRef.current) {
      justSelectedRef.current = false;
      return;
    }
    if (value.trim().length < 3) {
      abortRef.current?.abort();
      setSuggestions([]);
      setError(null);
      setOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const reqId = ++reqIdRef.current;
      setLoading(true);
      setError(null);
      try {
        const { suggestions } = await autocomplete(value.trim(), controller.signal);
        if (reqId !== reqIdRef.current) return; // stale response — ignore
        setSuggestions(suggestions);
        setActive(-1);
        setOpen(true);
      } catch (err) {
        if (err.name === "AbortError" || reqId !== reqIdRef.current) return;
        setSuggestions([]);
        setError("Location lookup unavailable");
        setOpen(true);
      } finally {
        if (reqId === reqIdRef.current) setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [value]);

  // Abort any in-flight request on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Close on outside click.
  useEffect(() => {
    function onClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function pick(s) {
    justSelectedRef.current = true;
    onChange(s.label);
    setOpen(false);
    setActive(-1);
  }

  function onKeyDown(e) {
    if (!open || !suggestions.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      pick(suggestions[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const listId = `${id}-listbox`;
  const showEmpty = open && !loading && !error && suggestions.length === 0
    && value.trim().length >= 3;

  return (
    <div className="field" ref={boxRef}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${id}-opt-${active}` : undefined}
        autoComplete="off"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={() => suggestions.length && setOpen(true)}
      />
      {loading && <span className="field-hint">searching…</span>}
      {open && (suggestions.length > 0 || showEmpty || error) && (
        <ul className="suggestions" id={listId} role="listbox">
          {suggestions.map((s, i) => (
            <li
              key={`${s.label}-${i}`}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : undefined}
              onMouseEnter={() => setActive(i)}
              onMouseDown={() => pick(s)}
            >
              {s.label}
            </li>
          ))}
          {showEmpty && <li className="suggestion-note">No matches</li>}
          {error && <li className="suggestion-note error">{error}</li>}
        </ul>
      )}
    </div>
  );
}
