import React from "react";

export default function SessionExpiredModal({ open, onRelogin, onClose }) {
  if (!open) return null;
  const style = {
    pos: { position: "fixed", inset: 0, display: "grid", placeItems: "center", background: "rgba(0,0,0,.4)" },
    card: { background: "#111", color: "#fff", padding: 20, borderRadius: 12, width: 360, boxShadow: "0 10px 30px rgba(0,0,0,.5)" },
    btn: { padding: "10px 14px", borderRadius: 8, border: "none", cursor: "pointer" }
  };
  return (
    <div style={style.pos} onClick={onClose}>
      <div style={style.card} onClick={(e)=>e.stopPropagation()}>
        <h3 style={{marginTop:0}}>Сессия истекла</h3>
        <p>Пожалуйста, войдите снова, чтобы продолжить.</p>
        <div style={{display:"flex", gap:8, marginTop:16, justifyContent:"flex-end"}}>
          <button style={{...style.btn, background:"#333", color:"#fff"}} onClick={onClose}>Позже</button>
          <button style={{...style.btn, background:"#4F46E5", color:"#fff"}} onClick={onRelogin}>Войти снова</button>
        </div>
      </div>
    </div>
  );
}
