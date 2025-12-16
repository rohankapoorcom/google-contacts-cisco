# Cisco IP Phone XML Requirements

## Overview

Cisco IP Phones use a specific XML format to display directory information. This document outlines the requirements and specifications for generating XML that Cisco IP Phones can consume.

## Research Needed

### Key Questions to Answer
1. What is the exact XML schema/structure required?
2. What are the character limits for names and phone numbers?
3. How does pagination work in Cisco XML directories?
4. What HTTP headers are required?
5. Are there any authentication requirements?
6. What Cisco phone models will be supported?

## Cisco XML Object Format

Based on the example directory structure, Cisco IP Phones use a hierarchical menu system with the following structure:

### Main Directory Menu (`/directory`)

Returns a `CiscoIPPhoneMenu` with group menu items organized by phone keypad groupings:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneMenu>
    <Title>Contacts</Title>
    <MenuItem>
        <Name>1</Name>
        <URL>http://server/directory/groups/1</URL>
    </MenuItem>
    <MenuItem>
        <Name>2ABC</Name>
        <URL>http://server/directory/groups/2ABC</URL>
    </MenuItem>
    <MenuItem>
        <Name>3DEF</Name>
        <URL>http://server/directory/groups/3DEF</URL>
    </MenuItem>
    <!-- More group menu items: 4GHI, 5JKL, 6MNO, 7PRQS, 8TUV, 9WXYZ, 0 -->
    <SoftKeyItem>
        <Name>Exit</Name>
        <Position>1</Position>
        <URL>Init:Directories</URL>
    </SoftKeyItem>
    <SoftKeyItem>
        <Name>View</Name>
        <Position>2</Position>
        <URL>SoftKey:Select</URL>
    </SoftKeyItem>
    <SoftKeyItem>
        <Name>Help</Name>
        <Position>3</Position>
        <URL>http://server/directory/help?name=</URL>
    </SoftKeyItem>
</CiscoIPPhoneMenu>
```

### Directory Groups Menu (`/directory/groups/<group>`)

Returns a `CiscoIPPhoneMenu` with contact names filtered by the group parameter:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneMenu>
    <Title>2ABC</Title>
    <MenuItem>
        <Name>Contact Name</Name>
        <URL>http://server/directory/contacts/<contact_id></URL>
    </MenuItem>
    <!-- More contact menu items -->
    <SoftKeyItem>
        <Name>Exit</Name>
        <Position>1</Position>
        <URL>Init:Directories</URL>
    </SoftKeyItem>
    <SoftKeyItem>
        <Name>View</Name>
        <Position>2</Position>
        <URL>SoftKey:Select</URL>
    </SoftKeyItem>
    <SoftKeyItem>
        <Name>Help</Name>
        <Position>3</Position>
        <URL>http://server/directory/help?name=</URL>
    </SoftKeyItem>
</CiscoIPPhoneMenu>
```

### Individual Contact Directory (`/directory/contacts/<id>`)

Returns a `CiscoIPPhoneDirectory` with phone numbers for the selected contact:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneDirectory>
    <Title>Contact Name</Title>
    <DirectoryEntry>
        <Name>Mobile</Name>
        <Telephone>(415) 824-6444</Telephone>
    </DirectoryEntry>
    <DirectoryEntry>
        <Name>Work</Name>
        <Telephone>(415) 555-1234</Telephone>
    </DirectoryEntry>
    <!-- More phone number entries -->
    <SoftKeyItem>
        <Name>Exit</Name>
        <Position>1</Position>
        <URL>http://server/directory?name=</URL>
    </SoftKeyItem>
    <SoftKeyItem>
        <Name>Call</Name>
        <Position>2</Position>
        <URL>SoftKey:Select</URL>
    </SoftKeyItem>
