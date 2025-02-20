import React, { useState } from "react";
import "./App.css";
import "bootstrap/dist/css/bootstrap.min.css";
import axios from "axios";

function App() {
  const [parsedData, setParsedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const [selectedApi, setSelectedApi] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState(null);
  const [additionalInput, setAdditionalInput] = useState(""); // New state for additional user input

  const apiOptions = [
    { id: "parse-resume", label: "Parse Resume" },
    { id: "parse-job-description", label: "Parse Job Description" },
    { id: "job-description-enhance", label: "Enhance JD" },
    { id: "score-resumes", label: "Score Resumes" },
  ];

  const toggleSection = (key) => {
    setExpandedSections((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleFileUpload = (event) => {
    setUploadedFiles(event.target.files);
  };

  const handleApiSelection = (apiId) => {
    setSelectedApi(apiId);
    setUploadedFiles(null);
    setParsedData(null);
    setError(null);
  };

  const handleSubmit = async () => {
    if (!uploadedFiles || uploadedFiles.length === 0) {
      setError("Please upload a file.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    for (let file of uploadedFiles) {
      formData.append(selectedApi === "score-resumes" ? "files" : "file", file);
    }

    // Include user input for scoring API
    if (selectedApi === "score-resumes") {
      formData.append("user_input", additionalInput);
    }

    try {
      const response = await axios.post(
        `http://localhost:8000/api/${selectedApi}/`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setParsedData(response.data);
    } catch (err) {
      setError("Error processing file.");
    } finally {
      setLoading(false);
    }
  };

  const labelMappings = {
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
  };

  const renderJsonData = (data, parentKey = "") => {
    if (!data) return null;

    return Object.entries(data).map(([key, value]) => {
      if (key === "vectorized_jd" || key === "logo") return null; // Exclude vectorized JD & logo
      let label = labelMappings[key] || key.replace(/_/g, " ").toUpperCase();
      let isExpanded = expandedSections[`${parentKey}${key}`];

      return (
        <div key={key} className="section">
          {Array.isArray(value) &&
          value.length > 0 &&
          typeof value[0] === "object" ? (
            <>
              <button
                className="collapsible"
                onClick={() => toggleSection(`${parentKey}${key}`)}
              >
                {label} {isExpanded ? "▲" : "▼"}
              </button>
              {isExpanded && (
                <div className="content">
                  {value.map((item, index) => (
                    <div key={index} className="nested-box">
                      <button
                        className="collapsible"
                        onClick={() =>
                          toggleSection(`${parentKey}${key}[${index}]`)
                        }
                      >
                        {label} {index + 1}{" "}
                        {expandedSections[`${parentKey}${key}[${index}]`]
                          ? "▲"
                          : "▼"}
                      </button>
                      {expandedSections[`${parentKey}${key}[${index}]`] &&
                        renderJsonData(item, `${parentKey}${key}[${index}].`)}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : typeof value === "object" ? (
            <>
              <button
                className="collapsible"
                onClick={() => toggleSection(`${parentKey}${key}`)}
              >
                {label} {isExpanded ? "▲" : "▼"}
              </button>
              {isExpanded && (
                <div className="content">
                  {renderJsonData(value, `${parentKey}${key}.`)}
                </div>
              )}
            </>
          ) : (
            <div className="subsection">
              <h4>{label}</h4>
              {typeof value === "string" && value.length > 50 ? (
                <textarea className="input-box" defaultValue={value} readOnly />
              ) : (
                <input
                  type="text"
                  className="input-box"
                  defaultValue={value}
                  readOnly
                />
              )}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className="container-fluid d-flex h-100">
      <nav className="sidebar">
        <h2 className="logo">JD Parser</h2>
        {apiOptions.map((option) => (
          <button
            key={option.id}
            className={`nav-btn ${selectedApi === option.id ? "active" : ""}`}
            onClick={() => handleApiSelection(option.id)}
          >
            {option.label}
          </button>
        ))}
      </nav>

      <main className="main-content">
        {selectedApi ? (
          <div className="upload-section">
            <h3>{apiOptions.find((opt) => opt.id === selectedApi)?.label}</h3>
            <div className="drop-zone">
              <input
                type="file"
                multiple={selectedApi === "score-resumes"}
                onChange={handleFileUpload}
              />
              <p>Drag & drop files here or click to upload</p>
            </div>

            {/* Additional Input for Resume Scoring */}
            {selectedApi === "score-resumes" && (
              <textarea
                placeholder="Enter additional requirements (e.g., 'Candidate should have DevOps experience')"
                value={additionalInput}
                onChange={(e) => setAdditionalInput(e.target.value)}
                rows="4"
                className="input-box"
              />
            )}

            <button
              className="submit-btn"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? "Processing..." : "Submit"}
            </button>
            {error && <p className="error">{error}</p>}
          </div>
        ) : (
          <h2 className="placeholder-text">
            Select an API option from the left
          </h2>
        )}
      </main>

      <aside className="results">
        <h3>Results</h3>
        {loading && <p>Loading...</p>}
        <div className="scrollable-results">
          {parsedData && (
            <div className="data-container">{renderJsonData(parsedData)}</div>
          )}
        </div>
      </aside>
    </div>
  );
}

export default App;
