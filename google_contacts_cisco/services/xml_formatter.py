"""XML formatter for Cisco IP Phone directory.

This module provides functionality to generate Cisco IP Phone XML format
for directory menus, contact lists, and help screens.
"""

from typing import TYPE_CHECKING, List

from lxml import etree

from ..config import settings
from ..utils.logger import get_logger

if TYPE_CHECKING:
    from ..models.contact import Contact

logger = get_logger(__name__)


# Group mapping for phone keypad
# Maps group labels to list of starting characters
GROUP_MAPPINGS = {
    "1": ["1"],
    "2ABC": ["2", "A", "B", "C"],
    "3DEF": ["3", "D", "E", "F"],
    "4GHI": ["4", "G", "H", "I"],
    "5JKL": ["5", "J", "K", "L"],
    "6MNO": ["6", "M", "N", "O"],
    "7PQRS": ["7", "P", "Q", "R", "S"],
    "8TUV": ["8", "T", "U", "V"],
    "9WXYZ": ["9", "W", "X", "Y", "Z"],
    "0": ["0"],
}

# All characters that are explicitly mapped to a group
MAPPED_CHARS = {char for chars in GROUP_MAPPINGS.values() for char in chars}


class CiscoXMLFormatter:
    """Format contacts into Cisco IP Phone XML.

    This class generates XML in Cisco IP Phone format for:
    - Main directory menu with group options (phone keypad style)
    - Group directory menus with filtered contacts
    - Individual contact directories with phone numbers
    - Help screens for different contexts
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize formatter.

        Args:
            base_url: Base URL for generating links in XML output
        """
        self.base_url = base_url.rstrip("/")

    def generate_main_directory(self) -> str:
        """Generate main directory menu with group options.

        Creates a CiscoIPPhoneMenu with menu items for each phone keypad
        group (1, 2ABC, 3DEF, etc.).

        Returns:
            XML string for main directory menu
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

    def generate_group_directory(
        self, group: str, contacts: List["Contact"]
    ) -> str:
        """Generate directory menu for a specific group.

        Creates a CiscoIPPhoneMenu listing contacts in the specified group.

        Args:
            group: Group identifier (e.g., "2ABC")
            contacts: List of contacts in this group

        Returns:
            XML string for group directory menu
        """
        root = etree.Element("CiscoIPPhoneMenu")

        # Title
        title = etree.SubElement(root, "Title")
        title.text = group

        if contacts:
            # Add menu items for each contact
            for contact in contacts:
                item = etree.SubElement(root, "MenuItem")

                name = etree.SubElement(item, "Name")
                # lxml handles XML escaping automatically when setting .text
                # Defensive: ensure display_name is never empty
                display = contact.display_name.strip() if contact.display_name else ""
                name.text = display or "Unnamed Contact"

                url = etree.SubElement(item, "URL")
                url.text = f"{self.base_url}/directory/contacts/{contact.id}"
        else:
            # Empty group - show informational message
            item = etree.SubElement(root, "MenuItem")
            name = etree.SubElement(item, "Name")
            name.text = "(No contacts)"
            url = etree.SubElement(item, "URL")
            # Link back to main directory for empty groups
            url.text = f"{self.base_url}/directory"

        # Add soft keys
        self._add_softkeys(root, show_help=True, help_context=f"group/{group}")

        return self._to_xml_string(root)

    def generate_contact_directory(self, contact: "Contact") -> str:
        """Generate directory for individual contact with phone numbers.

        Creates a CiscoIPPhoneDirectory showing the contact's phone numbers
        with options to call each number.

        Args:
            contact: Contact with phone numbers

        Returns:
            XML string for contact directory
        """
        root = etree.Element("CiscoIPPhoneDirectory")

        # Title - lxml handles XML escaping automatically when setting .text
        title = etree.SubElement(root, "Title")
        # Defensive: ensure display_name is never empty
        display = contact.display_name.strip() if contact.display_name else ""
        title.text = display or "Unnamed Contact"

        # Add phone numbers
        phone_numbers = getattr(contact, "phone_numbers", None) or []
        if phone_numbers:
            # Sort by primary flag (primary first)
            sorted_phones = sorted(phone_numbers, key=lambda p: not p.primary)
            for phone in sorted_phones:
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

    def map_contact_to_group(self, contact: "Contact") -> str:
        """Map contact to appropriate group based on first character.

        Maps the contact's display name to a phone keypad group based on
        the first character:
        - Numbers 1-9 map to their respective groups
        - Letters map to their phone keypad groups (ABC=2, DEF=3, etc.)
        - Special characters and other numbers map to "0"

        Args:
            contact: Contact to map

        Returns:
            Group identifier (e.g., "2ABC", "0")
        """
        # Defensive: handle empty or whitespace-only names
        if not contact.display_name or not contact.display_name.strip():
            return "0"

        first_char = contact.display_name.strip()[0].upper()

        for group, chars in GROUP_MAPPINGS.items():
            if first_char in chars:
                return group

        # Default to "0" for special characters
        return "0"

    def generate_help(self, context: str = "main") -> str:
        """Generate help text for different contexts.

        Creates a CiscoIPPhoneText screen with context-specific help
        instructions.

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
                "Select a group (e.g., 2ABC) to view contacts "
                "starting with those letters.\n\n"
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
            text.text = (
                "Use the menu to navigate the directory. "
                "Press Exit to return to main menu."
            )

        # Soft key to go back
        soft_key = etree.SubElement(root, "SoftKeyItem")
        key_name = etree.SubElement(soft_key, "Name")
        key_name.text = "Back"
        key_position = etree.SubElement(soft_key, "Position")
        key_position.text = "1"
        key_url = etree.SubElement(soft_key, "URL")
        key_url.text = "SoftKey:Back"

        return self._to_xml_string(root)

    def _add_softkeys(
        self,
        root: etree._Element,
        show_help: bool = False,
        help_context: str = "main",
    ) -> None:
        """Add standard soft keys to menu.

        Adds Exit, View, and optionally Help soft keys to a menu element.

        Args:
            root: XML root element
            show_help: Whether to include help button
            help_context: Context for help (main, group/<group>, contact)
        """
        # Exit key - Position 1
        exit_key = etree.SubElement(root, "SoftKeyItem")
        exit_name = etree.SubElement(exit_key, "Name")
        exit_name.text = "Exit"
        exit_position = etree.SubElement(exit_key, "Position")
        exit_position.text = "1"
        exit_url = etree.SubElement(exit_key, "URL")
        exit_url.text = "Init:Directories"

        # View/Select key - Position 2
        view_key = etree.SubElement(root, "SoftKeyItem")
        view_name = etree.SubElement(view_key, "Name")
        view_name.text = "View"
        view_position = etree.SubElement(view_key, "Position")
        view_position.text = "2"
        view_url = etree.SubElement(view_key, "URL")
        view_url.text = "SoftKey:Select"

        # Optional help key - Position 4
        if show_help:
            help_key = etree.SubElement(root, "SoftKeyItem")
            help_name = etree.SubElement(help_key, "Name")
            help_name.text = "Help"
            help_position = etree.SubElement(help_key, "Position")
            help_position.text = "4"
            help_url = etree.SubElement(help_key, "URL")
            help_url.text = f"{self.base_url}/directory/help?context={help_context}"

    def _to_xml_string(self, root: etree._Element) -> str:
        """Convert XML element to string with proper formatting.

        Args:
            root: XML root element

        Returns:
            Formatted XML string with UTF-8 encoding declaration
        """
        xml_str: str = etree.tostring(
            root,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=False,
        ).decode("utf-8")

        return xml_str


def get_xml_formatter(base_url: str = "http://localhost:8000") -> CiscoXMLFormatter:
    """Get XML formatter instance.

    Factory function to create a CiscoXMLFormatter with the specified
    base URL.

    Args:
        base_url: Base URL for generating links

    Returns:
        CiscoXMLFormatter instance
    """
    return CiscoXMLFormatter(base_url)