</CiscoIPPhoneDirectory>
```

## Requirements

### Endpoint Structure

The application must support the following RESTful hierarchical endpoint structure:

1. **`GET /directory`** - Main directory menu with group options
2. **`GET /directory/groups/<group>`** - Contact list for a specific group (e.g., `/directory/groups/2ABC`)
3. **`GET /directory/contacts/<id>`** - Individual contact phone numbers

**Parameters:**
- `<group>` - Path parameter for the group value (1, 2ABC, 3DEF, 4GHI, 5JKL, 6MNO, 7PRQS, 8TUV, 9WXYZ, 0)
- `<id>` - Path parameter for the contact identifier (Google Contacts resource name or internal database ID)

### Group Parameter

The group parameter supports phone keypad-based navigation:
- **"1"** - Contacts starting with 1 or numbers
- **"2ABC"** - Contacts starting with 2, A, B, or C
- **"3DEF"** - Contacts starting with 3, D, E, or F
- **"4GHI"** - Contacts starting with 4, G, H, or I
- **"5JKL"** - Contacts starting with 5, J, K, or L
- **"6MNO"** - Contacts starting with 6, M, N, or O
- **"7PRQS"** - Contacts starting with 7, P, Q, R, or S
- **"8TUV"** - Contacts starting with 8, T, U, or V
- **"9WXYZ"** - Contacts starting with 9, W, X, Y, or Z
- **"0"** - Contacts starting with 0 or other characters

### XML Structure Requirements

#### Main Directory Menu (`CiscoIPPhoneMenu`)
- **Root Element**: `CiscoIPPhoneMenu`
- **Title**: Menu title (e.g., "Contacts")
- **MenuItem**: Each group option
  - **Name**: Display name for the group (e.g., "2ABC")
  - **URL**: Link to groups endpoint with group path parameter (e.g., `/directory/groups/2ABC`)
- **SoftKeyItem**: Navigation buttons
  - **Name**: Button label (Exit, View, Help)
  - **Position**: Button position (1, 2, 3)
  - **URL**: Action URL or softkey command

#### Directory Groups Menu (`CiscoIPPhoneMenu`)
- **Root Element**: `CiscoIPPhoneMenu`
- **Title**: Group value (e.g., "2ABC")
- **MenuItem**: Each contact in the group
  - **Name**: Contact display name
  - **URL**: Link to contact endpoint with id path parameter (e.g., `/directory/contacts/<id>`)
- **SoftKeyItem**: Navigation buttons (same as main menu)

#### Individual Contact Directory (`CiscoIPPhoneDirectory`)
- **Root Element**: `CiscoIPPhoneDirectory`
- **Title**: Contact display name
- **DirectoryEntry**: Each phone number for the contact
  - **Name**: Phone number type/label (e.g., "Mobile", "Work", "Home")
  - **Telephone**: Formatted phone number
- **SoftKeyItem**: Action buttons
  - **Name**: Button label (Exit, Call)
  - **Position**: Button position
  - **URL**: Action URL or softkey command

### Display Constraints
- **Menu Item Name Length**: Typically limited to ~30-40 characters (needs verification)
- **Contact Name Length**: Should be truncated if too long for phone display
- **Phone Number Format**: Should be formatted for display (with dashes, parentheses, spaces)
- **Total Entries per Index**: May need pagination if an index group has many contacts
- **Phone Number Labels**: Use descriptive labels (Mobile, Work, Home, etc.)

### Character Encoding
- Must use UTF-8 encoding
- Special characters must be properly escaped
- XML entities must be used for special characters (`&`, `<`, `>`, `"`, `'`)

### HTTP Requirements
- **Content-Type**: `text/xml` or `application/xml`
- **Character Encoding**: UTF-8
- **HTTP Method**: GET
- **Status Code**: 200 OK

### Phone Number Handling
- **Multiple phone numbers per contact**: Each phone number should be a separate `DirectoryEntry` in the individual contact view
- **Phone number types**: Display appropriate labels (Mobile, Work, Home, Other, etc.)
- **Phone number format**: Format numbers for display (e.g., "(415) 824-6444" or "415-824-6444")
- **Primary phone number**: If a contact has a primary phone number, it should be listed first

### Group-Based Filtering
- **Contact name grouping**: Contacts must be filtered by the first character of their display name
- **Group mapping**: Map contact names to appropriate group based on first character:
  - Numbers (0-9) → "1" or "0" group
  - Letters A-C → "2ABC" group
  - Letters D-F → "3DEF" group
  - Letters G-I → "4GHI" group
  - Letters J-L → "5JKL" group
  - Letters M-O → "6MNO" group
  - Letters P-S → "7PRQS" group
  - Letters T-V → "8TUV" group
  - Letters W-Z → "9WXYZ" group
- **Case insensitivity**: Group matching should be case-insensitive
- **Special characters**: Contacts starting with special characters should be grouped appropriately (e.g., in "0" group)

## Implementation Tasks

### Task 1: Research and Documentation
- [ ] Research Cisco IP Phone XML Object specification
- [ ] Review example directory structure
- [ ] Test with actual Cisco IP Phone if available
- [ ] Document exact requirements
- [ ] Create test cases

### Task 2: Index-Based Contact Grouping
- [ ] Implement contact name to index mapping logic
- [ ] Create function to determine index for a contact name
- [ ] Handle case-insensitive matching
- [ ] Handle special characters and numbers
- [ ] Test index grouping with various contact names

### Task 3: XML Generation - Main Directory Menu
- [ ] Create endpoint `GET /directory`
- [ ] Generate `CiscoIPPhoneMenu` with index menu items
- [ ] Include all required index options (1, 2ABC, 3DEF, etc.)
- [ ] Add SoftKeyItems (Exit, View, Help)
- [ ] Handle character encoding and XML escaping

