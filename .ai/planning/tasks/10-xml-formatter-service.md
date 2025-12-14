# Task 4.1: XML Formatter Service

## Overview

Create a service to format contact data into Cisco IP Phone XML format. This includes generating main directory menus, group menus, and individual contact directories with proper XML structure.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 1.2: Database Setup
- Task 3.1: Full Sync Implementation

## Objectives

1. Implement main directory menu generation (group selection)
2. Implement group directory menu generation (contact list)
3. Implement individual contact directory generation (phone numbers)
4. Implement contact name to group mapping logic
5. Handle XML escaping and special characters
6. Generate proper Cisco XML structure
7. Build RESTful URLs for navigation
8. Test XML output with various contact data

## Technical Context

### Cisco XML Object Types
1. **CiscoIPPhoneMenu**: For menus with selectable items
2. **CiscoIPPhoneDirectory**: For contact phone numbers

### Group Mapping (Phone Keypad)
- **"1"**: Contacts starting with 1 or numbers
- **"2ABC"**: Contacts starting with 2, A, B, C
- **"3DEF"**: D, E, F
- **"4GHI"**: G, H, I
- **"5JKL"**: J, K, L
- **"6MNO"**: M, N, O
- **"7PRQS"**: P, Q, R, S
- **"8TUV"**: T, U, V
- **"9WXYZ"**: W, X, Y, Z
- **"0"**: Special characters and other

### XML Requirements
- UTF-8 encoding
- XML entity escaping (`&`, `<`, `>`, `"`, `'`)
- Proper structure and nesting
- SoftKey items for navigation

## Acceptance Criteria

- [ ] Main directory menu generates correctly with all groups
- [ ] Group menu generates correctly with filtered contacts
- [ ] Individual contact directory shows all phone numbers
- [ ] Contact names are mapped to correct groups
- [ ] Special characters are properly escaped
- [ ] URLs are correctly formatted and escaped
- [ ] Empty groups are handled gracefully
- [ ] Phone number types are displayed (Mobile, Work, etc.)
- [ ] Help messages are context-specific and useful
- [ ] Help soft key appears in all menus
- [ ] XML validates against Cisco format
- [ ] Tests cover all XML generation scenarios

## Implementation Steps

### 1. Create XML Formatter Service

Create `google_contacts_cisco/services/xml_formatter.py`:

