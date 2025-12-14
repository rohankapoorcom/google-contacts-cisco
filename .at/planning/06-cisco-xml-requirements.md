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

## Cisco XML Object Format (Preliminary)

Based on general Cisco IP Phone XML specifications, the format typically follows this structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneDirectory>
    <Title>Directory</Title>
    <Prompt>Select a contact</Prompt>
    <DirectoryEntry>
        <Name>Contact Name</Name>
        <Telephone>1234567890</Telephone>
    </DirectoryEntry>
    <DirectoryEntry>
        <Name>Another Contact</Name>
        <Telephone>0987654321</Telephone>
    </DirectoryEntry>
    <!-- More entries -->
    <SoftKeyItem>
        <Name>Exit</Name>
        <URL>SoftKey:Exit</URL>
        <Position>1</Position>
    </SoftKeyItem>
</CiscoIPPhoneDirectory>
```

## Requirements

### XML Structure Requirements
- **Root Element**: Must be `CiscoIPPhoneDirectory`
- **Title**: Directory title (e.g., "Google Contacts")
- **Prompt**: User prompt text
- **DirectoryEntry**: Each contact entry
  - **Name**: Contact display name
  - **Telephone**: Phone number

### Display Constraints
- **Name Length**: Typically limited to ~30-40 characters (needs verification)
- **Phone Number Format**: Should be formatted for display (with dashes/spaces)
- **Total Entries**: May need pagination for large directories

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
- Multiple phone numbers per contact: Need to decide strategy
  - Option 1: Create separate entries for each phone number
  - Option 2: Display primary phone number only
  - Option 3: Combine multiple numbers (may exceed display limits)
- Phone number format: Should match phone's expected format

## Implementation Tasks

### Task 1: Research and Documentation
- [ ] Research Cisco IP Phone XML Object specification
- [ ] Find official documentation or examples
- [ ] Test with actual Cisco IP Phone if available
- [ ] Document exact requirements
- [ ] Create test cases

### Task 2: XML Generation
- [ ] Create XML formatter class
- [ ] Implement proper XML structure
- [ ] Handle character encoding
- [ ] Escape special characters
- [ ] Format phone numbers appropriately
- [ ] Handle name truncation if needed

### Task 3: Pagination (if needed)
- [ ] Research pagination mechanism
- [ ] Implement pagination logic
- [ ] Create navigation links
- [ ] Test with large contact lists

### Task 4: Testing
- [ ] Create XML output samples
- [ ] Validate XML structure
- [ ] Test with Cisco IP Phone or simulator
- [ ] Verify display formatting
- [ ] Test with various contact name lengths
- [ ] Test with various phone number formats

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

## Assumptions (to be verified)

1. XML format follows standard Cisco IP Phone XML Object structure
2. No authentication required for directory access (or basic auth)
3. Pagination uses standard Cisco XML pagination mechanism
4. Character limits are consistent across phone models
5. Phone numbers can be in various formats (phone will handle formatting)

## Notes

- This is a preliminary document based on general knowledge
- Specific requirements need to be researched and verified
- Testing with actual Cisco IP Phones is critical
- Format may vary slightly between phone models
- May need to support multiple XML formats for different phone models

