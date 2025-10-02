import React from "react";


export default function Switch({ checked, onChange, label, hint, className = "" }) {
  return (
    <label className={`inline-flex items-center gap-3 select-none ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange?.(!checked)}
        className={[
          "relative inline-flex h-5 min-w-10 rounded-full transition-colors duration-200",
          checked ? "bg-blue-600" : "bg-neutral-400/60 dark:bg-neutral-600",
          "outline-none ring-2 ring-blue-500"
        ].join(" ")}
      >
        <span
          className={[
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200",
            checked ? "translate-x-full" : ""
          ].join(" ")}
        />
      </button>
      {(label || hint) && (
        <span className="flex flex-col">
          {label && <span className="text-sm">{label}</span>}
          {hint && <span className="text-xs opacity-70 -mt-0.5">{hint}</span>}
        </span>
      )}
    </label>
  );
}
