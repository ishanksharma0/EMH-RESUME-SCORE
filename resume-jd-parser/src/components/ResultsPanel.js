import React from "react";
import "../App.css";
import JsonRenderer from "./JsonRenderer";

function ResultsPanel({ parsedData, loading, expandedSections, toggleSection }) {
  return (
    <div className="results">
      <h3>Results</h3>
      {loading && <p>Loading...</p>}

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
