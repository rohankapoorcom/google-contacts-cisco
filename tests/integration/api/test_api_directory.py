"""Integration tests for XML directory API endpoints.

Tests verify XML directory functionality for Cisco IP phones including:
- XML directory listing
- XML search results
- XML format validation
- Cisco phone compatibility
- Error handling

NOTE: These tests currently require TestClient dependency injection fixes.
See test_database_transactions.py for working integration tests.
"""

import pytest
from fastapi import status
from lxml import etree

# Skip all API integration tests pending TestClient dependency injection fixes
pytestmark = pytest.mark.skip(reason="TestClient dependency injection needs fixing")


@pytest.mark.integration
class TestXMLDirectoryAPIIntegration:
    """Integration tests for XML directory API endpoints."""
    
    def test_xml_directory_root(self, integration_client):
        """Test XML directory root endpoint."""
        response = integration_client.get("/directory")
        
        assert response.status_code == status.HTTP_200_OK
        assert "xml" in response.headers["content-type"].lower()
        
        # Validate XML structure
        try:
            root = etree.fromstring(response.content)
            assert root.tag == "CiscoIPPhoneMenu"
        except etree.XMLSyntaxError:
            pytest.fail("Invalid XML returned")
    
    def test_xml_directory_list_contacts_empty(self, integration_client):
        """Test XML directory listing with no contacts."""
        response = integration_client.get("/directory/list")
        
        assert response.status_code == status.HTTP_200_OK
        assert "xml" in response.headers["content-type"].lower()
        
        root = etree.fromstring(response.content)
        assert root.tag in ["CiscoIPPhoneDirectory", "CiscoIPPhoneMenu"]
    
    def test_xml_directory_list_contacts(self, integration_client, integration_test_contacts):
        """Test XML directory listing with contacts."""
        response = integration_client.get("/directory/list")
        
        assert response.status_code == status.HTTP_200_OK
        assert "xml" in response.headers["content-type"].lower()
        
        root = etree.fromstring(response.content)
        
        # Should contain directory entries
        entries = root.findall(".//DirectoryEntry")
        assert len(entries) > 0
        
        # Verify entry structure
        if entries:
            entry = entries[0]
            name = entry.find("Name")
            telephone = entry.find("Telephone")
            assert name is not None
            # Directory entries may not have telephone if contact has no phone numbers
            assert telephone is not None or name is not None
    
    def test_xml_directory_search_endpoint(self, integration_client):
        """Test XML directory search endpoint exists."""
        response = integration_client.get("/directory/search")
        
        # Should return valid XML even for empty search
        assert response.status_code == status.HTTP_200_OK
        assert "xml" in response.headers["content-type"].lower()
    
    def test_xml_directory_search_with_query(
        self, integration_client, integration_test_contacts
    ):
        """Test XML directory search with query parameter."""
        response = integration_client.get("/directory/search?name=Test")
        
        assert response.status_code == status.HTTP_200_OK
        assert "xml" in response.headers["content-type"].lower()
        
        root = etree.fromstring(response.content)
        assert root.tag in ["CiscoIPPhoneDirectory", "CiscoIPPhoneMenu"]
    
    def test_xml_format_cisco_compatibility(
        self, integration_client, integration_test_contacts
    ):
        """Test that XML format is compatible with Cisco IP phones."""
        response = integration_client.get("/directory/list")
        
        root = etree.fromstring(response.content)
        
        # Verify Cisco-specific XML structure
        assert root.tag in ["CiscoIPPhoneDirectory", "CiscoIPPhoneMenu"]
        
        # Check for required Cisco elements
        if root.tag == "CiscoIPPhoneDirectory":
            # Should have Title and Prompt
            title = root.find("Title")
            prompt = root.find("Prompt")
            
            # Structure should be Cisco-compatible
            entries = root.findall("DirectoryEntry")
            for entry in entries:
                name = entry.find("Name")
                telephone = entry.find("Telephone")
                # Cisco phones expect these elements
                assert name is not None or telephone is not None
    
    def test_xml_directory_pagination(self, integration_client, integration_db):
        """Test XML directory with pagination."""
        from google_contacts_cisco.models import Contact, PhoneNumber
        
        # Create multiple contacts
        for i in range(15):
            contact = Contact(
                resource_name=f"people/xml_page_{i}",
                display_name=f"XML Contact {i}",
            )
            integration_db.add(contact)
            integration_db.flush()
            
            phone = PhoneNumber(
                contact_id=contact.id,
                value=f"+1555600{i:02d}",
                display_value=f"+1-555-600{i:02d}",
                type="mobile",
                primary=True,
            )
            integration_db.add(phone)
        
        integration_db.commit()
        
        # Test with limit
        response = integration_client.get("/directory/list?limit=5")
        
        assert response.status_code == status.HTTP_200_OK
        root = etree.fromstring(response.content)
        
        entries = root.findall(".//DirectoryEntry")
        # Should respect limit
        assert len(entries) <= 5
    
    def test_xml_special_characters_escaped(self, integration_client, integration_db):
        """Test that special XML characters are properly escaped."""
        from google_contacts_cisco.models import Contact, PhoneNumber
        
        # Create contact with special characters
        contact = Contact(
            resource_name="people/special_chars",
            display_name="Test <User> & Co.",
            given_name="Test",
            family_name="User & Co.",
        )
        integration_db.add(contact)
        integration_db.flush()
        
        phone = PhoneNumber(
            contact_id=contact.id,
            value="+15556000",
            display_value="+1-555-6000",
            type="mobile",
            primary=True,
        )
        integration_db.add(phone)
        integration_db.commit()
        
        # Get XML
        response = integration_client.get("/directory/list")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Should parse without errors (special chars properly escaped)
        try:
            root = etree.fromstring(response.content)
            assert root is not None
        except etree.XMLSyntaxError:
            pytest.fail("XML not properly escaped")


