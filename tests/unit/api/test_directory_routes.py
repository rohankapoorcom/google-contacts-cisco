"""Test Cisco IP Phone Directory API Endpoints.

This module tests the FastAPI endpoints for the Cisco IP Phone XML directory.
Tests cover all three levels of the directory hierarchy:
- Main menu with group options
- Group directory with filtered contacts
- Individual contact with phone numbers
- Help endpoint with context-specific content
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from google_contacts_cisco.main import app
from google_contacts_cisco.models import Base, get_db
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


# Use module-scoped engine for consistent database across tests
@pytest.fixture(scope="module")
def db_engine():
    """Create test database engine."""
    # Use StaticPool to share the same connection across threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def session_factory(db_engine):
    """Create session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    """Create test database session."""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(session_factory):
    """Create test client with test database."""

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_contact(db_session, client):
    """Create a test contact with phone numbers in the database."""
    contact = Contact(
        id=uuid.uuid4(),
        resource_name=f"people/c{uuid.uuid4().hex[:8]}",
        display_name="Alice Test",
        given_name="Alice",
        family_name="Test",
        deleted=False,
    )
    db_session.add(contact)
    db_session.flush()

    # Create phone numbers
    phone1 = PhoneNumber(
        id=uuid.uuid4(),
        contact_id=contact.id,
        type="mobile",
        value="5551234567",
        display_value="(555) 123-4567",
        primary=True,
    )
    phone2 = PhoneNumber(
        id=uuid.uuid4(),
        contact_id=contact.id,
        type="work",
        value="5559876543",
        display_value="(555) 987-6543",
        primary=False,
    )
    db_session.add(phone1)
    db_session.add(phone2)
    db_session.commit()

    return contact


@pytest.fixture
def test_contacts(db_session, client):
    """Create multiple test contacts for group testing in the database."""
    test_data = [
        ("Alice Test", f"people/c{uuid.uuid4().hex[:8]}"),
        ("Bob Smith", f"people/c{uuid.uuid4().hex[:8]}"),
        ("Charlie Brown", f"people/c{uuid.uuid4().hex[:8]}"),
        ("David Jones", f"people/c{uuid.uuid4().hex[:8]}"),
        ("Emma Wilson", f"people/c{uuid.uuid4().hex[:8]}"),
        ("Frank Miller", f"people/c{uuid.uuid4().hex[:8]}"),
        ("123 Company", f"people/c{uuid.uuid4().hex[:8]}"),
        ("@Special Contact", f"people/c{uuid.uuid4().hex[:8]}"),
    ]

    contacts = []
    for i, (name, resource_name) in enumerate(test_data):
        parts = name.split()
        contact = Contact(
            id=uuid.uuid4(),
            resource_name=resource_name,
            display_name=name,
            given_name=parts[0],
            family_name=parts[-1] if len(parts) > 1 else "",
            deleted=False,
        )
        db_session.add(contact)
        db_session.flush()  # Flush to get contact.id for phone numbers

        # Add a phone number to each contact so they appear in directory
        phone = PhoneNumber(
            id=uuid.uuid4(),
            contact_id=contact.id,
            type="mobile",
            value=f"555{i:07d}",
            display_value=f"(555) {i:03d}-{i:04d}",
            primary=True,
        )
        db_session.add(phone)
        contacts.append(contact)

    db_session.commit()
    return contacts


@pytest.fixture
def mock_contact():
    """Create a mock contact with phone numbers (for backward compatibility)."""
    contact = MagicMock(spec=Contact)
    contact.id = uuid.uuid4()
    contact.resource_name = "people/c123456"
    contact.display_name = "Alice Test"
    contact.given_name = "Alice"
    contact.family_name = "Test"
    contact.deleted = False

    # Create phone numbers
    phone1 = MagicMock(spec=PhoneNumber)
    phone1.id = uuid.uuid4()
    phone1.type = "mobile"
    phone1.value = "5551234567"
    phone1.display_value = "(555) 123-4567"
    phone1.primary = True

    phone2 = MagicMock(spec=PhoneNumber)
    phone2.id = uuid.uuid4()
    phone2.type = "work"
    phone2.value = "5559876543"
    phone2.display_value = "(555) 987-6543"
    phone2.primary = False

    contact.phone_numbers = [phone1, phone2]
    return contact


