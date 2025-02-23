import React from "react";
import "../App.css";

function Sidebar({ apiOptions, selectedApi, onApiSelect }) {
  return (
    <nav className="sidebar">
      <h2 className="logo">JD PARSER</h2>
      {apiOptions.map((option) => (
        <button
          key={option.id}
          className={`nav-btn ${selectedApi === option.id ? "active" : ""}`}
          onClick={() => onApiSelect(option.id)}
        >
          {option.label}
        </button>
      ))}
    </nav>
  );
}

export default Sidebar;