```python
"""XML formatter for Cisco IP Phone directory."""
import xml.etree.ElementTree as ET
from typing import List, Dict
from lxml import etree
from html import escape

from ..models.contact import Contact
from ..models.phone_number import PhoneNumber
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Group mapping for phone keypad
GROUP_MAPPINGS = {
    "1": ["1"],
    "2ABC": ["2", "A", "B", "C"],
    "3DEF": ["3", "D", "E", "F"],
    "4GHI": ["4", "G", "H", "I"],
    "5JKL": ["5", "J", "K", "L"],
    "6MNO": ["6", "M", "N", "O"],
    "7PRQS": ["7", "P", "Q", "R", "S"],
    "8TUV": ["8", "T", "U", "V"],
    "9WXYZ": ["9", "W", "X", "Y", "Z"],
    "0": ["0"]
}


class CiscoXMLFormatter:
    """Format contacts into Cisco IP Phone XML."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize formatter.
        
        Args:
            base_url: Base URL for generating links
        """
        self.base_url = base_url.rstrip('/')
    
    def generate_main_directory(self) -> str:
        """Generate main directory menu with group options.
        
        Returns:
            XML string for main directory
        """
        root = etree.Element("CiscoIPPhoneMenu")
        
        # Title
        title = etree.SubElement(root, "Title")
        title.text = settings.directory_title
        
        # Add menu items for each group
        for group_name in GROUP_MAPPINGS.keys():
            item = etree.SubElement(root, "MenuItem")
            
            name = etree.SubElement(item, "Name")
            name.text = group_name
            
            url = etree.SubElement(item, "URL")
            url.text = f"{self.base_url}/directory/groups/{group_name}"
        
        # Add soft keys
        self._add_softkeys(root, show_help=True, help_context="main")
        
        return self._to_xml_string(root)
    
    def generate_group_directory(self, group: str, contacts: List[Contact]) -> str:
        """Generate directory menu for a specific group.
        
        Args:
            group: Group identifier (e.g., "2ABC")
            contacts: List of contacts in this group
            
        Returns:
            XML string for group directory
        """
        root = etree.Element("CiscoIPPhoneMenu")
        
        # Title
        title = etree.SubElement(root, "Title")
        title.text = group
        
        # Add menu items for each contact
        for contact in contacts:
            item = etree.SubElement(root, "MenuItem")
            
            name = etree.SubElement(item, "Name")
            name.text = self._escape_xml(contact.display_name)
            
            url = etree.SubElement(item, "URL")
            url.text = f"{self.base_url}/directory/contacts/{contact.id}"
        
        # Add soft keys
        self._add_softkeys(root, show_help=True, help_context=f"group/{group}")
        
        return self._to_xml_string(root)
    
    def generate_contact_directory(self, contact: Contact) -> str:
        """Generate directory for individual contact with phone numbers.
        
        Args:
            contact: Contact with phone numbers
            
        Returns:
            XML string for contact directory
        """
        root = etree.Element("CiscoIPPhoneDirectory")
        
        # Title
        title = etree.SubElement(root, "Title")
        title.text = self._escape_xml(contact.display_name)
        
        # Add phone numbers
        if contact.phone_numbers:
            for phone in sorted(contact.phone_numbers, key=lambda p: not p.primary):
                entry = etree.SubElement(root, "DirectoryEntry")
                
                name = etree.SubElement(entry, "Name")
                # Use type as label (Mobile, Work, etc.)
                phone_label = phone.type.capitalize() if phone.type else "Phone"
                if phone.primary:
                    phone_label += " (Primary)"
                name.text = phone_label
                
                telephone = etree.SubElement(entry, "Telephone")
                telephone.text = phone.display_value
        else:
            # No phone numbers
            entry = etree.SubElement(root, "DirectoryEntry")
            name = etree.SubElement(entry, "Name")
            name.text = "No phone numbers"
            telephone = etree.SubElement(entry, "Telephone")
            telephone.text = ""
        
        # Add soft keys for contact view
        # Position 1: Exit (go to home directory)
        exit_key = etree.SubElement(root, "SoftKeyItem")
        exit_name = etree.SubElement(exit_key, "Name")
        exit_name.text = "Exit"
        exit_position = etree.SubElement(exit_key, "Position")
        exit_position.text = "1"
        exit_url = etree.SubElement(exit_key, "URL")
        exit_url.text = f"{self.base_url}/directory"
        
        # Position 2: Back (go back to group list)
        back_key = etree.SubElement(root, "SoftKeyItem")
        back_name = etree.SubElement(back_key, "Name")
        back_name.text = "Back"
        back_position = etree.SubElement(back_key, "Position")
        back_position.text = "2"
        back_url = etree.SubElement(back_key, "URL")
        back_url.text = "SoftKey:Back"
        
        # Position 3: Call
        call_key = etree.SubElement(root, "SoftKeyItem")
        call_name = etree.SubElement(call_key, "Name")
        call_name.text = "Call"
        call_position = etree.SubElement(call_key, "Position")
        call_position.text = "3"
        call_url = etree.SubElement(call_key, "URL")
        call_url.text = "SoftKey:Select"
        
        return self._to_xml_string(root)
    
    def map_contact_to_group(self, contact: Contact) -> str:
        """Map contact to appropriate group based on first character.
        
        Args:
            contact: Contact to map
            
        Returns:
            Group identifier (e.g., "2ABC")
        """
        if not contact.display_name:
            return "0"
        
        first_char = contact.display_name[0].upper()
        
        for group, chars in GROUP_MAPPINGS.items():
            if first_char in chars:
                return group
        
        # Default to "0" for special characters
        return "0"
    
    def generate_help(self, context: str = "main") -> str:
        """Generate help text for different contexts.
        
        Args:
            context: Help context (main, group/<group>, contact)
            
        Returns:
            XML string for help text
        """
        root = etree.Element("CiscoIPPhoneText")
        
        # Title
        title = etree.SubElement(root, "Title")
        title.text = "Help"
        
        # Help text based on context
        text = etree.SubElement(root, "Text")
        if context == "main":
            text.text = (
                "Directory Help:\n\n"
                "Select a group (e.g., 2ABC) to view contacts starting with those letters.\n\n"
                "Use the keypad to quickly jump to a group.\n\n"
                "Press Exit to return to main menu."
            )
        elif context.startswith("group/"):
            group = context.split("/", 1)[1] if "/" in context else ""
            text.text = (
                f"Group {group} Help:\n\n"
                "Select a contact to view their phone numbers.\n\n"
                "Use View button to open contact details.\n\n"
                "Press Exit to return to directory home."
            )
        elif context == "contact":
            text.text = (
                "Contact Help:\n\n"
                "Select a phone number and press Call to dial.\n\n"
                "Press Back to return to contact list.\n\n"
                "Press Exit to return to directory home."
            )
        else:
            text.text = "Use the menu to navigate the directory. Press Exit to return to main menu."
        
        # Soft key to go back
        soft_key = etree.SubElement(root, "SoftKeyItem")
        key_name = etree.SubElement(soft_key, "Name")
        key_name.text = "Back"
        key_position = etree.SubElement(soft_key, "Position")
        key_position.text = "1"
        key_url = etree.SubElement(soft_key, "URL")
        key_url.text = "SoftKey:Back"
        
        return self._to_xml_string(root)
    
    def _add_softkeys(self, root: etree.Element, show_help: bool = False, help_context: str = "main"):
        """Add standard soft keys to menu.
        
        Args:
            root: XML root element
            show_help: Whether to include help button
            help_context: Context for help (main, group/<group>, contact)
        """
        # Exit key
        exit_key = etree.SubElement(root, "SoftKeyItem")
        exit_name = etree.SubElement(exit_key, "Name")
        exit_name.text = "Exit"
        exit_position = etree.SubElement(exit_key, "Position")
        exit_position.text = "1"
        exit_url = etree.SubElement(exit_key, "URL")
        exit_url.text = "Init:Directories"
        
        # View/Select key
        view_key = etree.SubElement(root, "SoftKeyItem")
        view_name = etree.SubElement(view_key, "Name")
        view_name.text = "View"
        view_position = etree.SubElement(view_key, "Position")
        view_position.text = "2"
        view_url = etree.SubElement(view_key, "URL")
        view_url.text = "SoftKey:Select"
        
        # Optional help key
        if show_help:
            help_key = etree.SubElement(root, "SoftKeyItem")
            help_name = etree.SubElement(help_key, "Name")
            help_name.text = "Help"
            help_position = etree.SubElement(help_key, "Position")
            help_position.text = "4"
            help_url = etree.SubElement(help_key, "URL")
            help_url.text = f"{self.base_url}/directory/help?context={help_context}"
    
    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        if not text:
            return ""
        return escape(text, quote=True)
    
    def _to_xml_string(self, root: etree.Element) -> str:
        """Convert XML element to string with proper formatting.
        
        Args:
            root: XML root element
            
        Returns:
            Formatted XML string
        """
        xml_str = etree.tostring(
            root,
            encoding='UTF-8',
            xml_declaration=True,
            pretty_print=False
        ).decode('utf-8')
        
        return xml_str


def get_xml_formatter(base_url: str = "http://localhost:8000") -> CiscoXMLFormatter:
    """Get XML formatter instance.
    
    Args:
        base_url: Base URL for generating links
        
    Returns:
        CiscoXMLFormatter instance
    """
    return CiscoXMLFormatter(base_url)
```

