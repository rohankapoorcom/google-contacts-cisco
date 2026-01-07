"""Test XML formatter service.

This module tests the Cisco IP Phone XML formatter implementation,
including menu generation, contact directories, help screens, and
XML escaping functionality.
"""

import uuid

import pytest
from lxml import etree

from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber
from google_contacts_cisco.services.xml_formatter import (
    GROUP_MAPPINGS,
    CiscoXMLFormatter,
    get_xml_formatter,
)


class TestCiscoXMLFormatter:
    """Test CiscoXMLFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Create XML formatter with test base URL."""
        return CiscoXMLFormatter(base_url="http://test.example.com")

    @pytest.fixture
    def sample_contact(self):
        """Create sample contact with phone numbers."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/c123",
            display_name="John Doe",
            given_name="John",
            family_name="Doe",
        )

        # Add phone numbers
        contact.phone_numbers = [
            PhoneNumber(
                id=uuid.uuid4(),
                contact_id=contact.id,
                value="5551234567",
                display_value="(555) 123-4567",
                type="mobile",
                primary=True,
            ),
            PhoneNumber(
                id=uuid.uuid4(),
                contact_id=contact.id,
                value="5559876543",
                display_value="(555) 987-6543",
                type="work",
                primary=False,
            ),
        ]

        return contact

    @pytest.fixture
    def contact_no_phones(self):
        """Create contact without phone numbers."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="No Phone Contact",
        )
        contact.phone_numbers = []
        return contact


