# SCOPE 1: USER (U)

## 1.1 Registration

- **U-01** | State: _Not logged in_ | Action: Navigate to `/register` | Expected: Registration form appears with email, username, password fields and OAuth buttons (Google, Apple). Link to login page visible.
    - **R-U-01** we can see the registration page and create account by an email and password
        - login page link, oauth social btns are visable
    Gaps: 
    - **G-U-01-01** `google` and `apple` api are not connected for oauth
    - **G-U-01-02** we need email verification but we dont have stemp (ses aws) connected 
        - we must make sure are back end be ready for that + (as far as i remember we had 2 different system 1. verify by `link` 2. `otp`) we should check these systems readyness 
        
- **U-02** | State: _On register page_ | Action: Submit form with valid email, username (3+ chars), password (8+ chars) | Expected: Account created. Redirected to `/verify-email`. Success toast shown.
    Gaps:
    - we dont have username field here (we must also check the models and find out which fields could we have):
        - first name
        - last name 
        - repasword 
        - other general user registration field 

    - no verify email rediecting (we dont have ses connected) but we need to check backend to know howmuch we are ready 
    also for now we can create the otp and instead of sending email show it in terminal logs and we can test it using that 
    - IMPORTANT THESE ARE CRETICAL THINGS 
    

- **U-03** | State: _On register page_ | Action: Submit with already-used email | Expected: Error message "Email already registered" (or similar). Form stays on page.
    - **R-U-02**: yes it didnt accept Error message "Email already registered"

- **U-04** | State: _On register page_ | Action: Submit with already-taken username | Expected: Error message about username unavailability.
    - there is no username field!!!

- **U-05** | State: _On register page_ | Action: Submit with weak password (less than 8 chars) | Expected: Client-side validation error shown. Form not submitted.
    - **R-U-05** it just look for character count !!! 
    - **G-U-05-01** it accept user12345 for email: user4@user.com (no similarity check - no captal character or special character chek)
    - **G-U-05-02** we also need a ui helper to show howmuch is the pass strong and tik the criterias

- **U-06** | State: _On register page_ | Action: Submit with empty fields | Expected: Validation errors shown for each required field.
    - **R-U-06**  we already have 2 field and both are required email and password! it shows the required error currectly

- **U-07** | State: _On register page_ | Action: Submit with invalid email format | Expected: Validation error for email field.
    - **R-U-07** yes it asks me Enter a valid email address

### its login automatically !!!
--------------------
## 1.2 Email Verification (we dont conect these apies)

- **U-08** | State: _Registered but unverified, on `/verify-email`_ | Action: Enter the 6-digit code from email | Expected: Email verified. Success message. Redirected to `/home` (or login).

- **U-09** | State: _On verify-email page_ | Action: Enter wrong code | Expected: Error "Invalid code" shown. Can retry.

- **U-10** | State: _On verify-email page_ | Action: Enter wrong code 5 times | Expected: Account locked out from verification. Error message indicates lockout.

- **U-11** | State: _On verify-email page_ | Action: Click "Resend verification" | Expected: New code sent. Success toast "Verification email sent".

- **U-12** | State: _Not logged in_ | Action: Navigate to `/resend-verification`, enter email | Expected: Success message shown (always, even for non-existent emails to prevent enumeration).

### note we must make sure the otp and links have expire time and rate limit for resending the verification code or link
-----
## 1.3 Login

- **U-13** | State: _Not logged in, email verified_ | Action: Navigate to `/login`, enter valid email + password | Expected: Logged in. Redirected to `/home`. User menu shows username in topbar. 
    - **R-U-13**: yes it works

- **U-14** | State: _On login page_ | Action: Enter valid email + wrong password | Expected: Error "Invalid credentials". Form stays on page.
    - **R-U-14**: yes it works "Invalid email or password"
- **U-15** | State: _On login page_ | Action: Enter non-existent email | Expected: Same error "Invalid credentials" (no user enumeration).
    - **R-U-15**: yes it works "Invalid email or password"

- **U-16** | State: _On login page_ | Action: Attempt login 5+ times rapidly with wrong password | Expected: Rate limit hit. Error "Too many attempts, try again later".
    - **R-U-16**: no i attempt +10 time rapidly with wrong pass but it does not hit ratelimit and imediatly when i write the right pass it loged in   
    no such a message:
    "Too many attempts, try again later"