### 2. Create Tests

Create `tests/test_xml_formatter.py`:

```python
"""Test XML formatter."""
import pytest
from lxml import etree
from uuid import uuid4

from google_contacts_cisco.services.xml_formatter import CiscoXMLFormatter, GROUP_MAPPINGS
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def formatter():
    """Create XML formatter."""
    return CiscoXMLFormatter(base_url="http://test.example.com")


@pytest.fixture
def sample_contact():
    """Create sample contact."""
    contact = Contact(
        id=uuid4(),
        resource_name="people/c123",
        display_name="John Doe",
        given_name="John",
        family_name="Doe"
    )
    
    # Add phone numbers
    contact.phone_numbers = [
        PhoneNumber(
            id=uuid4(),
            contact_id=contact.id,
            value="5551234567",
            display_value="(555) 123-4567",
            type="mobile",
            primary=True
        ),
        PhoneNumber(
            id=uuid4(),
            contact_id=contact.id,
            value="5559876543",
            display_value="(555) 987-6543",
            type="work",
            primary=False
        )
    ]
    
    return contact


def test_generate_main_directory(formatter):
    """Test main directory generation."""
    xml_str = formatter.generate_main_directory()
    
    # Parse XML
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    assert root.tag == "CiscoIPPhoneMenu"
    
    # Check title
    title = root.find("Title")
    assert title is not None
    
    # Check menu items for all groups
    menu_items = root.findall("MenuItem")
    assert len(menu_items) == len(GROUP_MAPPINGS)
    
    # Check first menu item
    first_item = menu_items[0]
    name = first_item.find("Name").text
    url = first_item.find("URL").text
    assert name in GROUP_MAPPINGS.keys()
    assert "directory/groups/" in url


def test_generate_group_directory(formatter, sample_contact):
    """Test group directory generation."""
    contacts = [sample_contact]
    xml_str = formatter.generate_group_directory("2ABC", contacts)
    
    # Parse XML
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    assert root.tag == "CiscoIPPhoneMenu"
    
    # Check title
    title = root.find("Title")
    assert title.text == "2ABC"
    
    # Check menu items
    menu_items = root.findall("MenuItem")
    assert len(menu_items) == 1
    
    # Check contact item
    item = menu_items[0]
    name = item.find("Name").text
    url = item.find("URL").text
    assert name == "John Doe"
    assert str(sample_contact.id) in url


def test_generate_contact_directory(formatter, sample_contact):
    """Test individual contact directory generation."""
    xml_str = formatter.generate_contact_directory(sample_contact)
    
    # Parse XML
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    assert root.tag == "CiscoIPPhoneDirectory"
    
    # Check title
    title = root.find("Title")
    assert title.text == "John Doe"
    
    # Check directory entries (phone numbers)
    entries = root.findall("DirectoryEntry")
    assert len(entries) == 2
    
    # Check first entry (primary phone)
    first_entry = entries[0]
    name = first_entry.find("Name").text
    telephone = first_entry.find("Telephone").text
    assert "Mobile" in name
    assert "(555) 123-4567" in telephone


def test_contact_to_group_mapping(formatter):
    """Test contact to group mapping."""
    # Test various first characters
    test_cases = [
        ("Alice", "2ABC"),
        ("Bob", "2ABC"),
        ("Charlie", "2ABC"),
        ("David", "3DEF"),
        ("John", "5JKL"),
        ("Zara", "9WXYZ"),
        ("123 Company", "1"),
        ("@Special", "0"),
    ]
    
    for name, expected_group in test_cases:
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name=name
        )
        group = formatter.map_contact_to_group(contact)
        assert group == expected_group, f"Failed for {name}: expected {expected_group}, got {group}"


def test_xml_escaping(formatter):
    """Test XML character escaping."""
    contact = Contact(
        id=uuid4(),
        resource_name="people/test",
        display_name="John & Jane <Company>"
    )
    
    xml_str = formatter.generate_contact_directory(contact)
    
    # Should contain escaped characters
    assert "&amp;" in xml_str
    assert "&lt;" in xml_str
    assert "&gt;" in xml_str
    
    # Should not contain unescaped characters
    assert "John & Jane" not in xml_str
    assert "<Company>" not in xml_str  # This would break XML


def test_empty_phone_numbers(formatter):
    """Test contact with no phone numbers."""
    contact = Contact(
        id=uuid4(),
        resource_name="people/test",
        display_name="No Phone Contact"
    )
    contact.phone_numbers = []
    
    xml_str = formatter.generate_contact_directory(contact)
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    entries = root.findall("DirectoryEntry")
    assert len(entries) == 1
    assert "No phone numbers" in entries[0].find("Name").text


def test_help_generation(formatter):
    """Test help text generation for different contexts."""
    # Main directory help
    xml_str = formatter.generate_help("main")
    root = etree.fromstring(xml_str.encode('utf-8'))
    assert root.tag == "CiscoIPPhoneText"
    assert "Directory Help" in root.find("Text").text
    
    # Group directory help
    xml_str = formatter.generate_help("group/2ABC")
    root = etree.fromstring(xml_str.encode('utf-8'))
    assert "Group 2ABC Help" in root.find("Text").text
    
    # Contact directory help
    xml_str = formatter.generate_help("contact")
    root = etree.fromstring(xml_str.encode('utf-8'))
    assert "Contact Help" in root.find("Text").text


def test_help_softkey_in_menus(formatter):
    """Test that help soft key appears in menus."""
    xml_str = formatter.generate_main_directory()
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    # Find help soft key
    softkeys = root.findall("SoftKeyItem")
    help_keys = [sk for sk in softkeys if sk.find("Name").text == "Help"]
    assert len(help_keys) == 1
    assert "help?context=" in help_keys[0].find("URL").text
```