class TestMainDirectory(TestCiscoXMLFormatter):
    """Test main directory generation."""

    def test_generates_valid_xml(self, formatter):
        """Test that main directory generates valid XML."""
        xml_str = formatter.generate_main_directory()

        # Should be valid XML that can be parsed
        root = etree.fromstring(xml_str.encode("utf-8"))
        assert root is not None

    def test_has_correct_root_element(self, formatter):
        """Test that root element is CiscoIPPhoneMenu."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        assert root.tag == "CiscoIPPhoneMenu"

    def test_has_title_element(self, formatter):
        """Test that title element exists."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert title is not None
        assert title.text is not None
        assert len(title.text) > 0

    def test_has_all_group_menu_items(self, formatter):
        """Test that all group menu items are present."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        menu_items = root.findall("MenuItem")
        assert len(menu_items) == len(GROUP_MAPPINGS)

    def test_menu_items_have_names_and_urls(self, formatter):
        """Test that each menu item has name and URL."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        menu_items = root.findall("MenuItem")
        for item in menu_items:
            name = item.find("Name")
            url = item.find("URL")
            assert name is not None
            assert name.text in GROUP_MAPPINGS.keys()
            assert url is not None
            assert "directory/groups/" in url.text

    def test_url_uses_base_url(self, formatter):
        """Test that URLs use the configured base URL."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        menu_items = root.findall("MenuItem")
        first_url = menu_items[0].find("URL").text
        assert first_url.startswith("http://test.example.com")

    def test_has_softkeys(self, formatter):
        """Test that soft keys are present."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        assert len(softkeys) >= 2  # At least Exit and View

    def test_has_help_softkey(self, formatter):
        """Test that help soft key is present."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        help_keys = [sk for sk in softkeys if sk.find("Name").text == "Help"]
        assert len(help_keys) == 1
        assert "help?context=main" in help_keys[0].find("URL").text

    def test_has_xml_declaration(self, formatter):
        """Test that XML has proper declaration."""
        xml_str = formatter.generate_main_directory()
        assert xml_str.startswith("<?xml")
        assert 'encoding="UTF-8"' in xml_str or "encoding='UTF-8'" in xml_str


class TestGroupDirectory(TestCiscoXMLFormatter):
    """Test group directory generation."""

    def test_generates_valid_xml(self, formatter, sample_contact):
        """Test that group directory generates valid XML."""
        contacts = [sample_contact]
        xml_str = formatter.generate_group_directory("2ABC", contacts)

        root = etree.fromstring(xml_str.encode("utf-8"))
        assert root is not None

    def test_has_correct_root_element(self, formatter, sample_contact):
        """Test that root element is CiscoIPPhoneMenu."""
        contacts = [sample_contact]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        root = etree.fromstring(xml_str.encode("utf-8"))

        assert root.tag == "CiscoIPPhoneMenu"

    def test_title_matches_group(self, formatter, sample_contact):
        """Test that title matches the group name."""
        contacts = [sample_contact]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert title.text == "2ABC"

    def test_menu_items_for_contacts(self, formatter, sample_contact):
        """Test that menu items are created for contacts."""
        contacts = [sample_contact]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        root = etree.fromstring(xml_str.encode("utf-8"))

        menu_items = root.findall("MenuItem")
        assert len(menu_items) == 1

        item = menu_items[0]
        name = item.find("Name").text
        url = item.find("URL").text
        assert name == "John Doe"
        assert str(sample_contact.id) in url

    def test_multiple_contacts(self, formatter, sample_contact):
        """Test group directory with multiple contacts."""
        contact2 = Contact(
            id=uuid.uuid4(),
            resource_name="people/c456",
            display_name="Jane Smith",
        )
        contacts = [sample_contact, contact2]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        root = etree.fromstring(xml_str.encode("utf-8"))

        menu_items = root.findall("MenuItem")
        assert len(menu_items) == 2

    def test_empty_group(self, formatter):
        """Test group directory with no contacts."""
        xml_str = formatter.generate_group_directory("2ABC", [])
        root = etree.fromstring(xml_str.encode("utf-8"))

        menu_items = root.findall("MenuItem")
        assert len(menu_items) == 1
        name = menu_items[0].find("Name").text
        assert "(No contacts)" in name

    def test_has_help_softkey_with_group_context(self, formatter, sample_contact):
        """Test that help soft key has correct group context."""
        contacts = [sample_contact]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        help_keys = [sk for sk in softkeys if sk.find("Name").text == "Help"]
        assert len(help_keys) == 1
        assert "help?context=group/2ABC" in help_keys[0].find("URL").text


class TestContactDirectory(TestCiscoXMLFormatter):
    """Test contact directory generation."""

    def test_generates_valid_xml(self, formatter, sample_contact):
        """Test that contact directory generates valid XML."""
        xml_str = formatter.generate_contact_directory(sample_contact)

        root = etree.fromstring(xml_str.encode("utf-8"))
        assert root is not None

    def test_has_correct_root_element(self, formatter, sample_contact):
        """Test that root element is CiscoIPPhoneDirectory."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        assert root.tag == "CiscoIPPhoneDirectory"

    def test_title_is_contact_name(self, formatter, sample_contact):
        """Test that title is the contact's display name."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert title.text == "John Doe"

    def test_phone_numbers_as_directory_entries(self, formatter, sample_contact):
        """Test that phone numbers appear as directory entries."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        assert len(entries) == 2

    def test_primary_phone_first(self, formatter, sample_contact):
        """Test that primary phone number is listed first."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        first_entry = entries[0]
        name = first_entry.find("Name").text
        assert "Primary" in name
        assert "Mobile" in name

    def test_phone_type_as_label(self, formatter, sample_contact):
        """Test that phone type is used as label."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        # Check second entry (work phone)
        second_entry = entries[1]
        name = second_entry.find("Name").text
        assert "Work" in name

    def test_phone_display_value(self, formatter, sample_contact):
        """Test that phone display value is shown."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        first_entry = entries[0]
        telephone = first_entry.find("Telephone").text
        assert "(555) 123-4567" in telephone

    def test_no_phone_numbers(self, formatter, contact_no_phones):
        """Test contact with no phone numbers."""
        xml_str = formatter.generate_contact_directory(contact_no_phones)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        assert len(entries) == 1
        assert "No phone numbers" in entries[0].find("Name").text

    def test_has_exit_softkey(self, formatter, sample_contact):
        """Test that Exit soft key is present."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        exit_keys = [sk for sk in softkeys if sk.find("Name").text == "Exit"]
        assert len(exit_keys) == 1
        assert "/directory" in exit_keys[0].find("URL").text

    def test_has_back_softkey(self, formatter, sample_contact):
        """Test that Back soft key is present."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        back_keys = [sk for sk in softkeys if sk.find("Name").text == "Back"]
        assert len(back_keys) == 1
        assert back_keys[0].find("URL").text == "SoftKey:Back"

    def test_has_call_softkey(self, formatter, sample_contact):
        """Test that Call soft key is present."""
        xml_str = formatter.generate_contact_directory(sample_contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        call_keys = [sk for sk in softkeys if sk.find("Name").text == "Call"]
        assert len(call_keys) == 1
        assert call_keys[0].find("URL").text == "SoftKey:Select"

    def test_phone_without_type(self, formatter):
        """Test phone number without type uses default label."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Test Contact",
        )
        contact.phone_numbers = [
            PhoneNumber(
                id=uuid.uuid4(),
                contact_id=contact.id,
                value="5551234567",
                display_value="(555) 123-4567",
                type=None,
                primary=False,
            )
        ]

        xml_str = formatter.generate_contact_directory(contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        name = entries[0].find("Name").text
        assert "Phone" in name


class TestContactToGroupMapping(TestCiscoXMLFormatter):
    """Test contact to group mapping."""

    def test_letter_a_maps_to_2abc(self, formatter):
        """Test that 'A' maps to 2ABC group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Alice",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "2ABC"

    def test_letter_b_maps_to_2abc(self, formatter):
        """Test that 'B' maps to 2ABC group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Bob",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "2ABC"

    def test_letter_c_maps_to_2abc(self, formatter):
        """Test that 'C' maps to 2ABC group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Charlie",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "2ABC"

    def test_letter_d_maps_to_3def(self, formatter):
        """Test that 'D' maps to 3DEF group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="David",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "3DEF"

    def test_letter_j_maps_to_5jkl(self, formatter):
        """Test that 'J' maps to 5JKL group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="John",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "5JKL"

    def test_letter_z_maps_to_9wxyz(self, formatter):
        """Test that 'Z' maps to 9WXYZ group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Zara",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "9WXYZ"

    def test_number_1_maps_to_1(self, formatter):
        """Test that '1' maps to 1 group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="123 Company",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "1"

    def test_number_2_maps_to_2abc(self, formatter):
        """Test that '2' maps to 2ABC group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="24 Hour Service",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "2ABC"

    def test_special_char_maps_to_0(self, formatter):
        """Test that special characters map to 0 group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="@Special",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "0"

    def test_empty_name_maps_to_0(self, formatter):
        """Test that empty name maps to 0 group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "0"

    def test_none_name_maps_to_0(self, formatter):
        """Test that None name maps to 0 group."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name=None,
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "0"

    def test_lowercase_letter_maps_correctly(self, formatter):
        """Test that lowercase letters are handled correctly."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="alice",
        )
        group = formatter.map_contact_to_group(contact)
        assert group == "2ABC"

    def test_all_groups_covered(self, formatter):
        """Test that all groups have representative mappings."""
        test_cases = [
            ("1-800-Number", "1"),
            ("Alice", "2ABC"),
            ("David", "3DEF"),
            ("George", "4GHI"),
            ("John", "5JKL"),
            ("Mary", "6MNO"),
            ("Paul", "7PQRS"),
            ("Tom", "8TUV"),
            ("William", "9WXYZ"),
            ("!Special", "0"),
        ]

        for name, expected_group in test_cases:
            contact = Contact(
                id=uuid.uuid4(),
                resource_name="people/test",
                display_name=name,
            )
            group = formatter.map_contact_to_group(contact)
            assert group == expected_group, f"Failed for {name}"


