// Debug: test form template creation with owner_type/scope
async function main() {
  // Login as business owner
  const loginRes = await fetch('http://localhost:8001/api/v1/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'e2e-bizowner@test.com', password: 'TestPass123!' }),
  });
  const loginData: any = await loginRes.json();
  const token = loginData.tokens.access_token;

  // Get business ID
  const bizRes = await fetch('http://localhost:8001/api/v1/business/', {
    headers: { 'Authorization': 'Bearer ' + token },
  });
  const bizData: any = await bizRes.json();
  const bizId = bizData.results[0].id;
  console.log('Business ID:', bizId);

  // Create template WITH owner_type and scope
  const tmplRes = await fetch(`http://localhost:8001/api/v1/forms/business/${bizId}/templates/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
    body: JSON.stringify({ name: 'Debug Template', owner_type: 'business', scope: 'business' }),
  });
  console.log('Template create:', tmplRes.status);
  const tmplBody = await tmplRes.text();
  console.log('Template response:', tmplBody.substring(0, 300));

  if (tmplRes.ok) {
    const tmplData = JSON.parse(tmplBody);
    const templateId = tmplData.id;

    // Add field
    const fieldRes = await fetch(`http://localhost:8001/api/v1/forms/templates/${templateId}/fields/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ field_key: 'reason', field_type: 'text', label: 'Reason', is_required: true, order: 0 }),
    });
    console.log('Add field:', fieldRes.status);
    const fieldBody = await fieldRes.text();
    console.log('Field response:', fieldBody.substring(0, 300));

    // Publish
    const publishRes = await fetch(`http://localhost:8001/api/v1/forms/templates/${templateId}/publish/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
    });
    console.log('Publish:', publishRes.status);
    console.log('Publish body:', (await publishRes.text()).substring(0, 300));
  }
}
main().catch(e => { console.error('FATAL:', e); process.exit(1); });
