# Cisco IP Phone Configuration Guide

## Overview

This guide explains how to configure Cisco IP Phones to access the Google Contacts directory provided by this application. The directory appears on your phone just like the corporate directory, allowing you to browse and dial contacts directly from your Google Contacts.

## Table of Contents

1. [Supported Phone Models](#supported-phone-models)
2. [Prerequisites](#prerequisites)
3. [Configuration Methods](#configuration-methods)
4. [Manual Configuration](#manual-configuration)
5. [CUCM Configuration](#cucm-configuration)
6. [Testing and Verification](#testing-and-verification)
7. [Directory Navigation](#directory-navigation)
8. [Troubleshooting](#troubleshooting)

---

## Supported Phone Models

### Tested Models

- Cisco 7940/7960 Series
- Cisco 7941/7961 Series
- Cisco 7942/7962 Series
- Cisco 7945/7965 Series
- Cisco 7970/7971 Series
- Cisco 8800 Series
- Cisco 9900 Series

### Requirements

- IP Phone must support Cisco IP Phone Services
- Phone must have network access to application server
- Firmware supporting XML services (most modern firmware versions)

---

## Prerequisites

### Application Setup

1. **Application Running**
   ```bash
   # Verify application is running
   curl http://YOUR_SERVER:8000/health
   ```

2. **Contacts Synced**
   ```bash
   # Check sync status
   curl http://YOUR_SERVER:8000/api/sync/status
   ```

3. **Directory Accessible**
   ```bash
   # Test directory XML
   curl http://YOUR_SERVER:8000/directory
   ```

### Network Requirements

1. **Phone Can Reach Server**
   ```bash
   # From a computer on same network as phone
   ping YOUR_SERVER
   curl http://YOUR_SERVER:8000/directory
   ```

2. **Firewall Rules**
   - Allow HTTP traffic on port 8000 (or your configured port)
   - Allow traffic from phone subnet to server

3. **DNS Resolution** (if using hostname)
   ```bash
   # Verify DNS resolution
   nslookup YOUR_SERVER
   ```

---

## Configuration Methods

There are three ways to configure the directory service on Cisco IP Phones:

1. **Manual Configuration** - Configure directly on each phone (good for testing)
2. **CUCM Configuration** - Configure via Cisco Unified Communications Manager (enterprise)
3. **Configuration File** - Push config via TFTP/HTTP provisioning

This guide covers methods 1 and 2. Method 3 is specific to your provisioning setup.

---

## Manual Configuration

### Step 1: Access Phone Settings

1. **Press Services Button**
   - On the phone, press the "Services" button (or "Applications" on newer models)

2. **Access Settings**
   - If no services are configured, you'll see an empty list
   - Press the "Settings" soft key (or go to Settings menu)

### Step 2: Configure Service

Different phone models have slightly different menu structures. Choose your model:

#### Option A: 7940/7960/7941/7961 Series

1. Press the **Settings** button on the phone
2. Navigate to **Network Configuration**
3. Enter network password (default: cisco)
4. Scroll to **IP Phone Services**
5. Press **Setup** soft key
6. Select **New** soft key
7. Enter service details:
   - **Service Name**: `Google Contacts`
   - **Service URL**: `http://YOUR_SERVER:8000/directory`
8. Press **Submit**
9. Press **Exit** until back to home screen

#### Option B: 7942/7962/7945/7965 Series

1. Press **Applications** button
2. Select **Phone Services**
3. Press **Configure** soft key
4. Press **New** soft key
5. Enter service details:
   - **Service Name**: `Google Contacts`
   - **Service URL**: `http://YOUR_SERVER:8000/directory`
6. Press **Subscribe**
7. Press **Exit**

#### Option C: 8800/9900 Series

1. Press **Applications** button
2. Select **Phone Settings**
3. Select **Services**
4. Press **Add New**
5. Enter:
   - **Name**: `Google Contacts`
   - **URL**: `http://YOUR_SERVER:8000/directory`
6. Press **Submit**
7. Press **Back** to return

### Step 3: Subscribe to Service

1. **Press Services/Applications Button**
2. **Select "Google Contacts"** from the list
3. **Confirm Subscription** if prompted

### Step 4: Test Directory

1. Press **Services/Applications** button
2. Select **Google Contacts**
3. You should see the main menu with keypad groups (1, 2ABC, 3DEF, etc.)

---

## CUCM Configuration

### Prerequisites

- Access to Cisco Unified Communications Manager (CUCM) Administration
- Administrative credentials
- CUCM version 8.0 or higher

### Step 1: Create IP Phone Service

1. **Log in to CUCM Administration**
   - URL: `https://YOUR_CUCM/ccmadmin`

2. **Navigate to IP Phone Services**
   - Device → Device Settings → Phone Services

3. **Add New Service**
   - Click "Add New"

4. **Configure Service**
   - **Service Name**: `Google Contacts`
   - **Service Description**: `Google Contacts Directory`
   - **Service URL**: `http://YOUR_SERVER:8000/directory`
   - **Service Category**: Directory (XML)
   - **Service Type**: Standard IP Phone Service
   - **Enable**: ✓ Checked

5. **Service Parameters** (none required for this service)

6. **Save**
   - Click "Save"

### Step 2: Subscribe Phones to Service

#### Option A: Individual Phone Configuration

1. **Navigate to Phone Configuration**
   - Device → Phone → Find

2. **Select Phone**
   - Search for and select the phone

3. **Go to Subscribe Services**
   - Click "Subscribe/Unsubscribe Services" button

4. **Subscribe to Service**
   - Find "Google Contacts" in the list
   - Click "Subscribe"
   - Click "Save"

5. **Reset Phone**
   - Click "Reset" button
   - Select "Restart"

#### Option B: Bulk Phone Configuration

1. **Create Device Profile** (Optional)
   - Device → Device Settings → Device Profile

2. **Use BAT (Bulk Administration Tool)**
   - Bulk Administration → Phones → Update Phones
   - Select phones by criteria
   - Add service subscription
   - Apply changes

3. **Reset Phones**
   - Bulk Administration → Phones → Reset Phones

### Step 3: Set as Default Directory (Optional)

To make Google Contacts the default directory when users press the "Directories" button:

1. **Edit Phone Configuration**
   - Device → Phone → Find → [Select Phone]

2. **Scroll to Services Configuration**
   - Find "Services URL" or "Directory URL" section

3. **Set Directory URL**
   - **Directories URL**: `http://YOUR_SERVER:8000/directory`

4. **Save and Reset**

**Note**: This varies by CUCM version and phone model. Some phones don't support overriding the default directory.

---

## Testing and Verification

### Basic Connectivity Test

1. **Test from Browser**
   ```bash
   # Should return XML
   curl http://YOUR_SERVER:8000/directory
   ```

2. **Expected Output**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <CiscoIPPhoneMenu>
     <Title>Google Contacts</Title>
     <Prompt>Select a group</Prompt>
     <MenuItem>
       <Name>1</Name>
       <URL>http://YOUR_SERVER:8000/directory/groups/1</URL>
     </MenuItem>
     <!-- More items... -->
   </CiscoIPPhoneMenu>
   ```

### Phone-Side Testing

1. **Access Service**
   - Press Services/Applications button
   - Select "Google Contacts"

2. **Navigate Directory**
   - Press a keypad group (e.g., "2ABC")
   - Should show contacts in that group

3. **Select Contact**
   - Press a contact name
   - Should show phone numbers

4. **Dial Contact**
   - Press a phone number
   - Phone should dial the number

### Common Test Scenarios

#### Test Case 1: Empty Contacts

**Scenario**: No contacts synced yet

**Expected**: Empty groups with message "No contacts in this group"

**Fix**: Sync contacts from Google

#### Test Case 2: Large Contact List

**Scenario**: >1000 contacts

**Expected**: Directory loads normally, pagination works

**Verify**: Check all groups populate correctly

#### Test Case 3: Special Characters

**Scenario**: Contact names with special characters (é, ñ, 中文, etc.)

**Expected**: Characters display correctly on phone screen

**Note**: UTF-8 encoding is used; most modern phones support it

---

## Directory Navigation

### Directory Structure

```
Main Menu (Google Contacts)
├── 1
│   └── Contacts starting with 1
├── 2ABC
│   ├── Contacts starting with 2
│   ├── Contacts starting with A
│   ├── Contacts starting with B
│   └── Contacts starting with C
├── 3DEF
│   └── ...
├── ...
└── 9WXYZ
```

### Navigation Flow

1. **Main Menu**
   - Shows keypad groups (1, 2ABC, 3DEF, etc.)
   - Press softkey or use navigation keys
   - Select a group

2. **Group Menu**
   - Shows contacts in selected group
   - Sorted alphabetically
   - Shows contact count in prompt
   - Press "Back" to return to main menu

3. **Contact Menu**
   - Shows contact's name as title
   - Lists all phone numbers
   - Shows number type (Mobile, Work, Home)
   - Select number to dial

4. **Dialing**
   - Press "Dial" softkey
   - Or press selected number
   - Phone initiates call

### Soft Keys

#### Main Menu
- **Exit**: Return to phone home screen

#### Group Menu
- **Back**: Return to main menu
- **Exit**: Return to phone home screen

#### Contact Menu
- **Dial**: Dial selected number
- **Back**: Return to group menu
- **Exit**: Return to phone home screen

---

## Troubleshooting

### Phone Shows "Service Not Available"

**Causes**:
1. Server is not running
2. Network connectivity issue
3. Wrong URL configured
4. Firewall blocking access

**Solutions**:
```bash
# 1. Check server is running
curl http://YOUR_SERVER:8000/health

# 2. Test connectivity from phone network
ping YOUR_SERVER
curl http://YOUR_SERVER:8000/directory

# 3. Verify URL in phone config
# Check for typos, correct port, http vs https

# 4. Check firewall rules
# Allow HTTP traffic from phone subnet to server
```

### Directory Loads But Shows No Contacts

**Causes**:
1. No contacts synced from Google
2. All contacts deleted
3. Sync failed

**Solutions**:
```bash
# Check sync status
curl http://YOUR_SERVER:8000/api/sync/status

# Check contact count
curl http://YOUR_SERVER:8000/api/contacts/stats

# Trigger sync if needed
curl -X POST http://YOUR_SERVER:8000/api/sync

# Verify contacts exist
curl http://YOUR_SERVER:8000/api/contacts?limit=5
```

### XML Parsing Error on Phone

**Symptoms**: Phone shows "XML Error" or "Parse Error"

**Causes**:
1. Invalid XML generated by server
2. Special characters not properly encoded
3. XML too large for phone memory

**Solutions**:
```bash
# 1. Validate XML output
curl http://YOUR_SERVER:8000/directory | xmllint --format -

# 2. Check for encoding issues
curl http://YOUR_SERVER:8000/directory | grep -v "^<?xml" | od -c

# 3. Check XML size
curl http://YOUR_SERVER:8000/directory | wc -c
# Should be < 4096 bytes for most phones
```

### Contact Names Display Incorrectly

**Symptoms**: Special characters show as ??? or boxes

**Cause**: Encoding issue or phone firmware doesn't support UTF-8

**Solutions**:
1. **Update Phone Firmware**
   - Latest firmware has better UTF-8 support

2. **Check XML Encoding**
   ```bash
   curl http://YOUR_SERVER:8000/directory | head -1
   # Should show: <?xml version="1.0" encoding="UTF-8"?>
   ```

3. **Contact Names Too Long**
   - Phone screens have character limits
   - Long names are truncated automatically

### Phone Can't Dial Numbers

**Symptoms**: Selecting number doesn't dial

**Causes**:
1. Phone number format incompatible with phone system
2. Phone system requires specific format (e.g., 9 prefix)
3. XML Dial command not working

**Solutions**:
1. **Check Number Format**
   ```bash
   # View contact numbers
   curl http://YOUR_SERVER:8000/api/contacts?limit=1
   
   # Numbers should be in E.164 format: +1234567890
   ```

2. **Modify Dial Plan** (future enhancement)
   - Add prefix (e.g., 9 for external calls)
   - Strip country code if not needed
   - Format for local dialing

3. **Test Dial Command**
   - Manually dial number to verify it works
   - Check CUCM dial plan configuration

### Service Disappears After Phone Reboot

**Cause**: Service not saved in phone configuration

**Solutions**:
1. **For CUCM**:
   - Verify service is subscribed in CUCM
   - Reset phone from CUCM (not manual reboot)

2. **For Manual Config**:
   - Service settings may be stored in volatile memory
   - Need to reconfigure after power loss
   - Consider using TFTP provisioning for persistence

### Slow Directory Loading

**Symptoms**: Directory takes >5 seconds to load

**Causes**:
1. Many contacts (>5000)
2. Slow network
3. Server under load

**Solutions**:
```bash
# 1. Check server performance
curl -w "@- << EOF
    time_namelookup:  %{time_namelookup}
    time_connect:  %{time_connect}
    time_starttransfer:  %{time_starttransfer}
    time_total:  %{time_total}
EOF" http://YOUR_SERVER:8000/directory

# Target: < 200ms total time

# 2. Check network latency
ping -c 10 YOUR_SERVER

# 3. Monitor server resources
top
# CPU usage should be < 50%
```

**Optimizations**:
1. Use caching (future feature)
2. Deploy server closer to phones
3. Reduce contact count by filtering
4. Upgrade server resources

---

## Advanced Configuration

### Custom Group Labels

By default, groups are labeled as keypad groups (2ABC, 3DEF, etc.). These match phone keypads and can't be customized without code changes.

### Integration with Other Directories

Cisco phones can have multiple directory services:

1. **Add Multiple Services**
   - Follow configuration steps for each service
   - Each appears as separate item in Services menu

2. **Combined Directory**
   - Use a proxy/aggregator service
   - Combine Google Contacts with corporate directory
   - Requires custom development

### HTTPS Configuration

For secure connections (recommended for production):

1. **Set up SSL/TLS on server**
   - Use Let's Encrypt or corporate certificates
   - Configure reverse proxy (nginx/Apache)

2. **Update Phone Service URL**
   ```
   https://YOUR_SERVER/directory
   ```

3. **Install CA Certificate on Phones** (if using self-signed)
   - CUCM: OS Administration → Security → Certificate Management
   - Upload CA certificate
   - Phones will trust the certificate

### URL Parameters

The directory service supports optional parameters:

```text
# Base directory
http://YOUR_SERVER:8000/directory

# Specific group
http://YOUR_SERVER:8000/directory/groups/2ABC

# Specific contact
http://YOUR_SERVER:8000/directory/contacts/{contact_id}

# Help page
http://YOUR_SERVER:8000/directory/help?context=main
```

---

## Performance Optimization

### Caching

Cisco phones typically don't cache directory results. Each navigation fetches fresh data.

**Future Enhancement**: Implement HTTP caching headers
```http
Cache-Control: public, max-age=300
```

### Contact Limits

Phones have memory limits for XML responses:

- **Typical limit**: 4KB XML response
- **Recommended**: <100 items per menu
- **Current implementation**: Groups contacts by letter to stay under limits

### Network Optimization

1. **Deploy on Local Network**
   - Same subnet as phones if possible
   - Reduces latency

2. **Use CDN** (for distributed offices)
   - Cache static content
   - Serve directory from edge locations

3. **Compress Responses** (future)
   - Enable gzip compression
   - Reduces bandwidth usage

---

## Best Practices

### Testing

1. **Test with One Phone First**
   - Verify configuration before rolling out

2. **Test All Phone Models**
   - XML rendering varies by model
   - Test navigation and dialing

3. **Test Network Conditions**
   - Wi-Fi vs Ethernet
   - VPN connections
   - Remote office scenarios

### Deployment

1. **Pilot Group**
   - Deploy to small group first
   - Gather feedback
   - Fix issues before full rollout

2. **User Training**
   - Create quick reference guide
   - Show users how to access directory
   - Demonstrate navigation

3. **Monitoring**
   - Monitor directory endpoint performance
   - Track usage patterns
   - Log errors

### Maintenance

1. **Regular Syncs**
   - Enable automatic sync scheduler
   - Contacts stay up to date

2. **Monitor Server Health**
   ```bash
   # Check health endpoint
   curl http://YOUR_SERVER:8000/health
   ```

3. **Update Documentation**
   - Keep phone config docs current
   - Document customizations

---

## Reference

### Cisco IP Phone XML Objects

- [Cisco IP Phone Services SDK](https://developer.cisco.com/site/ip-phone-services/)
- [XML Object Reference](https://www.cisco.com/c/en/us/td/docs/voice_ip_comm/cuipph/all_models/xsi/8_5_1/xsi_dev_guide/xmlobjects.html)

### Supported XML Objects

This application uses:
- `CiscoIPPhoneMenu`: Main and group menus
- `CiscoIPPhoneDirectory`: Contact listings with dial-able numbers
- `CiscoIPPhoneText`: Help and error messages

### URL Schemes

Cisco phones support special URL schemes:
- `Init:Directories`: Return to main directories menu
- `SoftKey:Dial`: Trigger dial action
- `Key:Soft1-4`: Trigger soft keys programmatically

---

## Conclusion

Once configured, the Google Contacts directory integrates seamlessly with your Cisco IP Phone. Users can:

- ✅ Browse contacts by keypad groups
- ✅ Search for contacts (type-ahead on newer models)
- ✅ Dial numbers with one button press
- ✅ Access up-to-date contact information

For issues or questions:
- [Troubleshooting Guide](troubleshooting.md)
- [API Documentation](api.md)
- [Setup Guide](setup.md)
