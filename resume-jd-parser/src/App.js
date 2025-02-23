import React, { useState } from "react";
import axios from "axios";
import "bootstrap/dist/css/bootstrap.min.css";
import "./App.css";

// Import your components
import Sidebar from "./components/Sidebar";
import FileUploader from "./components/FileUploader";
import ResultsPanel from "./components/ResultsPanel";

function App() {
  const [parsedData, setParsedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const [selectedApi, setSelectedApi] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState(null);
  const [additionalInput, setAdditionalInput] = useState("");

  // Options for left sidebar
  const apiOptions = [
    { id: "parse-resume", label: "Parse Resume" },
    { id: "parse-job-description", label: "Parse Job Description" },
    { id: "job-description-enhance", label: "Enhance JD" },
    { id: "score-resumes", label: "Score Resumes" },
  ];

  // Toggle collapsible sections in the JSON rendering
  const toggleSection = (key) => {
    setExpandedSections((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // On file selection
  const handleFileUpload = (event) => {
    setUploadedFiles(event.target.files);
  };

  // On selecting an API from the sidebar
  const handleApiSelection = (apiId) => {
    setSelectedApi(apiId);
    setUploadedFiles(null);
    setParsedData(null);
    setError(null);
  };

  // Submitting files to the server
  const handleSubmit = async () => {
    if (!uploadedFiles || uploadedFiles.length === 0) {
      setError("Please upload a file.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      for (let file of uploadedFiles) {
        formData.append(
          selectedApi === "score-resumes" ? "files" : "file",
          file
        );
      }

      if (selectedApi === "score-resumes") {
        formData.append("user_input", additionalInput);
      }

      const response = await axios.post(
        `http://localhost:8000/api/${selectedApi}/`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      setParsedData(response.data);
    } catch (err) {
      console.error(err);
      setError("Error processing file.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-fluid">
      {/* Left: Sidebar with marine/royal green background */}
      <Sidebar
        apiOptions={apiOptions}
        selectedApi={selectedApi}
        onApiSelect={handleApiSelection}
      />

      {/* Middle: Uploader or placeholder text */}
      <div className="main-center">
        {selectedApi ? (
          <FileUploader
            selectedApi={selectedApi}
            onFileUpload={handleFileUpload}
            onSubmit={handleSubmit}
            loading={loading}
            error={error}
            additionalInput={additionalInput}
            setAdditionalInput={setAdditionalInput}
          />
        ) : (
          <h2 className="placeholder-text">Select an API option from the left</h2>
        )}
      </div>

      {/* Right: Results Panel */}
      <ResultsPanel
        parsedData={parsedData}
        loading={loading}
        expandedSections={expandedSections}
        toggleSection={toggleSection}
      />
    </div>
  );
}

export default App;