## Verification

After completing this task:

1. **Generate and View XML**:
   ```python
   from google_contacts_cisco.services.xml_formatter import get_xml_formatter
   from google_contacts_cisco.models import get_db
   from google_contacts_cisco.repositories.contact_repository import ContactRepository
   
   db = next(get_db())
   formatter = get_xml_formatter()
   
   # Generate main directory
   xml = formatter.generate_main_directory()
   print(xml)
   
   # Generate group directory
   repo = ContactRepository(db)
   contacts = repo.get_all_active()
   xml = formatter.generate_group_directory("2ABC", contacts[:5])
   print(xml)
   ```

2. **Validate XML**:
   ```python
   from lxml import etree
   
   # Parse XML to validate structure
   root = etree.fromstring(xml.encode('utf-8'))
   print(f"Valid XML: {root.tag}")
   ```

3. **Run Tests**:
   ```bash
   pytest tests/test_xml_formatter.py -v
   ```

## Notes

- **lxml vs ElementTree**: Using lxml for better XML generation and pretty printing
- **XML Escaping**: Critical for special characters in names
- **URL Encoding**: URLs in XML must be properly escaped
- **Group Mapping**: Case-insensitive matching
- **SoftKeys**: Standard navigation buttons for Cisco phones
- **Primary Phone**: Displayed first in contact directory

## Common Issues

1. **Special Characters**: Must escape &, <, >, ", '
2. **Empty Groups**: Handle gracefully with message
3. **Long Names**: May be truncated by phone display
4. **Multiple Numbers**: Sort by primary flag
5. **URL Encoding**: Ampersands in URLs must be &amp;

## Related Documentation

- lxml: https://lxml.de/
- Cisco XML Objects: https://www.cisco.com/c/en/us/td/docs/voice_ip_comm/cuipph/all_models/xsi/
- XML Entities: https://www.w3.org/TR/xml/#sec-predefined-ent

## Estimated Time

4-5 hours

