# Register a fresh user for deactivation test
$regBody = '{"email":"e2e_deactivate@test.com","password":"TestPass123!","confirm_password":"TestPass123!","username":"e2e_deactivate"}'
try {
    $regResp = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/register/' -Method POST -Body $regBody -ContentType 'application/json' -Headers @{'X-Client-Type'='mobile'}
    Write-Host "Registered: $($regResp.email)"
} catch {
    Write-Host "Register failed (may already exist): $($_.Exception.Message)"
}

# Get verification code from DB
$env:PGPASSWORD = 'postgres_dev_password'
$code = & psql -h localhost -U django_user -d backend_core_db -t -A -c "SELECT code FROM auth_verification_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'e2e_deactivate@test.com') AND is_used = false ORDER BY created_at DESC LIMIT 1"
Write-Host "Verification code: $code"

# Verify email
$verBody = "{`"email`":`"e2e_deactivate@test.com`",`"code`":`"$($code.Trim())`"}"
try {
    $verResp = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/verify-email/' -Method POST -Body $verBody -ContentType 'application/json'
    Write-Host "Verified: $($verResp.message)"
} catch {
    Write-Host "Verify failed: $($_.Exception.Message)"
}

# Login
$loginBody = '{"email":"e2e_deactivate@test.com","password":"TestPass123!","device_id":"e2e-deact","device_type":"web","device_name":"e2e-deact"}'
try {
    $loginResp = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/login/' -Method POST -Body $loginBody -ContentType 'application/json' -Headers @{'X-Client-Type'='mobile'}
    Write-Host "TOKEN=$($loginResp.access_token)"
} catch {
    Write-Host "Login failed: $($_.Exception.Message)"
}
