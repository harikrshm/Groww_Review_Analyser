# Email Deliverability Guide - Avoiding Spam Folder

## Problem
Emails are going to spam folder instead of inbox.

## Solutions (In Order of Importance)

### 1. **Domain Authentication (MOST IMPORTANT - RECOMMENDED)**

SendGrid requires domain authentication to improve deliverability. This involves setting up SPF, DKIM, and DMARC records.

**Steps:**
1. Go to SendGrid Dashboard → Settings → Sender Authentication
2. Click "Authenticate Your Domain"
3. Follow the wizard to add DNS records (SPF, DKIM, DMARC) to your domain
4. Wait for verification (can take up to 48 hours)
5. Update `config/email.json` to use your authenticated domain:
   ```json
   "from_email": "noreply@yourdomain.com"
   ```

**Why this works:** Domain authentication proves you own the domain and significantly improves sender reputation.

### 2. **Use a Custom Domain Instead of Gmail**

Currently using: `harikrish656@gmail.com`

**Better approach:**
- Use a custom domain (e.g., `noreply@yourdomain.com`)
- Authenticate the domain in SendGrid
- This is the most reliable way to avoid spam folder

### 3. **Immediate Actions (Already Implemented)**

✅ **Email Headers Added:**
- List-Unsubscribe header (helps with spam filters)
- Reply-To header (proper email routing)

### 4. **SendGrid Account Warm-up**

If this is a new SendGrid account:
- Start with low volume (10-20 emails/day)
- Gradually increase over 2-4 weeks
- This builds sender reputation

### 5. **Check SendGrid Activity**

Monitor your SendGrid dashboard:
- Go to Activity Feed
- Check for bounces, blocks, or spam reports
- Address any issues immediately

### 6. **Recipient Actions (Quick Fix)**

Ask recipients to:
- Mark email as "Not Spam" in their email client
- Add sender (`harikrish656@gmail.com`) to contacts
- This helps train the spam filter for future emails

## Quick Fix Steps

1. **Verify sender email in SendGrid:**
   - Dashboard → Settings → Sender Authentication → Single Sender Verification
   - Verify `harikrish656@gmail.com` if not already done ✅

2. **Check SendGrid Activity:**
   - Dashboard → Activity Feed
   - Look for any warnings, bounces, or blocks

3. **Test with recipient:**
   - Ask recipient to mark as "Not Spam"
   - Add to contacts
   - Future emails should improve

## Long-term Solution (Best Practice)

**Set up Domain Authentication:**
1. Get a custom domain (if you don't have one)
2. Authenticate it in SendGrid (SPF, DKIM, DMARC)
3. Update `config/email.json` to use the authenticated domain
4. This is the most reliable way to avoid spam folder

## Testing

After making changes:
1. Send a test email
2. Check spam folder initially
3. If it goes to spam, mark as "Not Spam"
4. Future emails should go to inbox

## Additional Notes

- Gmail addresses as senders have lower deliverability than custom domains
- Domain authentication is the industry standard for email deliverability
- SendGrid provides detailed guides for domain authentication setup

