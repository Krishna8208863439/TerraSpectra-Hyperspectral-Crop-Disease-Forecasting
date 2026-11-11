import csv
import io
from datetime import datetime
from typing import Dict, Any
from fastapi.responses import Response

class ReportExportEngine:
    """
    Export engine supporting scientific agronomic report generation in CSV and PDF-ready HTML.
    """

    @staticmethod
    def generate_csv_report(analysis_data: Dict[str, Any], forecast_data: Dict[str, Any] = None) -> Response:
        """
        Generates a tabular CSV summary of specimen diagnosis, narrowband indices, and risk forecast.
        """
        diag = analysis_data.get("diagnosis", {})
        indices = analysis_data.get("indices") or analysis_data.get("spectral_indices", {})
        stress = analysis_data.get("stress") or analysis_data.get("early_stress", {})
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Metadata Header
        writer.writerow(["TERRASPECTRA RESEARCH EXPORT REPORT"])
        writer.writerow(["Generated Timestamp", datetime.now().isoformat()])
        writer.writerow(["Specimen / Sample", analysis_data.get("sample_name", "Hyperspectral Specimen")])
        writer.writerow([])

        # Section 1: Classification & Diagnostic Summary
        writer.writerow(["--- 1. DIAGNOSTIC ASSESSMENT ---"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Predicted Condition", diag.get("predicted_condition", "N/A")])
        writer.writerow(["Model Confidence", f"{diag.get('confidence', 0.0) * 100:.2f}%"])
        writer.writerow(["Is Healthy Specimen", str(diag.get("is_healthy", False))])
        writer.writerow(["Severity Level", diag.get("severity", "None")])
        writer.writerow(["Ensemble Agreement", str(diag.get("ensemble_agreement", True))])
        writer.writerow(["Scientific Rationale", diag.get("scientific_rationale", "")])
        writer.writerow([])

        # Section 2: Narrowband Indices
        writer.writerow(["--- 2. NARROWBAND VEGETATION INDICES ---"])
        writer.writerow(["Index Code", "Value", "Description"])
        writer.writerow(["NDVI", indices.get("NDVI", 0.0), "Normalized Difference Vegetation Index (800nm vs 670nm)"])
        writer.writerow(["NDRE", indices.get("NDRE", 0.0), "Red-Edge Vegetation Index (790nm vs 720nm)"])
        writer.writerow(["PRI", indices.get("PRI", 0.0), "Photochemical Reflectance Index (531nm vs 570nm)"])
        writer.writerow(["WBI", indices.get("WBI", 0.0), "Water Band Index (900nm vs 970nm)"])
        writer.writerow(["PSRI", indices.get("PSRI", 0.0), "Plant Senescence Reflectance Index"])
        writer.writerow(["MCARI", indices.get("MCARI", 0.0), "Modified Chlorophyll Absorption in Reflectance"])
        writer.writerow([])

        # Section 3: Early Stress Analysis
        writer.writerow(["--- 3. EARLY PRE-SYMPTOMATIC STRESS ---"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Composite Stress Score", f"{stress.get('composite_stress_score', 0.0) * 100:.1f}%"])
        writer.writerow(["Stress Classification", stress.get("stress_level", "Nominal")])
        writer.writerow(["Dominant Factor", stress.get("dominant_stress_factor", "None")])
        writer.writerow(["Water Deficit Index", stress.get("water_stress_index", 0.0)])
        writer.writerow(["Chlorophyll Breakdown Index", stress.get("chlorophyll_stress_index", 0.0)])
        writer.writerow([])

        # Section 4: 7-Day Forecast Trajectory
        if forecast_data and "trajectory" in forecast_data:
            writer.writerow(["--- 4. 7-DAY EPIDEMIOLOGICAL FORECAST ---"])
            writer.writerow(["Day", "Date", "Projected Risk", "CI Lower", "CI Upper", "Risk Category", "Avg Temp (C)", "Humidity (%)"])
            for day in forecast_data["trajectory"]:
                writer.writerow([
                    f"Day {day.get('day')}",
                    day.get("date"),
                    f"{day.get('projected_risk', 0.0) * 100:.1f}%",
                    f"{day.get('confidence_lower', 0.0) * 100:.1f}%",
                    f"{day.get('confidence_upper', 0.0) * 100:.1f}%",
                    day.get("risk_category"),
                    day.get("temp_c"),
                    day.get("humidity_pct")
                ])

        csv_content = output.getvalue()
        output.close()

        filename = f"TerraSpectra_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

