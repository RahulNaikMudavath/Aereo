import io
import zipfile
import pytest


def test_health_check(client):
    """Test health check and root endpoints."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_home = client.get("/")
    assert res_home.status_code == 200
    assert "Bulk Certificate Generator" in res_home.text


def test_input_validation(client):
    """Test rejection of invalid top-level inputs."""
    # 1. Missing event_name
    res = client.post("/api/jobs/", json={
        "recipients": [{"name": "Alice"}]
    })
    assert res.status_code == 422

    # 2. Empty recipients list
    res = client.post("/api/jobs/", json={
        "event_name": "Python Bootcamp",
        "recipients": []
    })
    assert res.status_code == 422

    # 3. Invalid file format
    res = client.post("/api/jobs/", json={
        "event_name": "Python Bootcamp",
        "file_format": "docx",
        "recipients": [{"name": "Alice"}]
    })
    assert res.status_code == 422


def test_create_and_generate_certificates_asynchronously(client):
    """Test asynchronous background processing via FastAPI BackgroundTasks."""
    payload = {
        "event_name": "Async Python Mastery",
        "issuer_name": "Async Academy",
        "recipients": [
            {"name": "Grace Hopper", "email": "grace@example.com"}
        ]
    }

    # Submit without sync parameter (default is async background tasks)
    response = client.post("/api/jobs/", json=payload)
    assert response.status_code == 202
    initial_data = response.json()
    job_id = initial_data["id"]

    # When TestClient finishes the request, FastAPI executes background tasks.
    # Check the updated job status via GET /api/jobs/{job_id}
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    final_data = status_res.json()

    assert final_data["status"] == "COMPLETED"
    assert final_data["success_count"] == 1
    assert final_data["failed_count"] == 0
    assert len(final_data["certificates"]) == 1
    assert final_data["certificates"][0]["status"] == "COMPLETED"


def test_create_and_generate_certificates_synchronously(client):
    """Test end-to-end job creation and certificate generation."""
    payload = {
        "event_name": "Backend Development Mastery",
        "issuer_name": "Dev Institute",
        "issue_date": "2026-10-07",
        "file_format": "pdf",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"}
        ]
    }

    # Submit with sync=True
    response = client.post("/api/jobs/?sync=true", json=payload)
    assert response.status_code == 202
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["total_count"] == 2
    assert data["success_count"] == 2
    assert data["failed_count"] == 0
    assert len(data["certificates"]) == 2

    for cert in data["certificates"]:
        assert cert["status"] == "COMPLETED"
        assert cert["download_url"] is not None
        assert cert["error_message"] is None


def test_job_status_endpoint(client):
    """Test tracking job progress via GET /api/jobs/{id}."""
    payload = {
        "event_name": "FastAPI Workshop",
        "issuer_name": "Cloud Academy",
        "recipients": [
            {"name": "Charlie Brown", "email": "charlie@example.com"}
        ]
    }
    create_res = client.post("/api/jobs/?sync=true", json=payload)
    job_id = create_res.json()["id"]

    # Poll status
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    assert job_data["id"] == job_id
    assert job_data["event_name"] == "FastAPI Workshop"
    assert job_data["status"] == "COMPLETED"
    assert job_data["success_count"] == 1


def test_individual_failure_isolation(client):
    """
    CRITICAL REQUIREMENT:
    A failure while generating one certificate should NOT prevent
    other valid certificates in the same job from being generated.
    """
    payload = {
        "event_name": "Data Science Conference",
        "issuer_name": "Data Institute",
        "recipients": [
            {"name": "Valid Recipient One", "email": "valid1@example.com"},
            {"name": "", "email": "invalid-no-name@example.com"},  # Fails: empty name
            {"name": "Valid Recipient Two", "email": "valid2@example.com"},
            {"name": "Broken Email User", "email": "bad_email_without_domain"},  # Fails: bad email
            {"name": "Valid Recipient Three", "email": "valid3@example.com"}
        ]
    }

    response = client.post("/api/jobs/?sync=true", json=payload)
    assert response.status_code == 202
    data = response.json()

    # Overall job status should be PARTIALLY_COMPLETED
    assert data["status"] == "PARTIALLY_COMPLETED"
    assert data["total_count"] == 5
    assert data["success_count"] == 3
    assert data["failed_count"] == 2

    # Check individual certificates
    results_by_name = {c["recipient_name"]: c for c in data["certificates"]}

    # Valid recipients succeeded
    assert results_by_name["Valid Recipient One"]["status"] == "COMPLETED"
    assert results_by_name["Valid Recipient One"]["download_url"] is not None

    assert results_by_name["Valid Recipient Two"]["status"] == "COMPLETED"
    assert results_by_name["Valid Recipient Three"]["status"] == "COMPLETED"

    # Failed recipients isolated with error descriptions
    assert results_by_name[""]["status"] == "FAILED"
    assert "Invalid Recipient: Name cannot be empty" in results_by_name[""]["error_message"]

    assert results_by_name["Broken Email User"]["status"] == "FAILED"
    assert "not a valid email" in results_by_name["Broken Email User"]["error_message"]


def test_download_individual_certificate(client):
    """Test downloading an individual generated certificate."""
    payload = {
        "event_name": "Certificate Retrieval Test",
        "issuer_name": "Test Org",
        "file_format": "pdf",
        "recipients": [{"name": "Diana Prince", "email": "diana@example.com"}]
    }

    create_res = client.post("/api/jobs/?sync=true", json=payload)
    cert_id = create_res.json()["certificates"][0]["id"]

    # Download certificate
    dl_res = client.get(f"/api/certificates/{cert_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 1000  # valid PDF binary content


def test_download_all_certificates_zip(client):
    """Test packaging and downloading all certificates as a ZIP archive."""
    payload = {
        "event_name": "Bulk Zip Download Event",
        "issuer_name": "Testing Academy",
        "file_format": "png",
        "recipients": [
            {"name": "Participant One", "email": "p1@example.com"},
            {"name": "Participant Two", "email": "p2@example.com"}
        ]
    }

    create_res = client.post("/api/jobs/?sync=true", json=payload)
    job_id = create_res.json()["id"]

    # Download ZIP
    zip_res = client.get(f"/api/jobs/{job_id}/download-all")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Validate ZIP content in-memory
    with zipfile.ZipFile(io.BytesIO(zip_res.content)) as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        assert any("Participant_One" in fname for fname in file_list)
        assert any("Participant_Two" in fname for fname in file_list)


def test_verify_certificate_endpoint(client):
    """Test the certificate verification endpoint."""
    payload = {
        "event_name": "Security and Verification Seminar",
        "issuer_name": "Trust Lab",
        "recipients": [{"name": "Bruce Wayne", "email": "bruce@example.com"}]
    }

    create_res = client.post("/api/jobs/?sync=true", json=payload)
    cert_id = create_res.json()["certificates"][0]["id"]

    # Verify valid certificate
    verify_res = client.get(f"/api/certificates/{cert_id}/verify")
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["valid"] is True
    assert vdata["recipient_name"] == "Bruce Wayne"
    assert vdata["issuer_name"] == "Trust Lab"

    # Verify non-existent certificate
    bogus_res = client.get("/api/certificates/non-existent-id/verify")
    assert bogus_res.status_code == 200
    assert bogus_res.json()["valid"] is False