- **U-17** | State: _On login page_ | Action: Click Google OAuth button | Expected: Redirected to Google consent screen. After consent, redirected back and logged in. 
    - not connected for now

- **U-18** | State: _On login page_ | Action: Click Apple OAuth button | Expected: Redirected to Apple sign-in. After consent, redirected back and logged in.
    - not connected for now

- **U-19** | State: _On login page_ | Action: Click "Forgot password?" link | Expected: Navigated to `/forgot-password` page.
    - **R-U-19** it redirect me with email input and claim that it sent me the imail but i ses doesnt connected yet
- **U-20** | State: _On login page_ | Action: Click "Register" link | Expected: Navigated to `/register` page.
    - **R-U-20**: yes it works 

-----
## 1.4 Password Management

- **U-21** | State: _Not logged in_ | Action: Navigate to `/forgot-password`, enter registered email, submit | Expected: Success message "If an account exists, a reset link was sent" (always same message).

- **U-22** | State: _Not logged in_ | Action: On `/forgot-password`, enter non-existent email | Expected: Same success message (no user enumeration).

- **U-23** | State: _Have reset email_ | Action: Click reset link, navigate to `/reset-password?token=...` | Expected: New password form shown with password field.

- **U-24** | State: _On reset password page_ | Action: Enter new valid password and submit | Expected: Password reset success. Redirected to login.

- **U-25** | State: _On reset password page_ | Action: Use expired or invalid token | Expected: Error "Invalid or expired reset link".

- **U-26** | State: _Logged in as User A_ | Action: Navigate to settings/security, change password (enter current + new) | Expected: Password changed. All other sessions logged out. Success toast.
    - **R-U-26-01** password changed when the current password is corect but doesnt work with the wrang password.
    gsps and issues
    - **G-U-26-02** it shows 2 active session (device is unknown) 
        - revoke btn: Failed to revoke session. Please try again.
        - signout everywhere: Failed to log out all sessions. Please try again.

- **U-27** | State: _Logged in as User A_ | Action: Change password with wrong current password | Expected: Error "Current password is incorrect".
    - **R-U-27** yes its working

----
## 1.5 Session Management

- **U-28** | State: _Logged in as User A_ | Action: Navigate to `/sessions` | Expected: List of active sessions shown with device info, IP, last activity. Current session flagged.
    - i can see the sessions and current session is marked

- **U-29** | State: _On sessions page, logged in from 2 devices_ | Action: Click "Revoke" on another session | Expected: Session removed from list. That device is logged out.
     - it is not working Failed to revoke session. Please try again.
- **U-30** | State: _On sessions page_ | Action: Try to revoke current session | Expected: Either not allowed or handled gracefully (logged out).
    - no such btn here for current session

- **U-31** | State: _Logged in as User A_ | Action: Click "Logout" in user menu | Expected: Logged out. Redirected to `/login`. Access token cleared.
    - logout workd currectly
- **U-32** | State: _Logged in from 2+ devices_ | Action: Click "Logout all devices" | Expected: All sessions revoked. Logged out everywhere. Redirected to login.
    - it doesnt work: Failed to log out all sessions. Please try again.

## 1.6 User Profile — View & Edit

- **U-33** | State: _Logged in as User A_ | Action: Navigate to `/profile` | Expected: Own profile page shows username, display name, bio, avatar, country, city, tags.
    - yes i see the own profile:
        - firstname
        - lastname
        - phone
        - location 
        - time zone
        - language
        - bio 
        - proofile picture
        - username 
        - email
        - chips
        - join date
    Gap: 
    biside the profile picture it shows auto extracted name from email but we must show firstname + lastname
    we also need cover picture (dont have in backend we must create this area must be able to accept gif aswell in both backend and frontend)


- **U-34** | State: _On profile page_ | Action: Click "Edit Profile" (or navigate to `/profile/edit`) | Expected: Edit form with fields: first_name, last_name, bio, country, city, tags, timezone, language.
    - yes i can see the edit panel

- **U-35** | State: _On edit profile page_ | Action: Update first_name, last_name, bio and save | Expected: Profile updated. Success toast. Changes reflected on profile page.
    - yes it works 

- **U-36** | State: _On edit profile page_ | Action: Select a country from dropdown | Expected: Country saved. City dropdown filters to cities in selected country.
    - yes it works

- **U-37** | State: _On edit profile page_ | Action: Select a city using combobox | Expected: City saved. Shown on profile.
    - yes it works

