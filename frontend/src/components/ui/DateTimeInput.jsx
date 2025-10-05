import React, { useEffect, useState } from "react";

/**
 * Красивая пара: дата + время. Отдаёт ISO UTC (...Z).
 * Ровная высота, одинаковые ширины, не расползается.
 */
export default function DateTimeInput({
  value,
  onChange,
  className = "",
  datePlaceholder = "ДД.ММ.ГГГГ",
  timePlaceholder = "--:--",
}) {
  const [d, setD] = useState(""); // YYYY-MM-DD
  const [t, setT] = useState(""); // HH:MM

  // parse ISO -> parts
  useEffect(() => {
    if (!value) { setD(""); setT(""); return; }
    try {
      const dt = new Date(value);
      if (Number.isNaN(dt.getTime())) { setD(""); setT(""); return; }
      const pad = (n) => String(n).padStart(2, "0");
      setD(`${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`);
      setT(`${pad(dt.getUTCHours())}:${pad(dt.getUTCMinutes())}`);
    } catch (e) {
      setD("");
      setT("");
    }
  }, [value]);

  // parts -> ISO (UTC)
  function setFullDate (date, time) {
    if (!date && !time) { onChange?.(""); return; }
    if (!date) { onChange?.(""); return; }
    const [y, m, day] = date.split("-").map(Number);
    const [hh = 0, mm = 0] = time ? time.split(":").map(Number) : [0, 0];
    if (!y || !m || !day) { onChange?.(""); return; }
    const dt = new Date(Date.UTC(y, m - 1, day, hh || 0, mm || 0, 0, 0));
    onChange?.(dt.toISOString().replace(/\.\d{3}Z$/, "Z"));
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <input
        type="date"
        value={d}
        onChange={(e) => {
          setD(e.target.value);
          setFullDate(e.target.value, t)
        }}
        placeholder={datePlaceholder}
        className="input flex-[1.2] min-w-0"
      />
      <input
        type="time"
        value={t}
        onChange={(e) => {
          setT(e.target.value);
          setFullDate(d, e.target.value)
        }}
        placeholder={timePlaceholder}
        className="input flex-[0.8] min-w-[6.5rem]"
      />
    </div>
  );
}
