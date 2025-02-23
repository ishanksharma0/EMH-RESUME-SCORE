import React from "react";
import "../App.css";

function FileUploader({
  selectedApi,
  onFileUpload,
  onSubmit,
  loading,
  error,
  additionalInput,
  setAdditionalInput,
}) {
  // small helper for heading
  const getApiLabel = () => {
    switch (selectedApi) {
      case "parse-resume":
        return "Parse Resume";
      case "parse-job-description":
        return "Parse Job Description";
      case "job-description-enhance":
        return "Enhance JD";
      case "score-resumes":
        return "Score Resumes";
      default:
        return "";
    }
  };

  return (
    <div className="upload-section">
      <h3>{getApiLabel()}</h3>

      <div className="drop-zone">
        <input
          type="file"
          multiple={selectedApi === "score-resumes"}
          onChange={onFileUpload}
        />
        <p>Drag & drop files here or click to upload</p>
      </div>

      {selectedApi === "score-resumes" && (
        <textarea
          placeholder="Additional requirements (e.g. 'DevOps experience')"
          value={additionalInput}
          onChange={(e) => setAdditionalInput(e.target.value)}
          rows="4"
          className="input-box"
        />
      )}

      <button className="submit-btn" onClick={onSubmit} disabled={loading}>
        {loading ? "Processing..." : "Submit"}
      </button>

      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default FileUploader;