- **U-38** | State: _On edit profile page_ | Action: Add tags (type tag, press enter) | Expected: Tags added as chips. Saved to profile.
    - yes it works

- **U-39** | State: _On edit profile page_ | Action: Change timezone and language | Expected: Preferences saved successfully.
    - yes it works
## 1.7 Avatar

- **U-40** | State: _On profile/edit page_ | Action: Upload avatar image (JPEG, < 5MB) | Expected: Avatar uploaded immediately. Preview shown. Success toast.
    - yes its uploaded  and i can se the preview
    gaps:
    - image object must have (object cover style) now its deformed ( also we must have squer croper system when we upload a photo user can set the area like instagrom)
- **U-41** | State: _On profile/edit page_ | Action: Upload file > 5MB | Expected: Error "File too large" (max 5MB).
    - yes it works 
- **U-42** | State: _On profile/edit page_ | Action: Upload non-image file (.pdf) | Expected: Error "Unsupported format".
    - it works 
- **U-43** | State: _Has avatar uploaded_ | Action: Click "Remove avatar" | Expected: Avatar removed. Default placeholder shown.
    - it works

## 1.8 Username

- **U-44** | State: _Logged in as User A_ | Action: Navigate to settings, update username | Expected: Username changed. Success toast.
    - now username sits in the profile edit not in the setting (we must replace it to setting)
    but it works currectly with auto validation (unicness check)
    - we need to limit it must have atleast 5 character 
    - we need a reseved name list modify able by superuser (django dfault admin panel)  

- **U-45** | State: _On settings page_ | Action: Enter already-taken username | Expected: Error "Username already taken".
    - yes it works but i define the gaps in question U-44
- **U-46** | State: _On settings page_ | Action: Enter username with invalid characters | Expected: Validation error.
    - it checks the charakters but the gaps are defined in U-44
----
## 1.9 Privacy

- **U-47** | State: _Logged in as User A, profile is public_ | Action: Log in as User B, navigate to `/users/userA` | Expected: User A's public profile is visible.
    - no its visable but limited 

- **U-48** | State: _Logged in as User A_ | Action: Set profile to private (is_public = false) | Expected: Setting saved.
    - its not in the setting its in edit profile which is fine and saved
- **U-49** | State: _User A profile is private_ | Action: Log in as User B, navigate to `/users/userA` | Expected: 404 or "Profile not found" (private profile hidden).
    - yes it acts like your expectation but its not currect we must be able to see the users limited informations (name, profile pic, verification status, username )
- **U-50** | State: _User A profile is private_ | Action: As User A, navigate to `/users/userA` | Expected: Own profile always visible regardless of privacy setting.
    - ues it works

-----
## 1.10 Navigation & Layout

- **U-51** | State: _Logged in, on `/home`_ | Action: Check sidebar (desktop) | Expected: Personal nav sections visible: Main (Home, Explore, Notifications, Activity), Account (Profile, Settings, Security).
    - yes these are fine just i think we can mobe seurity in the setting 

- **U-52** | State: _Logged in, on `/home`, mobile viewport_ | Action: Check bottom navbar | Expected: Bottom navbar with Home, Explore, Notifications, Profile icons.
    - yes its fine and works well
- **U-53** | State: _Logged in_ | Action: Click hamburger menu (mobile) | Expected: Mobile menu sheet opens with full navigation. 
    - this is working well and its good 

- **U-54** | State: _Logged in_ | Action: Click user menu in topbar | Expected: Dropdown with profile link, settings, logout option.
    - in mobile menu we have repeated things - bottom nav bar - hamburger menu - and menu on top
        instead of user menu we must have account switcher and navigation to profile (if there is just 1 account)
- **U-55** | State: _Logged in, no business memberships_ | Action: Open account switcher | Expected: Only personal context shown. No business or platform accounts listed.
    - yes it woks fine i dont se account to switch
- **U-56** | State: _Logged in, member of Biz-X_ | Action: Open account switcher | Expected: Personal context + Biz-X listed. Can switch to business console.
    - yes it works fine 
    gap we need member ship limitation users can (be member up to 3 businesses + 1 platform)
    instead of top menu (opens when we click on profile picture we should have ac)

- **U-57** | State: _Not logged in_ | Action: Try to navigate to `/home` | Expected: Redirected to `/login?callbackUrl=/home`.
    - this works fine

- **U-58** | State: _Not logged in_ | Action: Navigate to `/explore` | Expected: Explore page loads (public access). "Users" tab may be auth-gated.
    - yes it loads and we just able to see the businesses