@pytest.fixture
def mock_contacts():
    """Create multiple mock contacts for group testing."""
    contacts = []
    test_data = [
        ("Alice Test", "2ABC"),
        ("Bob Smith", "2ABC"),
        ("Charlie Brown", "2ABC"),
        ("David Jones", "3DEF"),
        ("Emma Wilson", "3DEF"),
        ("Frank Miller", "3DEF"),
        ("123 Company", "1"),
        ("@Special Contact", "0"),
    ]

    for i, (name, _) in enumerate(test_data):
        contact = MagicMock(spec=Contact)
        contact.id = uuid.uuid4()
        contact.resource_name = f"people/c{i}"
        contact.display_name = name
        contact.given_name = name.split()[0]
        contact.family_name = name.split()[-1] if len(name.split()) > 1 else ""
        contact.deleted = False
        contact.phone_numbers = []
        contacts.append(contact)

    return contacts


class TestMainDirectoryEndpoint:
    """Test GET /directory endpoint."""

    def test_main_directory_returns_xml(self, client):
        """Test main directory returns valid XML."""
        response = client.get("/directory")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

        # Parse XML
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneMenu"

    def test_main_directory_has_title(self, client):
        """Test main directory has proper title."""
        response = client.get("/directory")
        root = etree.fromstring(response.content)

        title = root.find("Title")
        assert title is not None
        assert title.text is not None

    def test_main_directory_has_menu_items(self, client):
        """Test main directory has menu items for all groups."""
        response = client.get("/directory")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        # Should have 10 groups: 1, 2ABC, 3DEF, 4GHI, 5JKL, 6MNO, 7PQRS, 8TUV, 9WXYZ, 0
        assert len(menu_items) == 10

        # Verify group names
        group_names = [item.find("Name").text for item in menu_items]
        expected_groups = [
            "1", "2ABC", "3DEF", "4GHI", "5JKL", "6MNO", "7PQRS", "8TUV", "9WXYZ", "0"
        ]
        assert group_names == expected_groups

    def test_main_directory_menu_items_have_urls(self, client):
        """Test menu items have proper URLs."""
        response = client.get("/directory")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        for item in menu_items:
            url = item.find("URL")
            assert url is not None
            assert "/directory/groups/" in url.text

    def test_main_directory_has_soft_keys(self, client):
        """Test main directory has soft keys."""
        response = client.get("/directory")
        root = etree.fromstring(response.content)

        soft_keys = root.findall("SoftKeyItem")
        assert len(soft_keys) >= 2  # At least Exit and View

        # Check for Exit key
        exit_key = None
        for key in soft_keys:
            name = key.find("Name")
            if name is not None and name.text == "Exit":
                exit_key = key
                break
        assert exit_key is not None

    def test_main_directory_has_help_soft_key(self, client):
        """Test main directory has Help soft key."""
        response = client.get("/directory")
        root = etree.fromstring(response.content)

        soft_keys = root.findall("SoftKeyItem")
        help_key = None
        for key in soft_keys:
            name = key.find("Name")
            if name is not None and name.text == "Help":
                help_key = key
                break

        assert help_key is not None
        url = help_key.find("URL")
        assert "/directory/help" in url.text

    @patch("google_contacts_cisco.api.directory_routes.get_xml_formatter")
    def test_main_directory_handles_error(self, mock_formatter, client):
        """Test main directory handles errors gracefully."""
        mock_formatter.side_effect = Exception("Test error")

        response = client.get("/directory")

        # Should return 200 with error XML (Cisco phones expect 200)
        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"
        assert "Error" in root.find("Title").text


