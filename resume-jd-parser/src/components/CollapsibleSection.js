import React from "react";
import "../App.css";

function CollapsibleSection({ label, isOpen, onToggle, children }) {
  return (
    <div className="section">
      <button className="collapsible" onClick={onToggle}>
        {label} {isOpen ? "▲" : "▼"}
      </button>
      {isOpen && <div className="content">{children}</div>}
    </div>
  );
}

export default CollapsibleSection;