------

## 1.11 Explore / Discovery

- [ ] **U-59** | State: _On `/explore`_ | Action: Type a search query in search bar | Expected: Results shown in "All" tab (businesses + users combined). Results update as you type or on submit.
    - yes it works
- [ ] **U-60** | State: _On `/explore`, "Businesses" tab_ | Action: Search for a business name | Expected: Business cards shown with name, tagline, industry, location, tags.
    - its fine
- [ ] **U-61** | State: _On explore, Businesses tab_ | Action: Apply country filter | Expected: Results filtered to businesses in selected country. URL params updated.
    - its fine
- [ ] **U-62** | State: _On explore, Businesses tab_ | Action: Apply city filter (after selecting country) | Expected: Results filtered to businesses in selected city.
    - its fine
- [ ] **U-63** | State: _On explore, Businesses tab_ | Action: Apply industry filter | Expected: Results filtered by industry.
    - its fine
- [ ] **U-64** | State: _On explore, Businesses tab_ | Action: Apply company_size filter | Expected: Results filtered by company size range.
    - fine
- [ ] **U-65** | State: _On explore, Businesses tab_ | Action: Apply multiple filters simultaneously | Expected: All filters applied together (AND logic). Filter indicator badge shows count.
    - fine
- [ ] **U-66** | State: _On explore, Businesses tab_ | Action: Add tags filter | Expected: Tag autocomplete from `/explore/tags/` endpoint. Results filtered by tags.
    - fine
- [ ] **U-67** | State: _On explore, Businesses tab, many results_ | Action: Scroll to bottom of results | Expected: Infinite scroll triggers. Next page loads. Loading indicator shown.
    - fine
- **U-68** | State: _On explore_ | Action: Apply filters, then reload page | Expected: Filters restored from URL query params. Same results shown.
    - fine
- **U-69** | State: _On explore_ | Action: Search with no results | Expected: Empty state message "No results found" or similar.
    - fine
- **U-70** | State: _Logged in, on explore, "Users" tab_ | Action: Search for a user | Expected: User cards shown with display name, avatar, country, tags.
    - fine
- **U-71** | State: _Not logged in, on explore_ | Action: Click "Users" tab | Expected: Tab is auth-gated. Prompted to log in or tab disabled.
    - its fine
    - we need explore nav item in public pages top navbar 
- **U-72** | State: _On explore, Users tab_ | Action: Apply country + city filter | Expected: Users filtered by location.
    - fine

- **U-73** | State: _On explore, Businesses tab_ | Action: Click on a business card | Expected: Navigated to `/business/[slug]` public profile page.
    - fine
- **U-74** | State: _On explore_ | Action: Change ordering to "name" or "newest" | Expected: Results re-sorted accordingly.
    -fine

## 1.12 Public Pages

- **U-75** | State: _Not logged in_ | Action: Navigate to `/` (root) | Expected: Landing/home page shown with platform info.
    - fine

- **U-76** | State: _Not logged in_ | Action: Navigate to `/about` | Expected: About page loads.
    - fine
- **U-77** | State: _Not logged in_ | Action: Navigate to `/contact` | Expected: Contact page loads.
    - fine

- **U-78** | State: _Not logged in_ | Action: Navigate to `/business/test-business` | Expected: Public business profile page. Shows display name, tagline, description, logo, industry, location. No edit buttons.
    - fine
- **U-79** | State: _Not logged in_ | Action: On public business page, check for "Join" button | Expected: If business has `open_member_request=true`, "Request to Join" button visible. If false, no join button.
    - fine 

- **U-80** | State: _Logged in, not member of Biz-X, open_member_request=true_ | Action: Click "Request to Join" on public business page | Expected: Join request transaction created. Success toast. Button changes to "Request Pending" or similar.
    - fine
- **U-81** | State: _Logged in, already member of Biz-X_ | Action: Visit `/business/test-business` | Expected: "Request to Join" button not shown (already a member). May show "Go to Console" link instead.
    - fine
- **U-82** | State: _Not logged in_ | Action: Navigate to `/platform/profile` | Expected: Public platform profile page shown (platform name, description, logo).
    - fine

## 1.13 User Transactions (Receiving)
here we have problem we need to review them deeply, 
- form transaction connection 
- circular request verification and invitation circular verification 
- their ui ux nedd fixes 