class TestGroupDirectoryEndpoint:
    """Test GET /directory/groups/{group} endpoint."""

    def test_group_directory_returns_xml(self, client, test_contacts):
        """Test group directory returns valid XML."""
        response = client.get("/directory/groups/2ABC")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneMenu"

    def test_group_directory_filters_contacts(self, client, test_contacts):
        """Test group directory filters contacts correctly."""
        response = client.get("/directory/groups/2ABC")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        # Should have at least 3 contacts in 2ABC group:
        # Alice, Bob, Charlie (all start with A, B, C)
        assert len(menu_items) >= 3

        # Verify sorted order
        names = [item.find("Name").text for item in menu_items]
        assert names == sorted(names, key=str.lower)

        # Verify expected contacts are present
        expected_names = {"Alice Test", "Bob Smith", "Charlie Brown"}
        assert expected_names.issubset(set(names))

    def test_group_directory_case_insensitive(self, client, test_contacts):
        """Test group parameter is case insensitive."""
        # Test lowercase
        response1 = client.get("/directory/groups/2abc")
        root1 = etree.fromstring(response1.content)
        menu_items1 = root1.findall("MenuItem")

        # Test uppercase
        response2 = client.get("/directory/groups/2ABC")
        root2 = etree.fromstring(response2.content)
        menu_items2 = root2.findall("MenuItem")

        assert len(menu_items1) == len(menu_items2)

    def test_group_directory_empty_group(self, client):
        """Test group directory with no contacts shows message."""
        response = client.get("/directory/groups/5JKL")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        # Should have 1 item: "(No contacts)"
        assert len(menu_items) == 1
        assert "No contacts" in menu_items[0].find("Name").text

    def test_group_directory_has_title(self, client, test_contacts):
        """Test group directory has group as title."""
        response = client.get("/directory/groups/2ABC")
        root = etree.fromstring(response.content)

        title = root.find("Title")
        assert title is not None
        assert "2ABC" in title.text

    @patch("google_contacts_cisco.api.directory_routes.ContactRepository")
    def test_group_directory_handles_error(self, mock_repo_class, client):
        """Test group directory handles errors gracefully."""
        mock_repo_class.side_effect = Exception("Database error")

        response = client.get("/directory/groups/2ABC")

        # Should return 200 with error XML
        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"
        assert "Error" in root.find("Title").text


class TestContactDirectoryEndpoint:
    """Test GET /directory/contacts/{contact_id} endpoint."""

    def test_contact_directory_returns_xml(self, client, test_contact):
        """Test contact directory returns valid XML."""
        response = client.get(f"/directory/contacts/{test_contact.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneDirectory"

    def test_contact_directory_shows_name(self, client, test_contact):
        """Test contact directory shows contact name as title."""
        response = client.get(f"/directory/contacts/{test_contact.id}")
        root = etree.fromstring(response.content)

        title = root.find("Title")
        assert title is not None
        assert title.text == test_contact.display_name

    def test_contact_directory_shows_phone_numbers(self, client, test_contact):
        """Test contact directory lists all phone numbers."""
        response = client.get(f"/directory/contacts/{test_contact.id}")
        root = etree.fromstring(response.content)

        entries = root.findall("DirectoryEntry")
        assert len(entries) == 2  # Two phone numbers

        # Verify phone values are present
        telephones = [entry.find("Telephone").text for entry in entries]
        assert "(555) 123-4567" in telephones
        assert "(555) 987-6543" in telephones

    def test_contact_directory_primary_phone_first(self, client, test_contact):
        """Test contact directory shows primary phone first."""
        response = client.get(f"/directory/contacts/{test_contact.id}")
        root = etree.fromstring(response.content)

        entries = root.findall("DirectoryEntry")
        # First entry should be primary (Mobile)
        first_name = entries[0].find("Name").text
        assert "Primary" in first_name or "Mobile" in first_name

    def test_contact_not_found(self, client):
        """Test contact endpoint with invalid ID."""
        fake_id = uuid.uuid4()
        response = client.get(f"/directory/contacts/{fake_id}")

        # Should return 200 with error XML (Cisco phones expect 200)
        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"
        assert "not found" in root.find("Text").text.lower()

    def test_contact_deleted(self, client, db_session):
        """Test contact endpoint with deleted contact."""
        # Create a deleted contact
        deleted_contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/deleted123",
            display_name="Deleted Person",
            deleted=True,
        )
        db_session.add(deleted_contact)
        db_session.commit()

        response = client.get(f"/directory/contacts/{deleted_contact.id}")

        # Should return 200 with error XML
        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"
        assert "no longer available" in root.find("Text").text.lower()

    def test_contact_invalid_uuid(self, client):
        """Test contact endpoint with invalid UUID format."""
        response = client.get("/directory/contacts/not-a-uuid")

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    def test_contact_directory_has_soft_keys(self, client, test_contact):
        """Test contact directory has proper soft keys."""
        response = client.get(f"/directory/contacts/{test_contact.id}")
        root = etree.fromstring(response.content)

        soft_keys = root.findall("SoftKeyItem")
        assert len(soft_keys) >= 3  # Exit, Back, Call

        key_names = [key.find("Name").text for key in soft_keys]
        assert "Exit" in key_names
        assert "Back" in key_names
        assert "Call" in key_names


