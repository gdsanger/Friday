# ISSUE-55: @Mentions Feature - Manual Testing Checklist

## Setup Prerequisites

Before testing, ensure:
- Django server is running (`python manage.py runserver`)
- At least 2 non-portal users exist in the database
- At least 1 test project with tasks exists
- Mail configuration is set up (check settings.SITE_URL)

## Testing Checklist

### Backend Tests

#### 1. Mention Parser (apps/tasks/mentions.py)

**Test: parse_mentions() finds valid usernames**
```python
from apps.tasks.mentions import parse_mentions
text = "@testuser1 can you review? Also @testuser2"
mentioned = parse_mentions(text)
# Should return list of User objects
```

**Test: Ignores non-existent users**
```python
text = "@nonexistent123 hello"
mentioned = parse_mentions(text)
# Should return empty list, no errors
```

**Test: Excludes portal users**
```python
text = "@portaluser check this"
mentioned = parse_mentions(text)
# Should return empty list (portal users filtered)
```

**Test: render_mentions() HTML output**
```python
from apps.tasks.mentions import render_mentions
text = "@john please review"
rendered = render_mentions(text)
# Should contain: <span class="mention">@john</span>
```

#### 2. User Search API

**Test: API endpoint exists and returns JSON**
```bash
curl -u username:password "http://localhost:8000/accounts/api/users/search/?q=test"
# Should return: {"users": [...]}
```

**Test: API requires authentication**
```bash
curl "http://localhost:8000/accounts/api/users/search/?q=test"
# Should return 401 Unauthorized
```

**Test: Returns correct user structure**
```json
{
  "users": [
    {
      "key": "username",
      "value": "Display Name",
      "initials": "DN"
    }
  ]
}
```

#### 3. Comment View with Mentions

**Test: Creating comment with mentions**
1. Navigate to a task detail page
2. Add comment: "@username please review this"
3. Check notifications table for new Notification
4. Check mail queue/logs for outgoing email

**Test: Self-mention doesn't create notification**
1. Add comment mentioning your own username
2. Verify no notification created for self

**Test: Multiple mentions in one comment**
1. Add comment: "@user1 and @user2 please check"
2. Verify both users receive notifications

### Frontend Tests

#### 1. Tribute.js Integration

**Test: CDN links loaded**
- Open browser DevTools > Network tab
- Load any page
- Verify tribute.css and tribute.min.js loaded successfully

**Test: Textarea has mention-enabled class**
- Inspect comment form in slide-over
- Verify: `<textarea class="form-control mention-enabled" ...>`

**Test: JavaScript initialized**
- Open browser Console
- Type: `typeof Tribute`
- Should return: "function"

#### 2. Mention Autocomplete Dropdown

**Test: Typing @ opens dropdown**
1. Navigate to task detail (slide-over)
2. Click in comment textarea
3. Type "@"
4. Dropdown should appear within 500ms

**Test: Typing filters users**
1. Type "@j"
2. Dropdown should show only users matching "j"
3. Type "@jo"
4. Dropdown should filter further to "jo"

**Test: Dropdown shows correct information**
- Avatar initials (colored circle)
- Full name (bold, 13px)
- @username (smaller, lighter)

**Test: Selection inserts @username**
1. Type "@j"
2. Click or press Enter on a user
3. Text should contain "@username" (not display name)

**Test: Multiple mentions in one comment**
1. Type: "@user1 "
2. Type: "and @user2"
3. Both mentions should be inserted correctly

**Test: Escape closes dropdown**
1. Type "@"
2. Press Escape
3. Dropdown should close without selection

#### 3. HTMX Integration

**Test: Mentions work in slide-over**
1. Open task slide-over (HTMX swap)
2. Type "@" in comment field
3. Dropdown should work (initMentions reinitializes)

**Test: Mentions work after comment submission**
1. Add comment with mention
2. Form resets after submission (hx-on::after-request)
3. Type "@" again
4. Dropdown should still work

### Display Tests

#### 1. Mention Highlighting

**Test: @username is highlighted in comments**
1. Add comment: "Hey @username please check"
2. Submit comment
3. Comment should display with @username styled:
   - Colored text (accent color)
   - Light background
   - Bold weight
   - Slightly smaller font

**Test: Multiple mentions highlighted**
1. Add comment: "@user1 and @user2 check this"
2. Both mentions should be highlighted

**Test: Works in both light and dark mode**
1. Toggle theme (top-right icon)
2. Verify mentions are visible in both modes

#### 2. CSS Styling

**Test: Mention span styling**
- Color: var(--friday-accent)
- Background: var(--friday-accent-light)
- Font-weight: 600
- Border-radius: 3px

**Test: Tribute dropdown styling**
- Background: var(--friday-surface)
- Border: 1px solid var(--friday-border)
- Border-radius: 8px
- Shadow: var(--shadow-md)
- z-index: 9999 (above other content)

### Mail & Notification Tests

#### 1. In-App Notifications

**Test: Notification created**
1. User A mentions User B in comment
2. Check User B's notifications
3. Should show: "{User A} hat dich in einem Kommentar erwähnt"

**Test: Notification links to task**
1. Click notification
2. Should navigate to correct task

#### 2. Email Notifications

**Test: Email sent on mention**
1. User A mentions User B
2. Check mail logs/queue
3. Email should be queued for User B

**Test: Email subject for mentions**
- Should say: "Du wurdest in einem Kommentar erwähnt"
- Not: "Neuer Kommentar"

**Test: Email content**
- Should say: "{Author} hat dich ... erwähnt:"
- Should include comment text
- Should have "Task öffnen →" button
- Should link to task: {SITE_URL}/tasks/{pk}/

**Test: Only users with notify_email=True receive mail**
1. Set User B's notify_email to False
2. Mention User B
3. No email should be sent

### Edge Cases

**Test: Non-existent username**
1. Type: "@nonexistentuser123 hello"
2. Submit comment
3. Should succeed without errors
4. No notifications sent

**Test: Portal user mention**
1. Type: "@portaluser check"
2. Dropdown should not show portal users
3. Even if typed, no notification sent

**Test: Duplicate mentions**
1. Type: "@john @john check"
2. Only one notification sent to @john

**Test: Case insensitivity in search**
1. Type: "@Jo"
2. Should find users like "john", "Joshua"

**Test: Special characters in username**
1. Username: "test.user-name"
2. Type: "@test"
3. Should find user
4. Can mention with dots/hyphens

## Success Criteria

All tests should pass with:
- ✓ No JavaScript errors in console
- ✓ No Python errors in server logs
- ✓ Mentions autocomplete works smoothly
- ✓ Notifications created correctly
- ✓ Emails queued/sent correctly
- ✓ UI styling looks professional
- ✓ Works with HTMX dynamic content
- ✓ Compatible with light/dark themes

## Known Limitations

1. Mention parsing uses simple regex - doesn't check markdown code blocks
2. No mention preview in real-time (only after submit)
3. Duplicate mentions in same comment don't deduplicate in text
4. Email is sent even if user already watches the task

## Future Enhancements

- [ ] Mention suggestions based on project members
- [ ] Mention suggestions based on task watchers
- [ ] Show mention count badge on notifications icon
- [ ] Keyboard navigation in dropdown (arrow keys)
- [ ] Mention preview tooltip on hover