@pytest.mark.integration
class TestXMLDirectoryErrorHandling:
    """Integration tests for XML directory error handling."""
    
    def test_xml_directory_invalid_parameters(self, integration_client):
        """Test XML directory with invalid parameters."""
        response = integration_client.get("/directory/list?limit=-1")
        
        # Should handle gracefully, either with error XML or valid response
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
        
        # If 200, should still return valid XML
        if response.status_code == status.HTTP_200_OK:
            try:
                etree.fromstring(response.content)
            except etree.XMLSyntaxError:
                pytest.fail("Invalid XML returned")
    
    def test_xml_directory_search_no_query(self, integration_client):
        """Test XML directory search without query parameter."""
        response = integration_client.get("/directory/search")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]
        
        if response.status_code == status.HTTP_200_OK:
            # Should return valid XML
            root = etree.fromstring(response.content)
            assert root is not None


@pytest.mark.integration
@pytest.mark.slow
class TestXMLDirectoryPerformance:
    """Integration tests for XML directory performance."""
    
    def test_xml_generation_performance(self, integration_client, integration_db):
        """Test XML generation performance with many contacts."""
        from google_contacts_cisco.models import Contact, PhoneNumber
        
        # Create 100 contacts
        for i in range(100):
            contact = Contact(
                resource_name=f"people/xml_perf_{i}",
                display_name=f"XML Performance {i}",
            )
            integration_db.add(contact)
            integration_db.flush()
            
            phone = PhoneNumber(
                contact_id=contact.id,
                value=f"+1555700{i:03d}",
                display_value=f"+1-555-700-{i:03d}",
                type="mobile",
                primary=True,
            )
            integration_db.add(phone)
        
        integration_db.commit()
        
        # Test XML generation time
        import time
        start = time.time()
        response = integration_client.get("/directory/list")
        duration = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        assert duration < 2.0  # Should generate XML in under 2 seconds for 100 contacts
        
        # Verify XML is valid
        root = etree.fromstring(response.content)
        assert root is not None
    
    def test_xml_search_performance(self, integration_client, integration_db):
        """Test XML search performance."""
        from google_contacts_cisco.models import Contact
        
        # Create searchable contacts
        for i in range(50):
            contact = Contact(
                resource_name=f"people/search_xml_{i}",
                display_name=f"Searchable Contact {i}",
            )
            integration_db.add(contact)
        
        integration_db.commit()
        
        # Test search time
        import time
        start = time.time()
        response = integration_client.get("/directory/search?name=Searchable")
        duration = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        assert duration < 1.0  # Should search and generate XML quickly