class TestXMLEscaping(TestCiscoXMLFormatter):
    """Test XML character escaping.

    Note: lxml automatically escapes special characters when setting .text
    and unescapes them when reading .text back. So the raw XML string will
    contain escaped entities like &amp;, but etree.text will return the
    unescaped value.
    """

    def test_ampersand_escaped_in_xml(self, formatter):
        """Test that ampersand is escaped in raw XML output."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="John & Jane",
        )

        xml_str = formatter.generate_contact_directory(contact)

        # Raw XML should contain escaped ampersand
        assert "&amp;" in xml_str
        # When parsed back, lxml returns the unescaped value
        root = etree.fromstring(xml_str.encode("utf-8"))
        title = root.find("Title")
        assert title.text == "John & Jane"

    def test_less_than_escaped_in_xml(self, formatter):
        """Test that less than is escaped in raw XML output."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Test <Company>",
        )

        xml_str = formatter.generate_contact_directory(contact)

        # Raw XML should contain escaped less than
        assert "&lt;" in xml_str

    def test_greater_than_escaped_in_xml(self, formatter):
        """Test that greater than is escaped in raw XML output."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Test <Company>",
        )

        xml_str = formatter.generate_contact_directory(contact)

        # Raw XML should contain escaped greater than
        assert "&gt;" in xml_str

    def test_quote_preserved_in_text(self, formatter):
        """Test that quotes are preserved in XML content."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name='John "The Rock" Doe',
        )

        xml_str = formatter.generate_contact_directory(contact)

        # Should be valid XML
        root = etree.fromstring(xml_str.encode("utf-8"))
        title = root.find("Title")
        assert title.text == 'John "The Rock" Doe'

    def test_combined_special_characters(self, formatter):
        """Test escaping of combined special characters."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="Tom & Jerry's <Company>",
        )

        xml_str = formatter.generate_contact_directory(contact)

        # Should be valid XML
        root = etree.fromstring(xml_str.encode("utf-8"))
        title = root.find("Title")
        assert title.text == "Tom & Jerry's <Company>"

    def test_xml_valid_with_special_chars(self, formatter):
        """Test that generated XML is valid and parseable."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="A & B < C > D",
        )

        xml_str = formatter.generate_contact_directory(contact)

        # This should not raise an exception
        root = etree.fromstring(xml_str.encode("utf-8"))
        assert root is not None


