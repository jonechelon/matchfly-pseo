#!/usr/bin/env node
/**
 * Cursor Configuration Diagnostic Script
 * Helps identify why Cursor is blocking Perplexity models
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// IMPORTANTE: Configure PERPLEXITY_API_KEY como variável de ambiente
const API_KEY = process.env.PERPLEXITY_API_KEY;
if (!API_KEY) {
  console.error('❌ ERRO: PERPLEXITY_API_KEY não está definida como variável de ambiente');
  console.error('   Configure com: export PERPLEXITY_API_KEY="sua-chave-aqui"');
  process.exit(1);
}
const BASE_URL = 'https://api.perplexity.ai/v1';

// Test models (only valid chat models)
const TEST_MODELS = [
  'sonar-pro',
  'sonar'
];

function makeRequest(path, method = 'GET', body = null, model = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    
    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname + url.search,
      method: method,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Cursor-Diagnostic/1.0'
      }
    };

    if (body) {
      options.headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ 
            status: res.statusCode, 
            body: parsed,
            headers: res.headers,
            model: model
          });
        } catch (e) {
          resolve({ 
            status: res.statusCode, 
            body: data,
            headers: res.headers,
            model: model
          });
        }
      });
    });

    req.on('error', (error) => { reject({ error, model }); });
    if (body) { req.write(body); }
    req.end();
  });
}

async function testModels() {
  console.log('='.repeat(70));
  console.log('🔍 CURSOR CONFIGURATION DIAGNOSTIC');
  console.log('='.repeat(70));
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`API Key: ${API_KEY ? API_KEY.substring(0, 20) + '...' : 'NOT SET'}`);
  console.log('');

  // Test 1: List available models
  console.log('📋 Test 1: Listing available models from Perplexity API...');
  try {
    const modelsRes = await makeRequest('/models');
    console.log(`Status: ${modelsRes.status}`);
    if (modelsRes.status === 200 && modelsRes.body.data) {
      console.log('Available models:');
      modelsRes.body.data.forEach(m => {
        console.log(`  - ${m.id} (${m.object || 'unknown'})`);
      });
    } else {
      console.log('Response:', JSON.stringify(modelsRes.body, null, 2));
    }
  } catch (e) {
    console.log('❌ Error:', e.message);
  }
  console.log('');

  // Test 2: Test each model name
  console.log('🧪 Test 2: Testing individual model names...');
  for (const model of TEST_MODELS) {
    console.log(`\nTesting model: "${model}"`);
    const payload = JSON.stringify({
      model: model,
      messages: [{ role: 'user', content: 'Say "OK" if you can read this.' }],
      max_tokens: 10
    });

    try {
      const res = await makeRequest('/chat/completions', 'POST', payload, model);
      if (res.status === 200) {
        console.log(`  ✅ SUCCESS: Model "${model}" works!`);
        if (res.body.choices && res.body.choices[0]) {
          console.log(`  Response: ${res.body.choices[0].message.content}`);
        }
      } else {
        console.log(`  ❌ FAILED: Status ${res.status}`);
        if (res.body.error) {
          console.log(`  Error Code: ${res.body.error.code || 'N/A'}`);
          console.log(`  Error Type: ${res.body.error.type || 'N/A'}`);
          console.log(`  Error Message: ${res.body.error.message || 'N/A'}`);
        }
      }
    } catch (e) {
      console.log(`  ❌ CONNECTION ERROR: ${e.error?.message || e.message}`);
    }
    await new Promise(r => setTimeout(r, 500));
  }
  console.log('');

  // Test 3: Check settings files
  console.log('📁 Test 3: Checking configuration files...');
  const projectSettings = path.join(__dirname, '.cursor', 'settings.json');
  const globalSettings = path.join(process.env.HOME, 'Library', 'Application Support', 'Cursor', 'User', 'settings.json');
  
  [projectSettings, globalSettings].forEach((file, idx) => {
    const label = idx === 0 ? 'Project' : 'Global';
    if (fs.existsSync(file)) {
      try {
        const content = JSON.parse(fs.readFileSync(file, 'utf8'));
        console.log(`\n${label} settings (${file}):`);
        console.log(`  - openai.baseURL: ${content['openai.baseURL'] || content['cursor.general.openaiBaseUrl'] || 'NOT SET'}`);
        console.log(`  - openai.apiKey: ${content['openai.apiKey'] ? 'SET' : 'NOT SET'}`);
        console.log(`  - openai.defaultModel: ${content['openai.defaultModel'] || content['cursor.general.defaultModel'] || 'NOT SET'}`);
        console.log(`  - openai.model: ${content['openai.model'] || 'NOT SET'}`);
        const modelNames = content['openai.allowedModelNames'] || content['cursor.general.modelNames'] || [];
        console.log(`  - Allowed models: ${modelNames.length > 0 ? modelNames.join(', ') : 'NONE'}`);
      } catch (e) {
        console.log(`  ❌ Error reading ${label} settings: ${e.message}`);
      }
    } else {
      console.log(`  ⚠️  ${label} settings file not found: ${file}`);
    }
  });
  console.log('');

  // Test 4: Recommendations
  console.log('💡 Test 4: Recommendations');
  console.log('');
  console.log('If models are working via API but Cursor blocks them:');
  console.log('  1. Cursor may be doing client-side validation');
  console.log('  2. Try using the Cursor UI: Cursor → Settings → Models');
  console.log('  3. Enable "Override OpenAI Base URL" in the UI');
  console.log('  4. Add models manually via "Add Custom Model"');
  console.log('  5. Check Developer Tools (Cmd+Shift+P → Toggle Developer Tools)');
  console.log('  6. Look for errors in Console when selecting a model');
  console.log('');
  console.log('Expected error codes:');
  console.log('  - 401: Invalid API key');
  console.log('  - 403: Model not available for your plan');
  console.log('  - 404: Model not found');
  console.log('  - Client-side: Cursor blocking before API call');
  console.log('');
}

testModels().catch(console.error);
