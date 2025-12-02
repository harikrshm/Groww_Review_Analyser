# IMAP Polling Setup Guide

Complete step-by-step guide for setting up IMAP polling to receive analysis requests via email.

## Overview

The IMAP polling system allows users to send analysis requests via email. The system:
- Connects to your email account via IMAP
- Polls for emails with subject `[ANALYZE]`
- Processes requests automatically
- Sends reply emails with analysis reports

**No domain required** - Works with any email provider that supports IMAP.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Gmail Setup](#gmail-setup)
3. [Outlook Setup](#outlook-setup)
4. [Other Email Providers](#other-email-providers)
5. [Configuration](#configuration)
6. [Environment Variables](#environment-variables)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Email account with IMAP access enabled
- Python environment with required dependencies
- Access to configure environment variables

---

## Gmail Setup

### Step 1: Enable 2-Step Verification

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "2-Step Verification"
3. Click "Get Started" and follow the prompts
4. Complete the setup (phone verification, backup codes, etc.)

**Why**: Gmail requires 2-Step Verification to generate App Passwords for IMAP access.

### Step 2: Generate App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "2-Step Verification" section
3. Click on "App passwords" (below "2-Step Verification")
   - If you don't see "App passwords":
     - Make sure 2-Step Verification is enabled
     - Try accessing directly: https://myaccount.google.com/apppasswords
4. Select app: **Mail**
5. Select device: **Other (Custom name)**
6. Enter name: `Groww Review Analyser`
7. Click **Generate**
8. **Copy the 16-character password** (e.g., `abcd efgh ijkl mnop`)
   - This password is shown only once - save it securely!

**Important**: 
- App passwords are 16 characters with spaces
- You can remove spaces: `abcdefghijklmnop`
- Each app password is unique - you can generate multiple

### Step 3: Verify IMAP is Enabled

1. Go to [Gmail Settings](https://mail.google.com/mail/u/0/#settings/general)
2. Click on "See all settings"
3. Go to "Forwarding and POP/IMAP" tab
4. Under "IMAP access":
   - Select **Enable IMAP**
5. Click **Save Changes**

**Note**: IMAP is usually enabled by default on Gmail accounts.

### Step 4: Configure Environment Variable

Set the App Password as an environment variable:

**Windows PowerShell**:
```powershell
$env:EMAIL_PASSWORD="abcdefghijklmnop"
```

**Windows Command Prompt**:
```cmd
set EMAIL_PASSWORD=abcdefghijklmnop
```

**Linux/Mac**:
```bash
export EMAIL_PASSWORD="abcdefghijklmnop"
```

**Using .env file**:
```
EMAIL_PASSWORD=abcdefghijklmnop
```

**Important**: 
- Use the App Password (not your regular Gmail password)
- Remove spaces from the password
- Keep this password secure - never commit it to git

### Step 5: Update Configuration

Edit `config/inbound_email.json`:

```json
{
  "imap": {
    "server": "imap.gmail.com",
    "port": 993,
    "use_ssl": true,
    "email": "your-email@gmail.com",
    "password_env": "EMAIL_PASSWORD",
    "subject_filter": "[ANALYZE]"
  }
}
```

---

## Outlook Setup

### Step 1: Enable IMAP Access

1. Go to [Outlook Security Settings](https://account.microsoft.com/security)
2. Enable 2-factor authentication if not already enabled
3. IMAP is usually enabled by default

### Step 2: Generate App Password (Optional)

If you have 2FA enabled, you may need an App Password:

1. Go to [Microsoft Account Security](https://account.microsoft.com/security)
2. Click "Advanced security options"
3. Under "App passwords", click "Create a new app password"
4. Enter name: `Groww Review Analyser`
5. Click "Next"
6. Copy the generated password

**Note**: For Outlook, you can often use your regular password if 2FA is not enabled.

### Step 3: Configure Environment Variable

Set the password (App Password or regular password):

```bash
export EMAIL_PASSWORD="your-password"
```

### Step 4: Update Configuration

Edit `config/inbound_email.json`:

```json
{
  "imap": {
    "server": "outlook.office365.com",
    "port": 993,
    "use_ssl": true,
    "email": "your-email@outlook.com",
    "password_env": "EMAIL_PASSWORD",
    "subject_filter": "[ANALYZE]"
  }
}
```

---

## Other Email Providers

### Yahoo Mail

**IMAP Settings**:
- Server: `imap.mail.yahoo.com`
- Port: `993`
- SSL: `true`

**Setup**:
1. Enable IMAP in Yahoo Mail settings
2. Generate App Password (if 2FA enabled)
3. Set as `EMAIL_PASSWORD` environment variable

### Custom IMAP Server

For other providers, use their IMAP settings:

**Common Settings**:
- Port: `993` (SSL) or `143` (TLS)
- SSL/TLS: Usually required

**Configuration**:
```json
{
  "imap": {
    "server": "imap.example.com",
    "port": 993,
    "use_ssl": true,
    "email": "your-email@example.com",
    "password_env": "EMAIL_PASSWORD"
  }
}
```

---

## Configuration

### Complete Configuration Example

Edit `config/inbound_email.json`:

```json
{
  "polling": {
    "enabled": true,
    "interval_seconds": 60,
    "manual_mode": true,
    "continuous_mode": false
  },
  "imap": {
    "server": "imap.gmail.com",
    "port": 993,
    "use_ssl": true,
    "email": "your-email@gmail.com",
    "password_env": "EMAIL_PASSWORD",
    "folder": "INBOX",
    "subject_filter": "[ANALYZE]",
    "processed_folder": "PROCESSED"
  },
  "authorized_senders": {
    "emails": ["your-email@gmail.com", "colleague@example.com"],
    "domains": [],
    "mode": "whitelist"
  },
  "rate_limiting": {
    "enabled": true,
    "max_requests_per_hour": 10,
    "max_requests_per_day": 50
  },
  "default_time_period": {
    "weeks_back": 12
  }
}
```

### Configuration Fields

#### IMAP Settings

| Field | Description | Example |
|-------|-------------|---------|
| `server` | IMAP server address | `imap.gmail.com` |
| `port` | IMAP port (usually 993 for SSL) | `993` |
| `use_ssl` | Use SSL/TLS encryption | `true` |
| `email` | Your email address | `your-email@gmail.com` |
| `password_env` | Environment variable name | `EMAIL_PASSWORD` |
| `folder` | IMAP folder to monitor | `INBOX` |
| `subject_filter` | Subject line filter | `[ANALYZE]` |
| `processed_folder` | Folder for processed emails (optional) | `PROCESSED` |

#### Polling Settings

| Field | Description | Default |
|-------|-------------|---------|
| `enabled` | Enable/disable polling | `true` |
| `interval_seconds` | Polling interval (for continuous mode) | `60` |
| `manual_mode` | Use manual polling via CLI | `true` |
| `continuous_mode` | Enable continuous background polling | `false` |

#### Authorization

| Field | Description | Example |
|-------|-------------|---------|
| `emails` | Whitelist of authorized email addresses | `["email1@example.com"]` |
| `domains` | Whitelist of authorized domains | `["@company.com"]` |
| `mode` | Authorization mode: `whitelist` or `blacklist` | `whitelist` |

#### Rate Limiting

| Field | Description | Default |
|-------|-------------|---------|
| `enabled` | Enable rate limiting | `true` |
| `max_requests_per_hour` | Max requests per hour per sender | `10` |
| `max_requests_per_day` | Max requests per day per sender | `50` |

---

## Environment Variables

### Setting Environment Variables

#### Option 1: Command Line (Temporary)

**Windows PowerShell**:
```powershell
$env:EMAIL_PASSWORD="your-app-password"
```

**Linux/Mac**:
```bash
export EMAIL_PASSWORD="your-app-password"
```

**Note**: These are temporary and will be lost when the terminal closes.

#### Option 2: .env File (Recommended)

Create a `.env` file in the project root:

```
EMAIL_PASSWORD=your-app-password
```

Load it in your application (if using `python-dotenv`):
```python
from dotenv import load_dotenv
load_dotenv()
```

#### Option 3: System Environment (Permanent)

**Windows**:
1. Open System Properties → Environment Variables
2. Add new User variable:
   - Name: `EMAIL_PASSWORD`
   - Value: `your-app-password`

**Linux/Mac**:
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export EMAIL_PASSWORD="your-app-password"
```

Then reload:
```bash
source ~/.bashrc
```

### Security Best Practices

- ✅ **Do**: Use App Passwords (not regular passwords)
- ✅ **Do**: Store passwords in `.env` file (add to `.gitignore`)
- ✅ **Do**: Use environment variables in production
- ❌ **Don't**: Commit passwords to git
- ❌ **Don't**: Hardcode passwords in configuration files
- ❌ **Don't**: Share App Passwords

---

## Testing

### Step 1: Test Configuration

Check your configuration:

```bash
python scripts/test_email_interface.py check-config
```

Expected output:
```
Checking Email Interface Configuration
✓ Polling Enabled: Yes
✓ IMAP Server: imap.gmail.com
✓ Email Account: your-email@gmail.com
✓ EMAIL_PASSWORD: ✅ Set
```

### Step 2: Test Connection

Test IMAP connection:

```bash
python -m src.cli check-email
```

Expected output:
```
Checking email inbox for analysis requests...
Connecting to IMAP server...
✓ Pipeline initialized
Polling inbox for new emails...
No new emails to process.
```

If you see an error, check:
- Email password is set correctly
- IMAP server settings are correct
- IMAP is enabled in your email account

### Step 3: Send Test Email

1. **Send an email** from an authorized sender:
   - **To**: Your configured email address
   - **Subject**: `[ANALYZE] Test request`
   - **Body**: `Please analyze last 4 weeks`

2. **Poll inbox**:
   ```bash
   python -m src.cli check-email
   ```

3. **Verify processing**:
   - Email is detected
   - Request is extracted
   - Report is generated
   - Reply email is sent

### Step 4: Verify Reply

Check your inbox for the reply email:
- Subject contains report title
- HTML report embedded in body
- Graphs visible as inline images

---

## Troubleshooting

### Error: "Application-specific password required"

**Cause**: Gmail requires App Password when 2-Step Verification is enabled.

**Solution**:
1. Enable 2-Step Verification in Google Account
2. Generate App Password
3. Use App Password (not regular password) as `EMAIL_PASSWORD`

### Error: "Failed to connect to IMAP server"

**Possible Causes**:
1. Wrong IMAP server/port
2. SSL/TLS not enabled
3. Firewall blocking connection
4. Network connectivity issues

**Solutions**:
- Check `imap.server` and `imap.port` are correct
- Verify `use_ssl: true` is set
- Check firewall allows IMAP connections
- Test network connectivity

**Common IMAP Servers**:
- Gmail: `imap.gmail.com:993`
- Outlook: `outlook.office365.com:993`
- Yahoo: `imap.mail.yahoo.com:993`

### Error: "Authentication failed"

**Possible Causes**:
1. Wrong password
2. Using regular password instead of App Password
3. Account locked or suspended

**Solutions**:
- Verify `EMAIL_PASSWORD` environment variable is set
- Use App Password (for Gmail with 2FA)
- Check account status in email provider dashboard
- Regenerate App Password if needed

### Error: "IMAP not enabled"

**Cause**: IMAP access is disabled in email account settings.

**Solution**:
1. Go to email account settings
2. Enable IMAP access
3. Save changes
4. Wait a few minutes for changes to propagate

### Error: "Email from X rejected: not authorized"

**Cause**: Sender email is not in authorized list.

**Solution**:
1. Add sender email to `authorized_senders.emails`:
   ```json
   {
     "authorized_senders": {
       "emails": ["sender@example.com"],
       "mode": "whitelist"
     }
   }
   ```
2. Or add domain:
   ```json
   {
     "authorized_senders": {
       "domains": ["@company.com"],
       "mode": "whitelist"
     }
   }
   ```

### Error: "Rate limit exceeded"

**Cause**: Too many requests from the same sender.

**Solution**:
1. Wait for rate limit window to reset
2. Adjust rate limits in config:
   ```json
   {
     "rate_limiting": {
       "max_requests_per_hour": 20,
       "max_requests_per_day": 100
     }
   }
   ```
3. Disable rate limiting (for testing only):
   ```json
   {
     "rate_limiting": {
       "enabled": false
     }
   }
   ```

### Emails Not Being Processed

**Checklist**:
- [ ] Email subject contains `[ANALYZE]`
- [ ] Email is unread
- [ ] Sender is authorized
- [ ] Polling is enabled in config
- [ ] IMAP connection successful
- [ ] Email password is set correctly

**Debug Steps**:
1. Check email is in inbox (not spam)
2. Verify subject line exactly matches filter: `[ANALYZE]`
3. Run manual poll: `python -m src.cli check-email`
4. Check logs for errors
5. Verify email is marked as processed after polling

---

## Common IMAP Server Settings

| Provider | IMAP Server | Port | SSL | Notes |
|----------|-------------|------|-----|-------|
| Gmail | `imap.gmail.com` | 993 | Yes | Requires App Password with 2FA |
| Outlook | `outlook.office365.com` | 993 | Yes | May require App Password |
| Yahoo | `imap.mail.yahoo.com` | 993 | Yes | Requires App Password |
| iCloud | `imap.mail.me.com` | 993 | Yes | Requires App-Specific Password |
| Zoho | `imap.zoho.com` | 993 | Yes | Check Zoho settings |

---

## Security Considerations

### Best Practices

1. **Use App Passwords**: Never use your regular email password
2. **Whitelist Senders**: Only authorize trusted email addresses
3. **Enable Rate Limiting**: Prevent abuse and excessive requests
4. **Monitor Logs**: Watch for unauthorized access attempts
5. **Rotate Passwords**: Regenerate App Passwords periodically

### Production Deployment

For production environments:

1. **Use Environment Variables**: Never hardcode passwords
2. **Secure Storage**: Use secret management services (AWS Secrets Manager, etc.)
3. **Network Security**: Restrict IMAP access to trusted networks
4. **Logging**: Log all email processing for audit trails
5. **Monitoring**: Set up alerts for failures or suspicious activity

---

## Next Steps

After setup:
1. ✅ Test configuration: `python scripts/test_email_interface.py check-config`
2. ✅ Test connection: `python -m src.cli check-email`
3. ✅ Send test email and verify processing
4. ✅ Set up automated polling (cron, task scheduler, etc.)
5. ✅ Monitor email processing logs

See [Email Interface Testing Guide](../scripts/test_email_interface_guide.md) for detailed testing instructions.

---

## Additional Resources

- [Email Interface Configuration](../docs/CONFIGURATION_GUIDE.md#email-interface-configuration-configinbound_emailjson)
- [Email Interface Testing Guide](../scripts/test_email_interface_guide.md)
- [Gmail App Passwords Help](https://support.google.com/accounts/answer/185833)
- [Outlook App Passwords Help](https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944)