class TestHelpEndpoint:
    """Test GET /directory/help endpoint."""

    def test_help_main_context(self, client):
        """Test help endpoint with main context."""
        response = client.get("/directory/help?context=main")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"
        assert root.find("Title").text == "Help"
        assert "Directory Help" in root.find("Text").text

    def test_help_group_context(self, client):
        """Test help endpoint with group context."""
        response = client.get("/directory/help?context=group/2ABC")

        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert "Group 2ABC Help" in root.find("Text").text

    def test_help_contact_context(self, client):
        """Test help endpoint with contact context."""
        response = client.get("/directory/help?context=contact")

        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert "Contact Help" in root.find("Text").text

    def test_help_default_context(self, client):
        """Test help endpoint with no context (defaults to main)."""
        response = client.get("/directory/help")

        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert root.find("Title").text == "Help"

    def test_help_unknown_context(self, client):
        """Test help endpoint with unknown context."""
        response = client.get("/directory/help?context=unknown")

        assert response.status_code == 200
        root = etree.fromstring(response.content)
        # Should return generic help
        text = root.find("Text").text
        assert text is not None

    def test_help_has_back_button(self, client):
        """Test help has Back soft key."""
        response = client.get("/directory/help")
        root = etree.fromstring(response.content)

        soft_keys = root.findall("SoftKeyItem")
        back_key = None
        for key in soft_keys:
            name = key.find("Name")
            if name is not None and name.text == "Back":
                back_key = key
                break

        assert back_key is not None

    @patch("google_contacts_cisco.api.directory_routes.get_xml_formatter")
    def test_help_handles_error(self, mock_formatter, client):
        """Test help endpoint handles errors gracefully."""
        mock_formatter.side_effect = Exception("Test error")

        response = client.get("/directory/help")

        # Should return 200 with error XML
        assert response.status_code == 200
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"
        assert "Error" in root.find("Title").text


class TestXMLContentType:
    """Test XML content type across all endpoints."""

    def test_main_directory_content_type(self, client):
        """Test main directory returns correct content type."""
        response = client.get("/directory")
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

    def test_group_directory_content_type(self, client):
        """Test group directory returns correct content type."""
        response = client.get("/directory/groups/2ABC")
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

    def test_contact_directory_content_type(self, client, test_contact):
        """Test contact directory returns correct content type."""
        response = client.get(f"/directory/contacts/{test_contact.id}")
        assert response.headers["content-type"] == "text/xml; charset=utf-8"

    def test_help_content_type(self, client):
        """Test help returns correct content type."""
        response = client.get("/directory/help")
        assert response.headers["content-type"] == "text/xml; charset=utf-8"


