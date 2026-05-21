from app.classification.classifier import classify_job


class TestFunctionClassification:
    def test_engineer(self):
        result = classify_job("Software Engineer", "Build things", None)
        assert result.function == "Eng"

    def test_data_scientist(self):
        result = classify_job("Data Scientist", "Analyze data", None)
        assert result.function == "Data"

    def test_product_manager(self):
        result = classify_job("Product Manager", "Lead product", None)
        assert result.function == "Product"

    def test_designer(self):
        result = classify_job("UX Designer", "Design interfaces", None)
        assert result.function == "Design"

    def test_sales(self):
        result = classify_job("Account Executive", "Sell products", None)
        assert result.function == "Sales"

    def test_clinical(self):
        result = classify_job("Clinical Specialist", "Patient care", None)
        assert result.function == "Clinical"

    def test_compliance(self):
        result = classify_job("Compliance Analyst", "Regulatory work", None)
        assert result.function == "Compliance"

    def test_ops(self):
        result = classify_job("Recruiting Lead", "Talent operations", None)
        assert result.function == "Ops"

    def test_other_default(self):
        result = classify_job("Chief of Staff", "Strategy", None)
        assert result.function == "Other"

    def test_function_matches_description(self):
        result = classify_job("Team Lead", "Looking for a backend engineer", None)
        assert result.function == "Eng"


class TestSeniorityClassification:
    def test_vp_beats_senior(self):
        result = classify_job("VP of Senior Engineering", "", None)
        assert result.seniority == "VP"

    def test_c_suite(self):
        result = classify_job("Chief Technology Officer", "", None)
        assert result.seniority == "C-Suite"

    def test_director(self):
        result = classify_job("Director of Engineering", "", None)
        assert result.seniority == "Director"

    def test_senior(self):
        result = classify_job("Senior Engineer", "", None)
        assert result.seniority == "Senior"

    def test_junior(self):
        result = classify_job("Junior Developer", "", None)
        assert result.seniority == "Junior"

    def test_mid_default(self):
        result = classify_job("Software Engineer", "", None)
        assert result.seniority == "Mid"

    def test_staff(self):
        result = classify_job("Staff Engineer", "", None)
        assert result.seniority == "Staff"

    def test_principal(self):
        result = classify_job("Principal Engineer", "", None)
        assert result.seniority == "Principal"


class TestSeniorityTrack:
    def test_product_manager_is_mgmt(self):
        result = classify_job("Product Manager", "Lead product", None)
        assert result.function == "Product"
        assert result.seniority == "Manager"
        assert result.seniority_track == "Mgmt"

    def test_engineer_is_ic(self):
        result = classify_job("Senior Engineer", "", None)
        assert result.seniority_track == "IC"

    def test_director_is_mgmt(self):
        result = classify_job("Director of Sales", "", None)
        assert result.seniority_track == "Mgmt"

    def test_vp_is_mgmt(self):
        result = classify_job("VP Product", "", None)
        assert result.seniority_track == "Mgmt"


class TestGeographyClassification:
    def test_remote(self):
        result = classify_job("Engineer", "", "Remote")
        assert result.geography == "Remote"

    def test_us_west(self):
        result = classify_job("Engineer", "", "San Francisco, CA")
        assert result.geography == "US-West"

    def test_us_east(self):
        result = classify_job("Engineer", "", "New York, NY")
        assert result.geography == "US-East"

    def test_us_central(self):
        result = classify_job("Engineer", "", "Austin, TX")
        assert result.geography == "US-Central"

    def test_other_default(self):
        result = classify_job("Engineer", "", "London, UK")
        assert result.geography == "Other"

    def test_none_location(self):
        result = classify_job("Engineer", "", None)
        assert result.geography == "Other"


class TestDomainKeywords:
    def test_single_domain(self):
        result = classify_job("Engineer", "Work on HIPAA compliance", None)
        assert "hipaa" in result.domain_tags

    def test_multiple_domains(self):
        result = classify_job("Engineer", "Work with FHIR and EHR systems for payer integration", None)
        assert "fhir" in result.domain_tags
        assert "ehr" in result.domain_tags
        assert "payer" in result.domain_tags

    def test_no_domain(self):
        result = classify_job("Engineer", "Build web apps", None)
        assert result.domain_tags == []

    def test_prior_auth(self):
        result = classify_job("Engineer", "Automate prior auth workflows", None)
        assert "prior_auth" in result.domain_tags

    def test_rcm(self):
        result = classify_job("Analyst", "Revenue cycle management", None)
        assert "rcm" in result.domain_tags