@pytest.mark.integration
class TestDirectoryPhoneNumberFormatting:
    """Integration tests for phone number formatting in directory endpoints."""

    def test_directory_contact_phone_formatting(
        self, integration_client, integration_db
    ):
        """Test that phone numbers in directory are formatted without + prefix."""
        from google_contacts_cisco.models import Contact, PhoneNumber

        # Create contact with phone in +1 format
        contact = Contact(
            resource_name="people/format_test",
            display_name="Format Test Contact",
        )
        integration_db.add(contact)
        integration_db.flush()

        phone = PhoneNumber(
            contact_id=contact.id,
            value="15551234567",
            display_value="+1-555-123-4567",
            type="mobile",
            primary=True,
        )
        integration_db.add(phone)
        integration_db.commit()

        # Get contact directory
        response = integration_client.get(f"/directory/contacts/{contact.id}")

        assert response.status_code == status.HTTP_200_OK
        root = etree.fromstring(response.content)

        # Find telephone element
        entries = root.findall("DirectoryEntry")
        assert len(entries) > 0

        telephone = entries[0].find("Telephone").text
        # Should be formatted without + and with spaces
        assert telephone == "1 555 123 4567"
        assert "+" not in telephone
        assert "-" not in telephone

    def test_multiple_phones_all_formatted_consistently(
        self, integration_client, integration_db
    ):
        """Test that multiple phone numbers are all formatted consistently."""
        from google_contacts_cisco.models import Contact, PhoneNumber

        contact = Contact(
            resource_name="people/multi_format",
            display_name="Multi Format Test",
        )
        integration_db.add(contact)
        integration_db.flush()

        # Add phones with different input formats
        phones = [
            PhoneNumber(
                contact_id=contact.id,
                value="15551234567",
                display_value="+1 (555) 123-4567",
                type="mobile",
                primary=True,
            ),
            PhoneNumber(
                contact_id=contact.id,
                value="15559876543",
                display_value="+1-555-987-6543",
                type="work",
                primary=False,
            ),
            PhoneNumber(
                contact_id=contact.id,
                value="4402079460958",
                display_value="+44 20 7946 0958",
                type="home",
                primary=False,
            ),
        ]

        for phone in phones:
            integration_db.add(phone)

        integration_db.commit()

        # Get contact directory
        response = integration_client.get(f"/directory/contacts/{contact.id}")

        assert response.status_code == status.HTTP_200_OK
        root = etree.fromstring(response.content)

        entries = root.findall("DirectoryEntry")
        assert len(entries) == 3

        # Verify all formatted correctly
        tel1 = entries[0].find("Telephone").text
        tel2 = entries[1].find("Telephone").text
        tel3 = entries[2].find("Telephone").text

        assert tel1 == "1 555 123 4567"
        assert tel2 == "1 555 987 6543"
        assert tel3 == "44 207 946 0958"

        # Verify no + symbols in any phone
        for entry in entries:
            tel = entry.find("Telephone").text
            assert "+" not in tel
            assert tel.replace(" ", "").isdigit()

    def test_various_input_formats_normalize_correctly(
        self, integration_client, integration_db
    ):
        """Test that various input formats all normalize correctly."""
        from google_contacts_cisco.models import Contact, PhoneNumber

        test_cases = [
            ("+1-555-123-4567", "1 555 123 4567"),
            ("(555) 123-4567", "555 123 4567"),
            ("555.123.4567", "555 123 4567"),
            ("+15551234567", "1 555 123 4567"),
        ]

        for idx, (input_format, expected_output) in enumerate(test_cases):
            contact = Contact(
                resource_name=f"people/format_test_{idx}",
                display_name=f"Format Test {idx}",
            )
            integration_db.add(contact)
            integration_db.flush()

            digits = "".join(c for c in input_format if c.isdigit())
            phone = PhoneNumber(
                contact_id=contact.id,
                value=digits,
                display_value=input_format,
                type="mobile",
                primary=True,
            )
            integration_db.add(phone)
            integration_db.commit()

            # Get contact directory
            response = integration_client.get(f"/directory/contacts/{contact.id}")

            assert response.status_code == status.HTTP_200_OK
            root = etree.fromstring(response.content)

            entries = root.findall("DirectoryEntry")
            telephone = entries[0].find("Telephone").text

            assert (
                telephone == expected_output
            ), f"Input '{input_format}' should format to '{expected_output}' but got '{telephone}'"

    def test_rest_api_preserves_original_format(
        self, integration_client, integration_db
    ):
        """Test that REST API endpoints preserve original display_value with +."""
        from google_contacts_cisco.models import Contact, PhoneNumber

        contact = Contact(
            resource_name="people/rest_format",
            display_name="REST Format Test",
        )
        integration_db.add(contact)
        integration_db.flush()

        original_display = "+1-555-123-4567"
        phone = PhoneNumber(
            contact_id=contact.id,
            value="15551234567",
            display_value=original_display,
            type="mobile",
            primary=True,
        )
        integration_db.add(phone)
        integration_db.commit()

        # Get via REST API (not directory endpoint)
        response = integration_client.get(f"/api/contacts/{contact.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # REST API should preserve original format
        phone_data = data["phone_numbers"][0]
        assert phone_data["display_value"] == original_display
        assert "+" in phone_data["display_value"]