class TestErrorResponses:
    """Test error response format."""

    def test_error_returns_200_status(self, client):
        """Test errors return 200 status (Cisco phones expect this)."""
        fake_id = uuid.uuid4()
        response = client.get(f"/directory/contacts/{fake_id}")

        # Cisco phones expect 200 even for errors
        assert response.status_code == 200

    def test_error_returns_cisco_text_format(self, client):
        """Test errors return CiscoIPPhoneText format."""
        fake_id = uuid.uuid4()
        response = client.get(f"/directory/contacts/{fake_id}")

        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneText"

    def test_error_has_title_and_text(self, client):
        """Test error XML has Title and Text elements."""
        fake_id = uuid.uuid4()
        response = client.get(f"/directory/contacts/{fake_id}")

        root = etree.fromstring(response.content)
        assert root.find("Title") is not None
        assert root.find("Text") is not None

    def test_error_has_prompt(self, client):
        """Test error XML has Prompt element."""
        fake_id = uuid.uuid4()
        response = client.get(f"/directory/contacts/{fake_id}")

        root = etree.fromstring(response.content)
        prompt = root.find("Prompt")
        assert prompt is not None

    def test_error_has_exit_softkey(self, client):
        """Test error XML has Exit soft key."""
        fake_id = uuid.uuid4()
        response = client.get(f"/directory/contacts/{fake_id}")

        root = etree.fromstring(response.content)
        soft_keys = root.findall("SoftKeyItem")
        exit_key = None
        for key in soft_keys:
            name = key.find("Name")
            if name is not None and name.text == "Exit":
                exit_key = key
                break

        assert exit_key is not None


class TestGetBaseUrl:
    """Test base URL extraction from request."""

    def test_base_url_included_in_links(self, client):
        """Test base URL is included in generated links."""
        response = client.get("/directory")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        if menu_items:
            url = menu_items[0].find("URL").text
            assert "http://" in url or "https://" in url
            assert "/directory/" in url


class TestContactNoPhoneNumbers:
    """Test contact with no phone numbers."""

    def test_contact_without_phones_shows_message(self, client, db_session):
        """Test contact without phone numbers shows appropriate message."""
        # Create contact with no phone numbers
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/nophone123",
            display_name="No Phone Person",
            deleted=False,
        )
        db_session.add(contact)
        db_session.commit()

        response = client.get(f"/directory/contacts/{contact.id}")
        root = etree.fromstring(response.content)

        entries = root.findall("DirectoryEntry")
        assert len(entries) == 1

        name = entries[0].find("Name").text
        assert "No phone" in name


class TestSpecialCharacters:
    """Test handling of special characters in XML."""

    def test_special_characters_escaped(self, client, db_session):
        """Test special XML characters are properly escaped."""
        # Create contact with special characters in name
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/special123",
            display_name="Test <Company> & \"Friends\"",
            deleted=False,
        )
        db_session.add(contact)
        db_session.commit()

        response = client.get(f"/directory/contacts/{contact.id}")

        # Should not raise XML parsing error
        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneDirectory"


