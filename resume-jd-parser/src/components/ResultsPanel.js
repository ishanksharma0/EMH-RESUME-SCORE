// ResultsPanel.js
import React from "react";
import "../App.css";
import JsonRenderer from "./JsonRenderer";

function ResultsPanel({ parsedData, loading, expandedSections, toggleSection }) {
  // Utility function to flatten a nested JSON object.
  // It skips keys named "vectorized_jd" and formats arrays of objects prettily.
  const flattenObject = (obj, parentKey = "", res = {}) => {
    for (let key in obj) {
      if (!obj.hasOwnProperty(key)) continue;
      // Skip the key "vectorized_jd"
      if (key === "vectorized_jd") continue;
      const newKey = parentKey ? `${parentKey}.${key}` : key;
      const value = obj[key];

      if (typeof value === "object" && value !== null && !Array.isArray(value)) {
        flattenObject(value, newKey, res);
      } else if (Array.isArray(value)) {
        // For arrays of objects, format each object in a human-readable way.
        if (value.length > 0 && typeof value[0] === "object") {
          const formatted = value
            .map((item) =>
              Object.entries(item)
                .map(([k, v]) => `${k}: ${v}`)
                .join(", ")
            )
            .join("\n");
          res[newKey] = formatted;
        } else {
          // For arrays of primitives, join them with a semicolon.
          res[newKey] = value.join("; ");
        }
      } else {
        res[newKey] = value;
      }
    }
    return res;
  };

  // Function to convert JSON data (object or array) to CSV format.
  const jsonToCSV = (data) => {
    let csv = "";
    const isArray = Array.isArray(data);

    if (isArray) {
      const flattenedData = data.map((item) => flattenObject(item));
      // Get all unique keys across all objects.
      const headers = Array.from(
        new Set(flattenedData.reduce((acc, curr) => acc.concat(Object.keys(curr)), []))
      );
      csv += headers.join(",") + "\n";
      flattenedData.forEach((row) => {
        const rowData = headers.map((header) => {
          const cell = row[header] !== undefined ? row[header] : "";
          return `"${cell.toString().replace(/"/g, '""')}"`;
        });
        csv += rowData.join(",") + "\n";
      });
    } else {
      const flattenedData = flattenObject(data);
      const headers = Object.keys(flattenedData);
      csv += headers.join(",") + "\n";
      const rowData = headers.map((header) =>
        `"${flattenedData[header].toString().replace(/"/g, '""')}"`
      );
      csv += rowData.join(",") + "\n";
    }
    return csv;
  };

  // Trigger CSV download
  const downloadCSV = () => {
    if (!parsedData) return;
    const csvContent = jsonToCSV(parsedData);
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "output.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="results">
      <h3>Results</h3>
      {loading && <p>Loading...</p>}
      {parsedData && (
        <div style={{ marginBottom: "10px" }}>
          <button className="submit-btn" onClick={downloadCSV}>
            Download CSV
          </button>
        </div>
      )}
      <div className="scrollable-results">
        {parsedData && (
          <div className="data-container">
            <JsonRenderer
              data={parsedData}
              expandedSections={expandedSections}
              toggleSection={toggleSection}
              labelMappings={{
                candidate_name: "Name",
                email_address: "Email",
                phone_number: "Phone",
                work_experience: "Work Experience",
                educations_duration: "Education Duration",
                experiences: "Experience",
                educations: "Education",
                social_urls: "Social Links",
                skills: "Skills",
                job_title: "Job Title",
                job_description: "Job Description",
                required_skills: "Required Skills",
                min_work_experience: "Minimum Experience",
                enhanced_job_description: "Enhanced Job Description",
                generated_candidates: "Generated Candidates",
                resume_score: "Resume Score",
                gap_analysis: "Gap Analysis",
                candidate_summary: "Candidate Summary",
                closest_sample_candidate: "Closest Candidate",
                recommendations: "Recommendations",
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default ResultsPanel;