class TestHelpGeneration(TestCiscoXMLFormatter):
    """Test help text generation."""

    def test_main_help_generates_valid_xml(self, formatter):
        """Test that main help generates valid XML."""
        xml_str = formatter.generate_help("main")

        root = etree.fromstring(xml_str.encode("utf-8"))
        assert root is not None

    def test_main_help_has_correct_root(self, formatter):
        """Test that main help has CiscoIPPhoneText root."""
        xml_str = formatter.generate_help("main")
        root = etree.fromstring(xml_str.encode("utf-8"))

        assert root.tag == "CiscoIPPhoneText"

    def test_main_help_has_title(self, formatter):
        """Test that main help has Help title."""
        xml_str = formatter.generate_help("main")
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert title.text == "Help"

    def test_main_help_content(self, formatter):
        """Test main help text content."""
        xml_str = formatter.generate_help("main")
        root = etree.fromstring(xml_str.encode("utf-8"))

        text = root.find("Text")
        assert "Directory Help" in text.text
        assert "group" in text.text.lower()

    def test_group_help_content(self, formatter):
        """Test group help text content."""
        xml_str = formatter.generate_help("group/2ABC")
        root = etree.fromstring(xml_str.encode("utf-8"))

        text = root.find("Text")
        assert "Group 2ABC Help" in text.text

    def test_contact_help_content(self, formatter):
        """Test contact help text content."""
        xml_str = formatter.generate_help("contact")
        root = etree.fromstring(xml_str.encode("utf-8"))

        text = root.find("Text")
        assert "Contact Help" in text.text
        assert "Call" in text.text

    def test_unknown_context_help(self, formatter):
        """Test help with unknown context."""
        xml_str = formatter.generate_help("unknown")
        root = etree.fromstring(xml_str.encode("utf-8"))

        text = root.find("Text")
        assert text.text is not None
        assert len(text.text) > 0

    def test_help_has_back_softkey(self, formatter):
        """Test that help has Back soft key."""
        xml_str = formatter.generate_help("main")
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        assert len(softkeys) == 1
        assert softkeys[0].find("Name").text == "Back"
        assert softkeys[0].find("URL").text == "SoftKey:Back"


class TestSoftKeyGeneration(TestCiscoXMLFormatter):
    """Test soft key generation."""

    def test_exit_softkey_position(self, formatter):
        """Test Exit soft key is at position 1."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        exit_key = next(sk for sk in softkeys if sk.find("Name").text == "Exit")
        assert exit_key.find("Position").text == "1"

    def test_view_softkey_position(self, formatter):
        """Test View soft key is at position 2."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        view_key = next(sk for sk in softkeys if sk.find("Name").text == "View")
        assert view_key.find("Position").text == "2"

    def test_help_softkey_position(self, formatter):
        """Test Help soft key is at position 4."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        help_key = next(sk for sk in softkeys if sk.find("Name").text == "Help")
        assert help_key.find("Position").text == "4"

    def test_exit_uses_init_directories(self, formatter):
        """Test Exit soft key URL uses Init:Directories."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode("utf-8"))

        softkeys = root.findall("SoftKeyItem")
        exit_key = next(sk for sk in softkeys if sk.find("Name").text == "Exit")
        assert exit_key.find("URL").text == "Init:Directories"


