import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  const [health, setHealth] = React.useState(null);
  React.useEffect(() => {
    fetch(import.meta.env.VITE_API_BASE + "/health")
      .then(r => r.json()).then(setHealth).catch(()=>setHealth({ok:false}));
  }, []);
  return (
    <div style={{fontFamily:"system-ui", maxWidth:840, margin:"40px auto", padding:"0 16px"}}>
      <h1>🗞️ News MVP</h1>
      <p style={{color:"#6b7280"}}>API base: {import.meta.env.VITE_API_BASE}</p>
      <pre>{JSON.stringify(health, null, 2)}</pre>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