### Task 4: XML Generation - Directory Groups Menu
- [ ] Create endpoint `GET /directory/groups/<group>`
- [ ] Parse and validate group path parameter
- [ ] Filter contacts by group
- [ ] Generate `CiscoIPPhoneMenu` with contact names
- [ ] Include contact id in menu item URLs (e.g., `/directory/contacts/<id>`)
- [ ] Add SoftKeyItems (Exit, View, Help)
- [ ] Handle empty index groups

### Task 5: XML Generation - Individual Contact Directory
- [ ] Create endpoint `GET /directory/contacts/<id>`
- [ ] Parse and validate id path parameter
- [ ] Retrieve contact by id
- [ ] Generate `CiscoIPPhoneDirectory` with phone numbers
- [ ] Format phone numbers appropriately
- [ ] Include phone number type labels
- [ ] Add SoftKeyItems (Exit, Call)
- [ ] Handle contacts with no phone numbers

### Task 6: XML Utilities
- [ ] Create XML formatter utility class
- [ ] Implement proper XML structure generation
- [ ] Handle character encoding (UTF-8)
- [ ] Escape special characters (XML entities)
- [ ] Format phone numbers for display
- [ ] Handle name truncation if needed

### Task 7: Pagination (if needed for large index groups)
- [ ] Determine if pagination is needed for index groups
- [ ] Research pagination mechanism for Cisco menus
- [ ] Implement pagination logic if required
- [ ] Create navigation links
- [ ] Test with large contact lists in a single index

### Task 8: Testing
- [ ] Create XML output samples for each endpoint
- [ ] Validate XML structure against examples
- [ ] Test with Cisco IP Phone or simulator
- [ ] Verify display formatting
- [ ] Test with various contact name lengths
- [ ] Test with various phone number formats
- [ ] Test index filtering with edge cases
- [ ] Test special characters in contact names
- [ ] Test contacts with multiple phone numbers

## Known Cisco IP Phone Models

Common models that may need support:
- Cisco 7800 Series
- Cisco 8800 Series
- Cisco 7900 Series
- Other models as needed

## Resources

### Documentation to Review
- Cisco IP Phone XML Object Developer Guide
- Cisco IP Phone Customization Guide
- Cisco IP Phone XML Services documentation
- Sample XML directory implementations

### Testing Tools
- Cisco IP Phone simulator (if available)
- XML validators
- HTTP testing tools (curl, Postman)

## API Endpoints Required

### Main Directory Endpoint
- **Route**: `GET /directory`
- **Parameters**: None (optional `name` parameter may be supported)
- **Response**: `CiscoIPPhoneMenu` with index menu items
- **Purpose**: Entry point for directory navigation

### Directory Groups Endpoint
- **Route**: `GET /directory/groups/<group>`
- **Path Parameters**: 
  - `<group>` (required): Group value (1, 2ABC, 3DEF, 4GHI, 5JKL, 6MNO, 7PRQS, 8TUV, 9WXYZ, 0)
- **Response**: `CiscoIPPhoneMenu` with contacts for the specified group
- **Purpose**: Display contacts filtered by group

### Individual Contact Endpoint
- **Route**: `GET /directory/contacts/<id>`
- **Path Parameters**:
  - `<id>` (required): Unique identifier for the contact (Google Contacts resource name or internal database ID)
- **Response**: `CiscoIPPhoneDirectory` with phone numbers for the contact
- **Purpose**: Display phone numbers for a specific contact

### Help Endpoint (Optional)
- **Route**: `GET /directory/help`
- **Parameters**: `name` (optional)
- **Response**: Help information (format TBD)
- **Purpose**: Provide help information to users

## Assumptions (to be verified)

1. XML format follows standard Cisco IP Phone XML Object structure
2. No authentication required for directory access (or basic auth)
3. Index parameter is case-insensitive
4. ResourceName corresponds to Google Contacts resource name or internal ID
5. Pagination may be needed for index groups with many contacts
6. Character limits are consistent across phone models
7. Phone numbers can be in various formats (phone will handle formatting)
8. The `name` parameter in URLs may be optional or used for filtering

## Notes

- This document is based on analysis of a working example directory implementation
- The hierarchical menu structure (main menu → index menu → contact list → individual contact) is required
- Group-based navigation uses phone keypad groupings (2ABC, 3DEF, etc.)
- The contact `id` path parameter should map to Google Contacts resource names or internal database IDs
- RESTful path parameters provide clean, semantic URLs that are easy to understand and maintain
- Testing with actual Cisco IP Phones is critical to verify display formatting
- Format may vary slightly between phone models, but the basic structure should be consistent
- Special characters in contact names (like `&`) must be properly escaped as XML entities (`&amp;`)
- URL parameters should be properly URL-encoded in the XML output

