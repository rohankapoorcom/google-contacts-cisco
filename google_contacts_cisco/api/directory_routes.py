"""Cisco IP Phone directory routes.

This module provides FastAPI endpoints to serve the Cisco IP Phone XML directory.
It implements a three-level hierarchy: main menu → group menu → individual contact.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from lxml import etree
from sqlalchemy.orm import Session

from ..models import Contact, get_db
from ..repositories.contact_repository import ContactRepository
from ..services.xml_formatter import get_xml_formatter
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/directory", tags=["Cisco Directory"])


def get_base_url(request: Request) -> str:
    """Get base URL from request.

    Args:
        request: FastAPI request

    Returns:
        Base URL string (e.g., "http://localhost:8000")
    """
    return f"{request.url.scheme}://{request.url.netloc}"


def _error_response(message: str) -> Response:
    """Generate error XML response.

    Creates a CiscoIPPhoneText error screen that displays properly
    on Cisco IP Phones. Returns HTTP 200 status because Cisco phones
    expect 200 even for error conditions.

    Args:
        message: Error message to display

    Returns:
        Response with error XML
    """
    root = etree.Element("CiscoIPPhoneText")

    title = etree.SubElement(root, "Title")
    title.text = "Error"

    text = etree.SubElement(root, "Text")
    text.text = message

    # Add prompt
    prompt = etree.SubElement(root, "Prompt")
    prompt.text = "Press Exit to return"

    # Add Exit soft key
    exit_key = etree.SubElement(root, "SoftKeyItem")
    exit_name = etree.SubElement(exit_key, "Name")
    exit_name.text = "Exit"
    exit_position = etree.SubElement(exit_key, "Position")
    exit_position.text = "1"
    exit_url = etree.SubElement(exit_key, "URL")
    exit_url.text = "Init:Directories"

    xml_str = etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
    ).decode("utf-8")

    return Response(
        content=xml_str,
        media_type="text/xml; charset=utf-8",
        status_code=200,  # Cisco phones expect 200 even for errors
    )


@router.get("")
async def get_main_directory(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Get main directory menu with group options.

    Returns XML menu for Cisco IP Phone main directory with phone keypad
    groups (1, 2ABC, 3DEF, etc.).

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Response with main directory XML
    """
    try:
        base_url = get_base_url(request)
        formatter = get_xml_formatter(base_url)

        xml_content = formatter.generate_main_directory()

        logger.info("Generated main directory XML")

        return Response(
            content=xml_content,
            media_type="text/xml; charset=utf-8",
        )

    except Exception as e:
        logger.error("Error generating main directory: %s", e)
        return _error_response("Error loading directory")


@router.get("/groups/{group}")
async def get_group_directory(
    group: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Get directory for specific group.

    Returns XML menu with contacts in the specified phone keypad group.

    Args:
        group: Group identifier (e.g., "2ABC")
        request: FastAPI request
        db: Database session

    Returns:
        Response with group directory XML
    """
    try:
        base_url = get_base_url(request)
        formatter = get_xml_formatter(base_url)
        contact_repo = ContactRepository(db)

        # Get all active contacts with phone numbers
        all_contacts = contact_repo.get_all_active_with_phones()

        # Filter contacts by group
        group_upper = group.upper()
        group_contacts = [
            c for c in all_contacts if formatter.map_contact_to_group(c) == group_upper
        ]

        # Sort by display name
        group_contacts.sort(key=lambda c: c.display_name.lower())

        xml_content = formatter.generate_group_directory(group, group_contacts)

        logger.info(
            "Generated group directory for %s: %d contacts", group, len(group_contacts)
        )

        return Response(
            content=xml_content,
            media_type="text/xml; charset=utf-8",
        )

    except Exception as e:
        logger.error("Error generating group directory for %s: %s", group, e)
        return _error_response(f"Error loading group {group}")


@router.get("/contacts/{contact_id}")
async def get_contact_directory(
    contact_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Get directory for individual contact.

    Returns XML directory with contact's phone numbers that can be dialed
    directly from the Cisco IP Phone.

    Args:
        contact_id: Contact UUID
        request: FastAPI request
        db: Database session

    Returns:
        Response with contact directory XML
    """
    try:
        base_url = get_base_url(request)
        formatter = get_xml_formatter(base_url)

        # Get contact from database
        contact = db.query(Contact).filter(Contact.id == contact_id).first()

        if not contact:
            logger.warning("Contact not found: %s", contact_id)
            return _error_response("Contact not found")

        if contact.deleted:
            logger.warning("Contact deleted: %s", contact_id)
            return _error_response("Contact no longer available")

        xml_content = formatter.generate_contact_directory(contact)

        logger.info("Generated contact directory for %s", contact.display_name)

        return Response(
            content=xml_content,
            media_type="text/xml; charset=utf-8",
        )

    except ValueError as e:
        logger.error("Invalid contact ID: %s - %s", contact_id, e)
        return _error_response("Invalid contact")

    except Exception as e:
        logger.error("Error generating contact directory for %s: %s", contact_id, e)
        return _error_response("Error loading contact")


@router.get("/help")
async def get_help(
    request: Request,
    context: str = "main",
) -> Response:
    """Get help text for directory.

    Returns context-specific help text in Cisco XML format.

    Args:
        request: FastAPI request
        context: Help context (main, group/<group>, contact)

    Returns:
        Response with help text XML
    """
    try:
        logger.info("Generating help for context: %s", context)

        # Get formatter with base URL
        base_url = get_base_url(request)
        formatter = get_xml_formatter(base_url)

        # Generate help
        xml = formatter.generate_help(context)

        logger.debug("Help XML generated for context %s", context)
        return Response(content=xml, media_type="text/xml; charset=utf-8")

    except Exception as e:
        logger.error("Error generating help: %s", e, exc_info=True)
        return _error_response("Error loading help")