right now the invitation with connected form reaches to the user 
- rign now when user try to request a business with forme attaches to the rquest transaction see the form and fill it then able to send it. this request reches to the business but in business transactions requests page request detail page the the form is wronge (maybe the versioning couse this problem)
in user side who sends the request the form is correct but there we need to see the target business profile card (simple) as well 
request to join btn dont change -> cansle btn (when we already sent the request)
allso i think these area f code is not consisttent and curectly structured

gaps:
- the form data shown in the request is missed and not correct 
- the requester information is mised in request ditail page (business side) we cannot se the requester image name and base profile info

- [ ] **U-83** | State: _Logged in as User A, not member of Biz-X. Biz-X owner sent invitation_ | Action: Navigate to `/activity` or check transactions | Expected: Pending invitation visible in transaction list.

- [ ] **U-84** | State: _Viewing pending business invitation_ | Action: Click on invitation to view detail | Expected: Transaction detail page shows: initiator info, business name, role offered, message, timeline, action buttons (Accept, Deny).

- [ ] **U-85** | State: _Viewing business invitation detail_ | Action: Click "Accept" | Expected: Transaction → ACCEPTED. Membership created (ACTIVE). Redirected or toast "You joined [business]". Business now in account switcher.

- [ ] **U-86** | State: _Viewing business invitation detail_ | Action: Click "Deny" | Expected: Transaction → DENIED. Removed from active list. Toast "Invitation denied".

- [ ] **U-87** | State: _Viewing business invitation with required form_ | Action: Click "Accept" | Expected: Form dialog opens. Must fill required fields. Submit form, then accept completes. Transaction → PENDING_REVIEW. Membership → PENDING_APPROVAL.

- [ ] **U-88** | State: _Accepted invitation with form, status PENDING_REVIEW_ | Action: Check membership status | Expected: Membership shows as PENDING_APPROVAL. Limited or no console access. Guard shows "Pending Review" state.

---------------------------

- [ ] **U-89** | State: _Logged in as User A. User B sent connection request_ | Action: View connection request | Expected: Transaction detail shows User B's info and Accept/Deny buttons.
    - We dont have connection system yet as far as i remember 

- [ ] **U-90** | State: _Viewing connection request_ | Action: Accept connection | Expected: Transaction → ACCEPTED. Connection established.
    - We dont have connection system yet as far as i remember 

- [ ] **U-91** | State: _Viewing connection request_ | Action: Deny connection | Expected: Transaction → DENIED.
    - We dont have connection system yet as far as i remember 

- **U-92** | State: _Logged in as User A_ | Action: Send connection request to User B | Expected: Transaction created (PENDING). Visible in sent transactions.
    - We dont have connection system yet as far as i remember 
- **U-93** | State: _Sent connection request to User B_ | Action: Cancel the request | Expected: Transaction → CANCELLED.
    - We dont have connection system yet as far as i remember 

-----------------------

## 1.14 Activity & Notifications (Placeholders)

- **U-94** | State: _Logged in_ | Action: Navigate to `/activity` | Expected: Activity page loads (placeholder content or empty state).
    - yes we can navigate and see the activities  but in new activite we must have a marker that shows us there is new thing (notify us)

- **U-95** | State: _On activity page_ | Action: Click on an activity item (if any) | Expected: Navigated to `/activity/[id]` detail page.
    - yes i tested it by an invitation and i could see the detaile
- **U-96** | State: _Logged in_ | Action: Navigate to `/notifications` | Expected: Notifications page loads (placeholder content or empty state).
    - we must wired it up now its an empty page 
    - notifications must be grouped and type aware (need deep review of our system)


## 1.15 Account Deactivation
### i cannot find deactivation btn in the ui it must be in setting passes these tests 
> we need to review the logic we already have in backend and make sure it works exactly matched

- [ ] **U-97** | State: _Logged in as User A_ | Action: Navigate to settings, click "Deactivate Account" | Expected: Confirmation dialog appears. Warns about consequences.

- [ ] **U-98** | State: _On deactivation confirmation_ | Action: Confirm deactivation | Expected: Account soft-deleted. Logged out. Redirected to login.

- [ ] **U-99** | State: _Account deactivated_ | Action: Try to log in with old credentials | Expected: Login fails or shows "Account deactivated" message.

---

IMPORTANT
- page navigation are too slow and laggy each time it try to render in 
- refresh and access tokens management has problem it is not fully automated i thing i forced to refresh the pache too much time to re connection 