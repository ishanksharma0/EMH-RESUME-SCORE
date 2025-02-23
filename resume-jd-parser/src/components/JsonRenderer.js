import React from "react";
import "../App.css";
import CollapsibleSection from "./CollapsibleSection";

function JsonRenderer({
  data,
  expandedSections,
  toggleSection,
  parentKey = "",
  labelMappings = {},
}) {
  if (!data) return null;

  return Object.entries(data).map(([key, value]) => {
    // Skip certain keys
    if (key === "vectorized_jd" || key === "logo") return null;

    // Display label if available, else transform from snake_case
    const label = labelMappings[key] || key.replace(/_/g, " ").toUpperCase();
    const sectionKey = `${parentKey}${key}`;
    const isExpanded = expandedSections[sectionKey];

    // 1) Array of objects
    if (Array.isArray(value) && value.length > 0 && typeof value[0] === "object") {
      return (
        <CollapsibleSection
          key={sectionKey}
          label={label}
          isOpen={isExpanded}
          onToggle={() => toggleSection(sectionKey)}
        >
          {value.map((item, index) => {
            const nestedKey = `${sectionKey}[${index}]`;
            const nestedIsExpanded = expandedSections[nestedKey];
            return (
              <div key={nestedKey} className="nested-box">
                <CollapsibleSection
                  label={`${label} ${index + 1}`}
                  isOpen={nestedIsExpanded}
                  onToggle={() => toggleSection(nestedKey)}
                >
                  <JsonRenderer
                    data={item}
                    expandedSections={expandedSections}
                    toggleSection={toggleSection}
                    parentKey={`${nestedKey}.`}
                    labelMappings={labelMappings}
                  />
                </CollapsibleSection>
              </div>
            );
          })}
        </CollapsibleSection>
      );
    }

    // 2) Single object
    if (typeof value === "object" && value !== null) {
      return (
        <CollapsibleSection
          key={sectionKey}
          label={label}
          isOpen={isExpanded}
          onToggle={() => toggleSection(sectionKey)}
        >
          <JsonRenderer
            data={value}
            expandedSections={expandedSections}
            toggleSection={toggleSection}
            parentKey={`${sectionKey}.`}
            labelMappings={labelMappings}
          />
        </CollapsibleSection>
      );
    }

    // 3) If it's a scalar (string, number, etc.), we display it in a dynamic box
    return (
      <div key={sectionKey} className="subsection">
        <h4>{label}</h4>
        {/* 
          Instead of a textarea, we use a plain div with a special class 
          that auto-expands as the content grows.
        */}
        <div className="auto-size-box">{String(value)}</div>
      </div>
    );
  });
}

export default JsonRenderer;