class TestContactsWithoutPhoneNumbersFiltered:
    """Test that contacts without phone numbers are filtered from directory."""

    def test_group_directory_excludes_contacts_without_phones(self, client, db_session):
        """Test contacts without phone numbers don't appear in group directory."""
        # Create contact WITH phone
        contact_with_phone = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/withphone-{uuid.uuid4().hex[:8]}",
            display_name="Alice FilterTest",
            deleted=False,
        )
        db_session.add(contact_with_phone)
        db_session.flush()

        phone = PhoneNumber(
            id=uuid.uuid4(),
            contact_id=contact_with_phone.id,
            type="mobile",
            value="5551234567",
            display_value="(555) 123-4567",
            primary=True,
        )
        db_session.add(phone)

        # Create contact WITHOUT phone
        contact_no_phone = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/nophone-{uuid.uuid4().hex[:8]}",
            display_name="Bob NoPhoneFilter",
            deleted=False,
        )
        db_session.add(contact_no_phone)
        db_session.commit()

        # Request group directory (Alice starts with A = 2ABC)
        response = client.get("/directory/groups/2ABC")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        names = [item.find("Name").text for item in menu_items]

        # Only contact with phone should appear
        assert "Alice FilterTest" in names
        assert "Bob NoPhoneFilter" not in names

    def test_main_directory_still_accessible(self, client, db_session):
        """Test main directory still works when contacts have no phones."""
        # Create contact without phone
        contact = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/nophone-main-{uuid.uuid4().hex[:8]}",
            display_name="Contact NoPhone Main",
            deleted=False,
        )
        db_session.add(contact)
        db_session.commit()

        # Main directory should still load
        response = client.get("/directory")
        assert response.status_code == 200

        root = etree.fromstring(response.content)
        assert root.tag == "CiscoIPPhoneMenu"

    def test_empty_group_when_no_contacts_with_phones(self, client, db_session):
        """Test group shows empty message when no contacts have phones."""
        # Create contact in 5JKL group (starts with J) but without phones
        contact = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/john-{uuid.uuid4().hex[:8]}",
            display_name="John NoPhoneEmpty",
            deleted=False,
        )
        db_session.add(contact)
        db_session.commit()

        response = client.get("/directory/groups/5JKL")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        # Should show "(No contacts)" message
        assert len(menu_items) == 1
        assert "No contacts" in menu_items[0].find("Name").text

    def test_multiple_contacts_mixed_phones(self, client, db_session):
        """Test directory correctly filters in groups with mixed contacts."""
        # Create several contacts in the same group (2ABC)
        # Contact 1: with phone
        contact1 = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/alice-{uuid.uuid4().hex[:8]}",
            display_name="Aalice WithPhone",
            deleted=False,
        )
        db_session.add(contact1)
        db_session.flush()

        phone1 = PhoneNumber(
            id=uuid.uuid4(),
            contact_id=contact1.id,
            type="mobile",
            value="5551111111",
            display_value="(555) 111-1111",
            primary=True,
        )
        db_session.add(phone1)

        # Contact 2: without phone
        contact2 = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/amy-{uuid.uuid4().hex[:8]}",
            display_name="Aamy NoPhoneMix",
            deleted=False,
        )
        db_session.add(contact2)

        # Contact 3: with phone
        contact3 = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/andrew-{uuid.uuid4().hex[:8]}",
            display_name="Aandrew WithPhone",
            deleted=False,
        )
        db_session.add(contact3)
        db_session.flush()

        phone3 = PhoneNumber(
            id=uuid.uuid4(),
            contact_id=contact3.id,
            type="work",
            value="5553333333",
            display_value="(555) 333-3333",
            primary=True,
        )
        db_session.add(phone3)

        # Contact 4: without phone
        contact4 = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/anna-{uuid.uuid4().hex[:8]}",
            display_name="Aanna NoPhoneMix",
            deleted=False,
        )
        db_session.add(contact4)
        db_session.commit()

        # Request group directory for 2ABC
        response = client.get("/directory/groups/2ABC")
        root = etree.fromstring(response.content)

        menu_items = root.findall("MenuItem")
        names = [item.find("Name").text for item in menu_items]

        # Only contacts with phones should appear
        assert "Aalice WithPhone" in names
        assert "Aandrew WithPhone" in names
        assert "Aamy NoPhoneMix" not in names
        assert "Aanna NoPhoneMix" not in names

    def test_contact_detail_still_shows_no_phone_message(self, client, db_session):
        """Test individual contact view still handles contacts without phones.
        
        This ensures backward compatibility - if someone directly accesses
        a contact without phones, they still get appropriate messaging.
        """
        # Create contact without phone
        contact = Contact(
            id=uuid.uuid4(),
            resource_name=f"people/nophone-detail-{uuid.uuid4().hex[:8]}",
            display_name="No Phone Detail Person",
            deleted=False,
        )
        db_session.add(contact)
        db_session.commit()

        # Access contact directly
        response = client.get(f"/directory/contacts/{contact.id}")
        root = etree.fromstring(response.content)

        # Should still show the contact with "No phone numbers" message
        entries = root.findall("DirectoryEntry")
        assert len(entries) == 1
        name = entries[0].find("Name").text
        assert "No phone" in name


