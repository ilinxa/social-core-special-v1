# Login as bob (owner of Bob LLC)
$loginBody = '{"email":"bob@example.com","password":"testpass123","device_id":"e2e-script","device_type":"web","device_name":"e2e-script"}'
$loginResp = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/login/' -Method POST -Body $loginBody -ContentType 'application/json' -Headers @{'X-Client-Type'='mobile'}
$token = $loginResp.access_token
Write-Host "Logged in as bob, token starts with: $($token.Substring(0, 20))..."

# Search for e2e_user_a
$headers = @{Authorization="Bearer $token"}
$searchResp = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/explore/users/?q=e2e_user_a' -Method GET -Headers $headers
$targetUser = $searchResp.results | Where-Object { $_.username -eq 'e2e_user_a' }
Write-Host "Target user: $($targetUser.id)"

# Create invitation
$invBody = "{`"target_user_id`":`"$($targetUser.id)`"}"
Write-Host "Invitation body: $invBody"
$invResp = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/business/bob-llc/transactions/invitations/' -Method POST -Body $invBody -ContentType 'application/json' -Headers $headers
Write-Host "INVITATION_ID=$($invResp.id)"
Write-Host "INVITATION_STATUS=$($invResp.status)"