class TestFactoryFunction:
    """Test factory function."""

    def test_get_xml_formatter_returns_formatter(self):
        """Test that factory function returns formatter instance."""
        formatter = get_xml_formatter()
        assert isinstance(formatter, CiscoXMLFormatter)

    def test_get_xml_formatter_with_custom_url(self):
        """Test factory function with custom base URL."""
        formatter = get_xml_formatter(base_url="http://custom.example.com")
        assert formatter.base_url == "http://custom.example.com"

    def test_get_xml_formatter_default_url(self):
        """Test factory function with default URL."""
        formatter = get_xml_formatter()
        assert formatter.base_url == "http://localhost:8000"


class TestBaseURLHandling(TestCiscoXMLFormatter):
    """Test base URL handling."""

    def test_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        formatter = CiscoXMLFormatter(base_url="http://example.com/")
        assert formatter.base_url == "http://example.com"

    def test_multiple_trailing_slashes_handled(self):
        """Test that multiple trailing slashes are handled."""
        formatter = CiscoXMLFormatter(base_url="http://example.com///")
        # Should have at most one level stripped (rstrip behavior)
        assert not formatter.base_url.endswith("/")

    def test_base_url_in_generated_urls(self):
        """Test that base URL appears in generated URLs."""
        formatter = CiscoXMLFormatter(base_url="https://secure.example.com:8443")
        xml_str = formatter.generate_main_directory()

        assert "https://secure.example.com:8443" in xml_str


class TestGroupMappings:
    """Test GROUP_MAPPINGS constant."""

    def test_has_ten_groups(self):
        """Test that there are 10 groups (0-9 on phone keypad)."""
        assert len(GROUP_MAPPINGS) == 10

    def test_group_1_has_only_1(self):
        """Test that group 1 only contains digit 1."""
        assert GROUP_MAPPINGS["1"] == ["1"]

    def test_group_2abc_has_correct_chars(self):
        """Test that 2ABC has 2, A, B, C."""
        assert set(GROUP_MAPPINGS["2ABC"]) == {"2", "A", "B", "C"}

    def test_group_7pqrs_has_correct_chars(self):
        """Test that 7PQRS has 7, P, Q, R, S."""
        assert set(GROUP_MAPPINGS["7PQRS"]) == {"7", "P", "Q", "R", "S"}

    def test_group_0_has_only_0(self):
        """Test that group 0 only contains digit 0."""
        assert GROUP_MAPPINGS["0"] == ["0"]

    def test_all_letters_covered(self):
        """Test that all letters A-Z are covered by groups."""
        all_chars = set()
        for chars in GROUP_MAPPINGS.values():
            all_chars.update(chars)

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert letter in all_chars, f"Letter {letter} not covered"


class TestEdgeCases(TestCiscoXMLFormatter):
    """Test edge cases."""

    def test_contact_with_empty_phone_numbers_list(self, formatter, contact_no_phones):
        """Test contact with empty phone numbers list."""
        xml_str = formatter.generate_contact_directory(contact_no_phones)
        root = etree.fromstring(xml_str.encode("utf-8"))

        entries = root.findall("DirectoryEntry")
        assert len(entries) == 1
        assert "No phone numbers" in entries[0].find("Name").text

    def test_very_long_contact_name(self, formatter):
        """Test contact with very long name."""
        long_name = "A" * 200
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name=long_name,
        )

        xml_str = formatter.generate_contact_directory(contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert title.text == long_name

    def test_unicode_characters(self, formatter):
        """Test contact with unicode characters."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="José García 日本語",
        )

        xml_str = formatter.generate_contact_directory(contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert title.text == "José García 日本語"

    def test_emoji_in_name(self, formatter):
        """Test contact with emoji in name."""
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/test",
            display_name="John 👋 Doe",
        )

        xml_str = formatter.generate_contact_directory(contact)
        root = etree.fromstring(xml_str.encode("utf-8"))

        title = root.find("Title")
        assert "John" in title.text
        assert "Doe" in title.text

